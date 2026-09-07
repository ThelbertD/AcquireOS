#!/usr/bin/env python3
"""Source-agnostic CSV ingestion for the prospect pipeline.

Reads a CSV with a column-mapping config, normalises it, validates email syntax, removes
duplicates, checks against the suppression list, and loads the survivors into Postgres.

**Nothing is dropped silently.** Every rejected row is written to the rejection log with its
reason and its original content. "The list is smaller than expected" is a question you will be
asked, and it has to be answerable row by row.

Usage:
    # Dry run: full validation, no database, no dependencies. Always do this first.
    python list_pipeline.py --csv leads.csv --mapping mapping.json --dry-run

    # Dry run with a suppression file rather than a database
    python list_pipeline.py --csv leads.csv --mapping mapping.json --dry-run \\
        --suppression suppression.csv --rejections rejected.csv

    # Load. Needs DATABASE_URL and psycopg.
    python list_pipeline.py --csv leads.csv --mapping mapping.json

    # Write a starter mapping file from a CSV's headers
    python list_pipeline.py --csv leads.csv --infer-mapping > mapping.json

The mapping file:

    {
      "source_name":   "conference-attendee-list-q1",
      "source_detail": "Attendee list, downloaded 2026-03-01",
      "encoding":      "utf-8-sig",
      "delimiter":     ",",
      "columns": {
        "email":        "Email",
        "full_name":    "Contact Name",
        "job_title":    "Job Title",
        "company_name": "Company",
        "website":      "Website",
        "employee_count": "Employees",
        "country":      "Country"
      },
      "defaults": {
        "jurisdiction":  "US",
        "consent_basis": "can-spam-optout"
      },
      "segment_field": "employee_band"
    }

Only `email` is a required column. Everything else improves scoring and personalisation.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

# --------------------------------------------------------------------------------------
# Validation rules
# --------------------------------------------------------------------------------------

# Deliberately not RFC 5322. A full RFC-compliant pattern accepts addresses no mail server
# will deliver to and is unreadable. This accepts what real addresses look like and rejects
# what typos look like, which is the actual job. Verification with a provider is a separate,
# required step; this is the cheap pass that runs first.
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}$"
)

# Role addresses reply at close to zero, complain above average, and are a common source of
# spam trap hits. They contribute volume with no pipeline.
ROLE_LOCAL_PARTS = frozenset(
    """
    info sales admin support help hello contact enquiries enquiry inquiries inquiry
    office mail email team marketing accounts accounting billing invoice invoices
    finance hr jobs careers recruitment noreply no-reply donotreply do-not-reply
    postmaster webmaster hostmaster abuse security privacy legal compliance
    press media pr newsletter subscribe unsubscribe feedback service customerservice
    general reception front desk bookings orders shop store returns
    """.split()
)

# Consumer mailbox providers. Not rejected by default — plenty of small businesses run on
# them — but flagged, because a B2B list that is mostly consumer domains was not built from
# what its author thinks it was built from.
FREE_MAIL_DOMAINS = frozenset(
    """
    gmail.com googlemail.com yahoo.com yahoo.co.uk ymail.com hotmail.com hotmail.co.uk
    outlook.com live.com msn.com aol.com icloud.com me.com mac.com protonmail.com proton.me
    gmx.com gmx.net mail.com zoho.com yandex.com yandex.ru tutanota.com fastmail.com
    """.split()
)

# Addresses that exist to be thrown away. Always rejected: they cannot be sold to and a
# meaningful share of them are traps.
DISPOSABLE_DOMAINS = frozenset(
    """
    mailinator.com guerrillamail.com 10minutemail.com temp-mail.org throwawaymail.com
    yopmail.com trashmail.com sharklasers.com getnada.com dispostable.com maildrop.cc
    fakeinbox.com tempmail.net mytemp.email spamgourmet.com
    """.split()
)

MAX_EMAIL_LENGTH = 254        # RFC 5321 limit on a forward path
MAX_LOCAL_LENGTH = 64

# Canonical fields the pipeline understands. A mapping may name any subset.
KNOWN_FIELDS = (
    "email", "first_name", "last_name", "full_name", "job_title", "seniority", "department",
    "phone", "linkedin_url", "country", "timezone", "company_name", "website",
    "employee_count", "employee_band", "industry", "segment_value", "jurisdiction",
    "consent_basis", "consent_expires_at", "consent_source", "lia_reference",
)

# Header names commonly seen in exported lists, for --infer-mapping.
HEADER_GUESSES: dict[str, tuple[str, ...]] = {
    "email": ("email", "email address", "e-mail", "work email", "business email", "mail"),
    "first_name": ("first name", "firstname", "first", "given name"),
    "last_name": ("last name", "lastname", "last", "surname", "family name"),
    "full_name": ("name", "contact name", "full name", "contact", "person"),
    "job_title": ("title", "job title", "position", "role", "job"),
    "seniority": ("seniority", "level"),
    "department": ("department", "function", "team"),
    "phone": ("phone", "telephone", "mobile", "phone number", "direct dial"),
    "linkedin_url": ("linkedin", "linkedin url", "linkedin profile"),
    "country": ("country", "location", "country name"),
    "company_name": ("company", "company name", "organisation", "organization", "account"),
    "website": ("website", "domain", "company website", "url", "web"),
    "employee_count": ("employees", "employee count", "headcount", "size", "company size"),
    "industry": ("industry", "sector", "vertical"),
}


class PipelineError(ValueError):
    """Raised when the pipeline cannot run at all."""


# --------------------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------------------


def normalise_email(value: str) -> str:
    """Trim, lowercase, and strip the display-name wrapper some exports leave behind."""
    v = (value or "").strip()
    # "Name <addr@example.com>" -> "addr@example.com"
    if "<" in v and ">" in v:
        start, end = v.rfind("<"), v.rfind(">")
        if start < end:
            v = v[start + 1 : end].strip()
    v = v.strip("\"'` \t\r\n")
    # A few exports prefix with mailto:
    if v.lower().startswith("mailto:"):
        v = v[7:]
    return v.lower()


def normalise_domain(value: str) -> str:
    """Reduce a website column to a bare hostname."""
    v = (value or "").strip().lower()
    for prefix in ("https://", "http://", "//"):
        if v.startswith(prefix):
            v = v[len(prefix) :]
    v = v.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if v.startswith("www."):
        v = v[4:]
    return v.rstrip(".")


def normalise_text(value: str) -> str:
    """Collapse whitespace. Nothing more — this is not the place to guess at capitalisation."""
    return " ".join((value or "").split())


def split_full_name(full: str) -> tuple[str, str]:
    """Split a full name into first and last.

    Crude by design. Names do not decompose reliably, and a wrong guess in a greeting is
    worse than no greeting, so anything ambiguous returns the whole string as the first name
    and the copy fallback handles it.
    """
    parts = normalise_text(full).split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def parse_int(value: str) -> int | None:
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def employee_band(count: int | None) -> str | None:
    """Bucket a headcount. The bands are a default; override them per client if the ICP
    splits somewhere else."""
    if count is None:
        return None
    if count < 10:
        return "1-9"
    if count < 50:
        return "10-49"
    if count < 200:
        return "50-199"
    if count < 500:
        return "200-499"
    if count < 1000:
        return "500-999"
    return "1000+"


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------


def validate_email(email: str) -> tuple[bool, str, str]:
    """Return (ok, reason_code, detail)."""
    if not email:
        return False, "missing_email", "the email column was empty"
    if len(email) > MAX_EMAIL_LENGTH:
        return False, "invalid_email_syntax", f"longer than {MAX_EMAIL_LENGTH} characters"
    if email.count("@") != 1:
        return False, "invalid_email_syntax", f"expected exactly one @, found {email.count('@')}"

    local, _, domain = email.partition("@")
    if len(local) > MAX_LOCAL_LENGTH:
        return False, "invalid_email_syntax", f"local part longer than {MAX_LOCAL_LENGTH}"
    if not EMAIL_RE.match(email):
        return False, "invalid_email_syntax", "does not match the address pattern"
    if ".." in email:
        return False, "invalid_email_syntax", "consecutive dots"
    if domain in DISPOSABLE_DOMAINS:
        return False, "disposable_domain", f"{domain} is a disposable address provider"

    # Strip plus-addressing before the role check, so sales+q1@ is caught.
    base_local = local.split("+", 1)[0]
    if base_local in ROLE_LOCAL_PARTS:
        return False, "role_address", f"{base_local}@ is a role address, not a person"

    return True, "", ""


# --------------------------------------------------------------------------------------
# Mapping
# --------------------------------------------------------------------------------------


def load_mapping(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            mapping = json.load(fh)
    except OSError as exc:
        raise PipelineError(f"could not read mapping {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineError(f"mapping {path!r} is not valid JSON: line {exc.lineno}, {exc.msg}") from exc

    if not isinstance(mapping, dict):
        raise PipelineError(f"mapping {path!r} must contain a JSON object")

    columns = mapping.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise PipelineError("mapping must contain a non-empty 'columns' object")
    if "email" not in columns:
        raise PipelineError("mapping 'columns' must include 'email'; nothing else can be inferred")

    unknown = set(columns) - set(KNOWN_FIELDS)
    if unknown:
        raise PipelineError(
            f"mapping refers to unknown field(s): {', '.join(sorted(unknown))}. "
            f"Known fields: {', '.join(KNOWN_FIELDS)}"
        )

    if not mapping.get("source_name"):
        raise PipelineError(
            "mapping must set 'source_name'. Every contact carries it, and it is how a bad "
            "batch is identified and quarantined later."
        )

    mapping.setdefault("encoding", "utf-8-sig")
    mapping.setdefault("delimiter", ",")
    mapping.setdefault("defaults", {})
    return mapping


def infer_mapping(csv_path: str, encoding: str = "utf-8-sig") -> dict:
    """Guess a mapping from a CSV's headers. A starting point to be checked by a human."""
    try:
        with open(csv_path, encoding=encoding, newline="") as fh:
            reader = csv.reader(fh)
            headers = next(reader, [])
    except OSError as exc:
        raise PipelineError(f"could not read {csv_path!r}: {exc}") from exc

    if not headers:
        raise PipelineError(f"{csv_path!r} has no header row")

    lowered = {h.strip().lower(): h for h in headers if h and h.strip()}
    columns: dict[str, str] = {}
    for field, guesses in HEADER_GUESSES.items():
        for guess in guesses:
            if guess in lowered:
                columns[field] = lowered[guess]
                break

    return {
        "source_name": "REPLACE-ME",
        "source_detail": f"Inferred from {Path(csv_path).name}",
        "encoding": encoding,
        "delimiter": ",",
        "columns": columns,
        "defaults": {"jurisdiction": "REPLACE-ME", "consent_basis": "REPLACE-ME"},
        "_unmapped_headers": [h for h in headers if h not in columns.values()],
        "_note": (
            "Check every mapping before using it. Replace REPLACE-ME values. A wrong column "
            "mapping shows up as a high invalid-syntax rejection rate, not as an error."
        ),
    }


# --------------------------------------------------------------------------------------
# Suppression
# --------------------------------------------------------------------------------------


def load_suppression_file(path: str) -> tuple[set[str], set[str]]:
    """Read a suppression file: one address or domain per line, or a CSV with an email column.

    Returns (addresses, domains). A line with no @ is treated as a whole domain.
    """
    addresses: set[str] = set()
    domains: set[str] = set()
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            has_header = "@" not in sample.split("\n", 1)[0]
            reader = csv.reader(fh)
            for n, row in enumerate(reader):
                if not row:
                    continue
                if n == 0 and has_header:
                    continue
                value = normalise_email(row[0])
                if not value:
                    continue
                if "@" in value:
                    addresses.add(value)
                else:
                    domains.add(value.lstrip("@").lower())
    except OSError as exc:
        raise PipelineError(f"could not read suppression file {path!r}: {exc}") from exc
    return addresses, domains


def load_suppression_db(conn) -> tuple[set[str], set[str]]:
    """Read the active suppression list from Postgres."""
    addresses: set[str] = set()
    domains: set[str] = set()
    with conn.cursor() as cur:
        cur.execute("SELECT email, email_domain FROM active_suppression")
        for email, domain in cur.fetchall():
            if email:
                addresses.add(str(email).lower())
            elif domain:
                domains.add(str(domain).lower())
    return addresses, domains


# --------------------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------------------


def read_rows(csv_path: str, mapping: dict) -> Iterator[tuple[int, dict]]:
    """Yield (row_number, row_dict) from the CSV. Row numbers are 1-based excluding the header."""
    encoding = mapping.get("encoding", "utf-8-sig")
    delimiter = mapping.get("delimiter", ",")
    try:
        with open(csv_path, encoding=encoding, newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            if not reader.fieldnames:
                raise PipelineError(f"{csv_path!r} has no header row")
            missing = [
                src for src in mapping["columns"].values() if src not in reader.fieldnames
            ]
            if missing:
                raise PipelineError(
                    f"mapping refers to column(s) not in the CSV: {', '.join(missing)}. "
                    f"CSV headers are: {', '.join(reader.fieldnames)}"
                )
            for n, row in enumerate(reader, start=1):
                yield n, row
    except UnicodeDecodeError as exc:
        raise PipelineError(
            f"could not decode {csv_path!r} as {encoding}: {exc}. "
            f"Try setting 'encoding' in the mapping to 'cp1252' or 'latin-1'."
        ) from exc
    except OSError as exc:
        raise PipelineError(f"could not read {csv_path!r}: {exc}") from exc


def transform(row: dict, mapping: dict) -> dict:
    """Map a source row onto the canonical fields and normalise every value."""
    columns = mapping["columns"]
    defaults = mapping.get("defaults", {})

    out: dict[str, Any] = {}
    for field, source_column in columns.items():
        out[field] = normalise_text(row.get(source_column) or "")

    for field, value in defaults.items():
        if not out.get(field):
            out[field] = value

    out["email"] = normalise_email(out.get("email", ""))
    out["email_domain"] = out["email"].partition("@")[2] if "@" in out["email"] else ""

    # Derive first/last from a single name column where one was supplied.
    if out.get("full_name") and not (out.get("first_name") or out.get("last_name")):
        out["first_name"], out["last_name"] = split_full_name(out["full_name"])
    elif out.get("first_name") and not out.get("full_name"):
        out["full_name"] = normalise_text(f"{out['first_name']} {out.get('last_name', '')}")

    if out.get("website"):
        out["website"] = normalise_domain(out["website"])

    count = parse_int(out.get("employee_count"))
    out["employee_count"] = count
    if not out.get("employee_band"):
        out["employee_band"] = employee_band(count)

    # The value the segment router reads. Falls back to the band, which is the most common
    # segmentation in practice.
    segment_field = mapping.get("segment_field")
    if not out.get("segment_value"):
        if segment_field and segment_field in out:
            out["segment_value"] = out[segment_field]
        else:
            out["segment_value"] = out.get("employee_band")

    # The account domain is the email domain, not the website column. The website is often
    # a marketing domain that does not match where people actually receive mail.
    out["account_domain"] = out["email_domain"]

    return out


def process(
    csv_path: str,
    mapping: dict,
    suppressed_addresses: set[str],
    suppressed_domains: set[str],
    reject_free_mail: bool = False,
) -> dict:
    """Run the full validation pass. Pure apart from reading the CSV; performs no writes."""
    accepted: list[dict] = []
    rejections: list[dict] = []
    seen_emails: dict[str, int] = {}
    reason_counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    total = 0

    def reject(row_number: int, raw: dict, code: str, detail: str) -> None:
        reason_counts[code] += 1
        rejections.append(
            {
                "row_number": row_number,
                "reason_code": code,
                "reason_detail": detail,
                "payload": raw,
            }
        )

    for row_number, raw in read_rows(csv_path, mapping):
        total += 1
        rec = transform(raw, mapping)
        email = rec["email"]

        ok, code, detail = validate_email(email)
        if not ok:
            reject(row_number, raw, code, detail)
            continue

        if email in seen_emails:
            reject(
                row_number,
                raw,
                "duplicate_in_file",
                f"already seen at row {seen_emails[email]}",
            )
            continue

        if email in suppressed_addresses:
            reject(row_number, raw, "suppressed_address", "address is on the suppression list")
            continue

        if rec["email_domain"] in suppressed_domains:
            reject(
                row_number,
                raw,
                "suppressed_domain",
                f"{rec['email_domain']} is suppressed at the domain level",
            )
            continue

        if rec["email_domain"] in FREE_MAIL_DOMAINS:
            if reject_free_mail:
                reject(
                    row_number,
                    raw,
                    "free_mail_domain",
                    f"{rec['email_domain']} is a consumer mailbox provider",
                )
                continue
            flag_counts["free_mail_domain"] += 1
            rec["_flags"] = ["free_mail_domain"]

        if not rec.get("consent_basis"):
            flag_counts["no_consent_basis"] += 1
            rec.setdefault("_flags", []).append("no_consent_basis")

        seen_emails[email] = row_number
        domain_counts[rec["email_domain"]] += 1
        rec["_row_number"] = row_number
        rec["_raw"] = raw
        accepted.append(rec)

    return {
        "source_name": mapping["source_name"],
        "total_rows": total,
        "accepted": accepted,
        "rejections": rejections,
        "reason_counts": dict(reason_counts),
        "flag_counts": dict(flag_counts),
        "top_domains": domain_counts.most_common(15),
        "distinct_domains": len(domain_counts),
    }


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------


def load_to_postgres(result: dict, mapping: dict, database_url: str) -> dict:
    """Load accepted rows into Postgres. Requires psycopg.

    Runs in one transaction. A partial load leaves an import batch whose counts do not match
    its rows, which is worse than no load.
    """
    try:
        import psycopg
    except ImportError as exc:
        raise PipelineError(
            "psycopg is not installed. Install it with `pip install -r requirements.txt`, "
            "or use --dry-run, which needs no database and no dependencies."
        ) from exc

    accepted = result["accepted"]
    rejections = result["rejections"]
    inserted = 0
    updated = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO import_batch (
                    source_name, source_detail, file_name, row_count,
                    accepted_count, rejected_count, jurisdiction, consent_basis, imported_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    mapping["source_name"],
                    mapping.get("source_detail"),
                    mapping.get("_file_name"),
                    result["total_rows"],
                    len(accepted),
                    len(rejections),
                    mapping.get("defaults", {}).get("jurisdiction"),
                    mapping.get("defaults", {}).get("consent_basis"),
                    os.environ.get("USER") or os.environ.get("USERNAME"),
                ),
            )
            batch_id = cur.fetchone()[0]

            for rec in accepted:
                account_id = None
                if rec.get("account_domain"):
                    cur.execute(
                        """
                        INSERT INTO account (domain, name, employee_count, employee_band,
                                             industry, country, website)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (domain) DO UPDATE SET
                            name           = COALESCE(EXCLUDED.name, account.name),
                            employee_count = COALESCE(EXCLUDED.employee_count, account.employee_count),
                            employee_band  = COALESCE(EXCLUDED.employee_band, account.employee_band),
                            industry       = COALESCE(EXCLUDED.industry, account.industry),
                            country        = COALESCE(EXCLUDED.country, account.country),
                            website        = COALESCE(EXCLUDED.website, account.website),
                            updated_at     = now()
                        RETURNING id
                        """,
                        (
                            rec["account_domain"],
                            rec.get("company_name") or None,
                            rec.get("employee_count"),
                            rec.get("employee_band") or None,
                            rec.get("industry") or None,
                            rec.get("country") or None,
                            rec.get("website") or None,
                        ),
                    )
                    account_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO contact (
                        email, email_domain, account_id, first_name, last_name, full_name,
                        job_title, seniority, department, phone, linkedin_url, country,
                        timezone, segment_value, jurisdiction, consent_basis,
                        consent_source, lia_reference, source_name, first_batch_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (email) DO UPDATE SET
                        account_id    = COALESCE(EXCLUDED.account_id, contact.account_id),
                        first_name    = COALESCE(EXCLUDED.first_name, contact.first_name),
                        last_name     = COALESCE(EXCLUDED.last_name, contact.last_name),
                        full_name     = COALESCE(EXCLUDED.full_name, contact.full_name),
                        job_title     = COALESCE(EXCLUDED.job_title, contact.job_title),
                        segment_value = COALESCE(EXCLUDED.segment_value, contact.segment_value),
                        updated_at    = now()
                    RETURNING id, (xmax = 0) AS was_inserted
                    """,
                    (
                        rec["email"],
                        rec["email_domain"],
                        account_id,
                        rec.get("first_name") or None,
                        rec.get("last_name") or None,
                        rec.get("full_name") or None,
                        rec.get("job_title") or None,
                        rec.get("seniority") or None,
                        rec.get("department") or None,
                        rec.get("phone") or None,
                        rec.get("linkedin_url") or None,
                        rec.get("country") or None,
                        rec.get("timezone") or None,
                        rec.get("segment_value") or None,
                        rec.get("jurisdiction") or None,
                        rec.get("consent_basis") or None,
                        rec.get("consent_source") or None,
                        rec.get("lia_reference") or None,
                        mapping["source_name"],
                        batch_id,
                    ),
                )
                contact_id, was_inserted = cur.fetchone()
                inserted += 1 if was_inserted else 0
                updated += 0 if was_inserted else 1

                cur.execute(
                    """
                    INSERT INTO raw_import (batch_id, row_number, payload, contact_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (batch_id, rec["_row_number"], json.dumps(rec["_raw"]), contact_id),
                )

            for rej in rejections:
                cur.execute(
                    """
                    INSERT INTO import_rejection
                        (batch_id, row_number, payload, reason_code, reason_detail)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        batch_id,
                        rej["row_number"],
                        json.dumps(rej["payload"]),
                        rej["reason_code"],
                        rej["reason_detail"],
                    ),
                )

        conn.commit()

    return {"batch_id": batch_id, "inserted": inserted, "updated": updated}


def write_rejections(path: str, rejections: list[dict]) -> None:
    """Write the rejection log as a CSV, with the original row preserved."""
    if not rejections:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(["row_number", "reason_code", "reason_detail"])
        return

    source_columns: list[str] = []
    for rej in rejections:
        for key in rej["payload"]:
            if key not in source_columns:
                source_columns.append(key)

    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["row_number", "reason_code", "reason_detail", *source_columns])
        for rej in rejections:
            writer.writerow(
                [
                    rej["row_number"],
                    rej["reason_code"],
                    rej["reason_detail"],
                    *[rej["payload"].get(col, "") for col in source_columns],
                ]
            )


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

REASON_NOTES = {
    "missing_email": "The email column was empty. Usually a mapping error rather than a bad list.",
    "invalid_email_syntax": (
        "Not a usable address. A high count here almost always means the email column is "
        "mapped to the wrong CSV column."
    ),
    "role_address": (
        "info@, sales@ and similar. Near-zero reply rate, above-average complaint rate, and a "
        "common source of spam trap hits."
    ),
    "disposable_domain": "A throwaway address provider. Cannot be sold to.",
    "duplicate_in_file": "The same address appeared earlier in this file.",
    "suppressed_address": "On the suppression list. Never sent to again, under any circumstances.",
    "suppressed_domain": "The whole domain is suppressed - usually a customer, partner or competitor.",
    "free_mail_domain": "A consumer mailbox provider, rejected because --reject-free-mail was set.",
}


def render_report(result: dict, load_result: dict | None, dry_run: bool) -> str:
    lines: list[str] = []
    a = lines.append
    total = result["total_rows"]
    accepted = len(result["accepted"])
    rejected = len(result["rejections"])

    a("=" * 78)
    a(f"LIST INGESTION - {result['source_name']}" + ("  [DRY RUN]" if dry_run else ""))
    a("=" * 78)
    a("")
    a(f"  Rows read        {total:,}")
    a(f"  Accepted         {accepted:,}" + (f"  ({accepted / total:.1%})" if total else ""))
    a(f"  Rejected         {rejected:,}" + (f"  ({rejected / total:.1%})" if total else ""))
    a(f"  Distinct domains {result['distinct_domains']:,}")
    a("")

    if result["reason_counts"]:
        a("-" * 78)
        a("REJECTIONS")
        a("-" * 78)
        a(f"  {'COUNT':<9}{'REASON':<24}")
        for code, count in sorted(result["reason_counts"].items(), key=lambda kv: -kv[1]):
            share = f"{count / total:.1%}" if total else ""
            a(f"  {count:<9,}{code:<24}{share}")
        a("")
        for code in sorted(result["reason_counts"]):
            note = REASON_NOTES.get(code)
            if note:
                a(f"  {code}")
                for line in _wrap(note, 70):
                    a(f"      {line}")
                a("")

    if result["flag_counts"]:
        a("-" * 78)
        a("FLAGGED, NOT REJECTED")
        a("-" * 78)
        for code, count in sorted(result["flag_counts"].items(), key=lambda kv: -kv[1]):
            a(f"  {count:<9,}{code}")
        a("")

    if result["top_domains"]:
        a("-" * 78)
        a("TOP DOMAINS")
        a("-" * 78)
        for domain, count in result["top_domains"]:
            a(f"  {count:<9,}{domain}")
        a("")

    # --- The checks that decide whether this list is safe to send to -----------------
    a("-" * 78)
    a("ASSESSMENT")
    a("-" * 78)
    findings: list[str] = []

    invalid = result["reason_counts"].get("invalid_email_syntax", 0)
    if total and invalid / total > 0.05:
        findings.append(
            f"{invalid / total:.0%} of rows failed syntax validation. Above 5% this is "
            f"normally a column mapping error, not a bad list. Check the mapping before "
            f"assuming the source is at fault."
        )

    if total and accepted / total < 0.7:
        findings.append(
            f"Only {accepted / total:.0%} of rows survived. Read the rejection log before "
            f"loading; a list that loses a third of itself at ingestion usually has a "
            f"structural problem."
        )

    free = result["flag_counts"].get("free_mail_domain", 0)
    if accepted and free / accepted > 0.2:
        findings.append(
            f"{free / accepted:.0%} of accepted contacts are on consumer mailbox providers. "
            f"For a B2B list this suggests the source is not what it was assumed to be."
        )

    no_basis = result["flag_counts"].get("no_consent_basis", 0)
    if no_basis:
        findings.append(
            f"{no_basis:,} contacts have no lawful basis recorded. Gate G2 will reject every "
            f"one of them at cadence entry. Set 'consent_basis' in the mapping defaults, per "
            f"jurisdiction, before loading."
        )

    dupes = result["reason_counts"].get("duplicate_in_file", 0)
    if total and dupes / total > 0.1:
        findings.append(
            f"{dupes / total:.0%} of rows were duplicates within the file. The source export "
            f"is probably joining on something that fans out."
        )

    if findings:
        for f in findings:
            for i, line in enumerate(_wrap(f, 72)):
                a(f"  {'! ' if i == 0 else '  '}{line}")
            a("")
    else:
        a("  Nothing unusual. Rejection reasons and rates are within normal ranges.")
        a("")

    a("-" * 78)
    a("NEXT")
    a("-" * 78)
    if dry_run:
        a("  1. Read the rejection log. Confirm every reason is expected.")
        a("  2. Run the accepted addresses through email verification. This is a required")
        a("     gate, not an optimisation: an unverified list is the single most common")
        a("     cause of a burned sending estate.")
        a("  3. Re-run without --dry-run to load.")
    else:
        if load_result:
            a(f"  Batch id         {load_result['batch_id']}")
            a(f"  Contacts created {load_result['inserted']:,}")
            a(f"  Contacts updated {load_result['updated']:,}")
            a("")
        a("  1. Verify the loaded addresses before the first send.")
        a("  2. Run enrichment and scoring; contacts below the threshold are excluded.")
        a("  3. Enrol only contacts appearing in the eligible_contact view.")
    a("")

    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    out = [words[0]]
    for word in words[1:]:
        if len(out[-1]) + 1 + len(word) <= width:
            out[-1] += " " + word
        else:
            out.append(word)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Source-agnostic CSV ingestion for the prospect pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python list_pipeline.py --csv leads.csv --mapping mapping.json --dry-run\n"
        ),
    )
    parser.add_argument("--csv", required=True, help="Path to the source CSV")
    parser.add_argument("--mapping", help="Path to the column-mapping JSON")
    parser.add_argument(
        "--infer-mapping",
        action="store_true",
        help="Print a starter mapping guessed from the CSV headers, and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only. No database, no dependencies, nothing written except --rejections.",
    )
    parser.add_argument(
        "--suppression",
        default=None,
        help="Suppression file for dry runs: one address or domain per line, or a CSV whose "
        "first column is the address. Ignored when loading, which reads the database.",
    )
    parser.add_argument(
        "--rejections", default=None, help="Write the rejection log to this CSV path"
    )
    parser.add_argument(
        "--reject-free-mail",
        action="store_true",
        help="Reject consumer mailbox providers rather than flagging them",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Postgres connection string. Defaults to the DATABASE_URL environment variable.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON summary instead of a report")
    args = parser.parse_args(argv)

    try:
        if args.infer_mapping:
            print(json.dumps(infer_mapping(args.csv), indent=2))
            return 0

        if not args.mapping:
            parser.error("--mapping is required (or use --infer-mapping)")

        mapping = load_mapping(args.mapping)
        mapping["_file_name"] = Path(args.csv).name

        suppressed_addresses: set[str] = set()
        suppressed_domains: set[str] = set()

        database_url = args.database_url or os.environ.get("DATABASE_URL")

        if args.dry_run:
            if args.suppression:
                suppressed_addresses, suppressed_domains = load_suppression_file(args.suppression)
            else:
                print(
                    "warning: no --suppression file supplied, so no suppression check ran. "
                    "The accepted count will be optimistic.",
                    file=sys.stderr,
                )
        else:
            if not database_url:
                raise PipelineError(
                    "no database URL. Set DATABASE_URL or pass --database-url, or use "
                    "--dry-run, which needs neither."
                )
            try:
                import psycopg
            except ImportError as exc:
                raise PipelineError(
                    "psycopg is not installed. Install it with "
                    "`pip install -r requirements.txt`, or use --dry-run."
                ) from exc
            with psycopg.connect(database_url) as conn:
                suppressed_addresses, suppressed_domains = load_suppression_db(conn)

        result = process(
            csv_path=args.csv,
            mapping=mapping,
            suppressed_addresses=suppressed_addresses,
            suppressed_domains=suppressed_domains,
            reject_free_mail=args.reject_free_mail,
        )

        if args.rejections:
            write_rejections(args.rejections, result["rejections"])

        load_result = None
        if not args.dry_run:
            load_result = load_to_postgres(result, mapping, database_url)

    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        summary = {
            "source_name": result["source_name"],
            "total_rows": result["total_rows"],
            "accepted": len(result["accepted"]),
            "rejected": len(result["rejections"]),
            "reason_counts": result["reason_counts"],
            "flag_counts": result["flag_counts"],
            "distinct_domains": result["distinct_domains"],
            "dry_run": args.dry_run,
            "load": load_result,
        }
        print(json.dumps(summary, indent=2))
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(render_report(result, load_result, args.dry_run))

    if args.rejections:
        print(f"Rejection log written to {args.rejections}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

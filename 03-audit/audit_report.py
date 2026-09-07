#!/usr/bin/env python3
"""Render a deliverability audit report from a JSON file of findings.

Reads a findings file matching the structure of sample-input.json and writes the filled
markdown report described by audit-template.md.

Every section is optional. A section that is absent is rendered as "Not assessed" with a note
saying so, rather than being silently dropped or crashing the run — an audit that quietly omits
a section it did not cover is worse than one that says it did not cover it.

Usage:
    python audit_report.py --input sample-input.json
    python audit_report.py --input findings.json --output report.md
    python audit_report.py --input findings.json --check
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_RANK = {s: n for n, s in enumerate(SEVERITY_ORDER)}
EFFORT_RANK = {"low": 0, "medium": 1, "high": 2}

# A section that is present but empty still gets a heading and a "checked, nothing found"
# line. The client is paying for the check, not only for the problems it turned up.
NOT_ASSESSED = (
    "> **Not assessed.** This section was not covered by this audit. See "
    "*What this does not cover* in section 8."
)
NO_FINDINGS = "No findings. Checked, nothing of concern found."

MISSING = "[not provided]"


class AuditError(ValueError):
    """Raised when the input file cannot be turned into a report."""


# --------------------------------------------------------------------------------------
# Safe accessors. Everything below tolerates missing keys, wrong types and nulls, because
# these files are hand-written under time pressure in the middle of an engagement.
# --------------------------------------------------------------------------------------


def get_dict(data: Any, key: str) -> dict:
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, dict) else {}


def get_list(data: Any, key: str) -> list:
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, list) else []


def get_str(data: Any, key: str, default: str = MISSING) -> str:
    value = data.get(key) if isinstance(data, dict) else None
    if value is None or value == "":
        return default
    return str(value)


def has_section(data: dict, key: str) -> bool:
    """True if the section exists at all, even if it holds no findings."""
    return isinstance(data, dict) and key in data and data[key] is not None


def collect_findings(data: dict) -> list[dict]:
    """Gather findings from every section, tagged with the section they came from."""
    findings: list[dict] = []
    for key, label in SECTION_LABELS.items():
        section = get_dict(data, key)
        for f in get_list(section, "findings"):
            if not isinstance(f, dict):
                continue
            tagged = dict(f)
            tagged["_section"] = label
            findings.append(tagged)
    return findings


def sort_findings(findings: list[dict]) -> list[dict]:
    """Order by severity, then by effort ascending, then by title."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_RANK.get(str(f.get("severity", "")).lower(), len(SEVERITY_ORDER)),
            EFFORT_RANK.get(str(f.get("effort", "")).lower(), 1),
            str(f.get("title", "")),
        ),
    )


def count_by_severity(findings: list[dict]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        sev = str(f.get("severity", "")).lower()
        if sev in counts:
            counts[sev] += 1
    return counts


SECTION_LABELS = {
    "authentication": "Authentication",
    "reputation": "Reputation",
    "list_hygiene": "List hygiene",
    "content": "Content and copy",
    "sending_patterns": "Sending patterns",
    "inbox_placement": "Inbox placement",
}


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------


def render_finding(f: dict) -> list[str]:
    """Render one finding as a markdown blockquote."""
    sev = str(f.get("severity", "info")).lower()
    if sev not in SEVERITY_RANK:
        sev = f"{sev} (unrecognised severity)" if sev else "info"
    title = get_str(f, "title", "[untitled finding]")
    lines = [f"> **`{sev}`** — {title}", ">"]
    for label, key in (("Observed", "observed"), ("Impact", "impact"), ("Fix", "fix")):
        lines.append(f"> *{label}:* {get_str(f, key)}")
        lines.append(">")
    lines.pop()  # trailing '>'
    lines.append("")
    return lines


def render_findings_block(section: dict) -> list[str]:
    findings = [f for f in get_list(section, "findings") if isinstance(f, dict)]
    if not findings:
        return [NO_FINDINGS, ""]
    lines: list[str] = []
    for f in sort_findings(findings):
        lines.extend(render_finding(f))
    return lines


def render_kv_table(rows: dict, headers: tuple[str, str] = ("Check", "Result")) -> list[str]:
    """Render a flat dict as a two-column markdown table."""
    if not rows:
        return ["_No values recorded._", ""]
    lines = [f"| {headers[0]} | {headers[1]} |", "|---|---|"]
    for k, v in rows.items():
        label = str(k).replace("_", " ").capitalize()
        lines.append(f"| {label} | {_fmt(v)} |")
    lines.append("")
    return lines


def render_rows_table(rows: list, columns: list[tuple[str, str]]) -> list[str]:
    """Render a list of dicts as a markdown table. `columns` is [(header, key), ...]."""
    rows = [r for r in rows if isinstance(r, dict)]
    if not rows:
        return ["_No rows recorded._", ""]
    lines = [
        "| " + " | ".join(h for h, _ in columns) + " |",
        "|" + "---|" * len(columns),
    ]
    for r in rows:
        lines.append("| " + " | ".join(_fmt(r.get(k)) for _, k in columns) + " |")
    lines.append("")
    return lines


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return MISSING
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def render_report(data: dict) -> str:
    meta = get_dict(data, "meta")
    all_findings = collect_findings(data)
    counts = count_by_severity(all_findings)

    out: list[str] = []
    a = out.append

    # ---- Header ------------------------------------------------------------------
    a(f"# Deliverability Audit — {get_str(meta, 'client_name')}")
    a("")
    a(f"**Prepared by:** {get_str(meta, 'auditor_name')}, {get_str(meta, 'agency_name')}")
    a(f"**Date:** {get_str(meta, 'audit_date')}")
    a(f"**Sending data reviewed:** {get_str(meta, 'audit_period')}")
    domains = get_list(meta, "sending_domains")
    a(f"**Domains in scope:** {', '.join(str(d) for d in domains) if domains else MISSING}")
    a(f"**Primary domain:** {get_str(meta, 'primary_domain')}")
    a(f"**ESP:** {get_str(meta, 'esp')}")
    a("")
    a("---")
    a("")

    # ---- 1. Summary --------------------------------------------------------------
    summary = get_dict(data, "summary")
    a("## 1. Summary")
    a("")
    a(get_str(summary, "narrative", "_No summary written._"))
    a("")
    a(f"**Overall assessment:** {get_str(summary, 'overall_assessment')}")
    a("")
    a("| | Count |")
    a("|---|---|")
    for sev in SEVERITY_ORDER:
        if sev == "info" and counts[sev] == 0:
            continue
        a(f"| {sev.capitalize()} findings | {counts[sev]} |")
    a("")
    a("---")
    a("")

    # ---- 2. Authentication -------------------------------------------------------
    a("## 2. Authentication status")
    a("")
    if not has_section(data, "authentication"):
        a(NOT_ASSESSED)
        a("")
    else:
        section = get_dict(data, "authentication")
        a(
            "Whether receiving mail servers can verify that mail claiming to be from these "
            "domains actually is."
        )
        a("")
        out.extend(
            render_rows_table(
                get_list(section, "domains"),
                [
                    ("Domain", "domain"),
                    ("SPF", "spf"),
                    ("DKIM", "dkim"),
                    ("DMARC", "dmarc"),
                    ("Policy", "policy"),
                    ("Aligned", "aligned"),
                ],
            )
        )
        out.extend(render_findings_block(section))
    a("---")
    a("")

    # ---- 3. Reputation -----------------------------------------------------------
    a("## 3. Domain and IP reputation")
    a("")
    if not has_section(data, "reputation"):
        a(NOT_ASSESSED)
        a("")
    else:
        section = get_dict(data, "reputation")
        out.extend(render_kv_table(get_dict(section, "checks")))
        out.extend(render_findings_block(section))
    a("---")
    a("")

    # ---- 4. List hygiene ---------------------------------------------------------
    a("## 4. List hygiene")
    a("")
    if not has_section(data, "list_hygiene"):
        a(NOT_ASSESSED)
        a("")
    else:
        section = get_dict(data, "list_hygiene")
        out.extend(
            render_kv_table(get_dict(section, "metrics"), headers=("Metric", "Value"))
        )
        out.extend(render_findings_block(section))
    a("---")
    a("")

    # ---- 5. Content --------------------------------------------------------------
    a("## 5. Content and copy risk")
    a("")
    if not has_section(data, "content"):
        a(NOT_ASSESSED)
        a("")
    else:
        section = get_dict(data, "content")
        out.extend(render_kv_table(get_dict(section, "checks")))
        out.extend(render_findings_block(section))
    a("---")
    a("")

    # ---- 6. Sending patterns -----------------------------------------------------
    a("## 6. Sending patterns")
    a("")
    if not has_section(data, "sending_patterns"):
        a(NOT_ASSESSED)
        a("")
    else:
        section = get_dict(data, "sending_patterns")
        out.extend(
            render_kv_table(get_dict(section, "metrics"), headers=("Metric", "Value"))
        )
        out.extend(render_findings_block(section))
    a("---")
    a("")

    # ---- 7. Inbox placement ------------------------------------------------------
    a("## 7. Inbox placement")
    a("")
    if not has_section(data, "inbox_placement"):
        a(NOT_ASSESSED)
        a("")
    else:
        section = get_dict(data, "inbox_placement")
        a(
            "Results from seed testing: sending the client's actual production message to "
            "accounts held across the major mailbox providers and recording where each landed."
        )
        a("")
        out.extend(
            render_rows_table(
                get_list(section, "results"),
                [
                    ("Provider", "provider"),
                    ("Inbox", "inbox"),
                    ("Promotions / other", "promotions"),
                    ("Spam", "spam"),
                    ("Not delivered", "not_delivered"),
                ],
            )
        )
        test = get_dict(section, "test")
        if test:
            a("**Test details**")
            a("")
            a(f"- Message tested: {get_str(test, 'message')}")
            a(f"- Sending domain tested: {get_str(test, 'sending_domain')}")
            a(f"- Date of test: {get_str(test, 'date')}")
            a("")
        overall = section.get("overall_placement_rate")
        if overall not in (None, ""):
            a(f"**Overall inbox placement:** {_fmt(overall)}")
            a("")
        out.extend(render_findings_block(section))
    a("---")
    a("")

    # ---- 8. Remediation ----------------------------------------------------------
    # Built from every finding in the report, so the plan cannot drift out of step with
    # the sections above.
    a("## 8. Prioritized remediation")
    a("")
    if not all_findings:
        a("No remediation required. No findings were raised in any assessed section.")
        a("")
    else:
        a("Ordered by severity, then by effort.")
        a("")
        a("| # | Severity | Section | Finding | Fix | Effort | Owner | Target |")
        a("|---|---|---|---|---|---|---|---|")
        for n, f in enumerate(sort_findings(all_findings), start=1):
            a(
                f"| {n} | `{_fmt(f.get('severity'))}` | {_fmt(f.get('_section'))} "
                f"| {_fmt(f.get('title'))} | {_fmt(f.get('fix'))} | {_fmt(f.get('effort'))} "
                f"| {_fmt(f.get('owner'))} | {_fmt(f.get('target'))} |"
            )
        a("")

    remediation = get_dict(data, "remediation")
    sequencing = remediation.get("sequencing_note")
    a("**Sequencing note**")
    a("")
    a(
        str(sequencing)
        if sequencing
        else (
            "Authentication findings are fixed first: reputation work on a domain that fails "
            "authentication is wasted. List hygiene is fixed before any volume change."
        )
    )
    a("")

    a("**What this does not cover**")
    a("")
    limitations = get_list(remediation, "limitations")
    if limitations:
        for lim in limitations:
            a(f"- {_fmt(lim)}")
    else:
        a("_No limitations recorded. State them explicitly before sending this to a client._")
    a("")

    unassessed = [
        label for key, label in SECTION_LABELS.items() if not has_section(data, key)
    ]
    if unassessed:
        a(
            f"The following sections were not assessed: "
            f"{', '.join(unassessed)}. No conclusion should be drawn about them from this report."
        )
        a("")

    # ---- Appendices --------------------------------------------------------------
    appendix = get_dict(data, "appendix")
    a("---")
    a("")
    a("## Appendix A — Raw check output")
    a("")
    raw = appendix.get("raw_output")
    if raw:
        a("```")
        a(str(raw).rstrip())
        a("```")
    else:
        a("_No raw output recorded._")
    a("")

    a("## Appendix B — Glossary")
    a("")
    a("| Term | Meaning |")
    a("|---|---|")
    for term, meaning in GLOSSARY:
        a(f"| {term} | {meaning} |")
    a("")

    return "\n".join(out)


GLOSSARY = [
    ("SPF", "A DNS record naming which servers may send mail for a domain"),
    (
        "DKIM",
        "A cryptographic signature on each message proving it was not altered and came from "
        "an authorised sender",
    ),
    (
        "DMARC",
        "A DNS record telling receivers what to do with mail that fails SPF and DKIM, and "
        "where to send reports",
    ),
    (
        "Alignment",
        "Whether the domain shown in the From: header matches the domain that SPF or DKIM "
        "authenticated",
    ),
    (
        "Seed test",
        "Sending the real message to accounts across the major providers to observe where it lands",
    ),
    (
        "Warmup",
        "Building a sending history on a new domain by starting at very low volume and ramping "
        "gradually",
    ),
    ("Suppression list", "The record of addresses that must never be sent to again"),
    (
        "Spam trap",
        "An address that exists only to catch senders using unverified or purchased lists",
    ),
    ("Hard bounce", "Permanent delivery failure, usually because the address does not exist"),
    ("Complaint rate", "The proportion of recipients who mark a message as spam"),
]


# --------------------------------------------------------------------------------------
# Input checking
# --------------------------------------------------------------------------------------


def check_input(data: dict) -> list[str]:
    """Return a list of warnings about the input. Never raises; warnings are advisory."""
    warnings: list[str] = []

    meta = get_dict(data, "meta")
    for field in ("client_name", "auditor_name", "audit_date", "audit_period"):
        if not meta.get(field):
            warnings.append(f"meta.{field} is missing; the report header will show {MISSING}")

    if not get_dict(data, "summary").get("narrative"):
        warnings.append("summary.narrative is missing; section 1 will be empty")

    for key, label in SECTION_LABELS.items():
        if not has_section(data, key):
            warnings.append(f"section '{key}' ({label}) absent; will render as Not assessed")

    for f in collect_findings(data):
        sev = str(f.get("severity", "")).lower()
        title = f.get("title", "[untitled]")
        if sev not in SEVERITY_RANK:
            warnings.append(
                f"finding {title!r} has severity {f.get('severity')!r}, "
                f"not one of {', '.join(SEVERITY_ORDER)}"
            )
        for field in ("observed", "impact", "fix"):
            if not f.get(field):
                warnings.append(f"finding {title!r} is missing '{field}'")
        if sev in ("critical", "high") and not f.get("owner"):
            warnings.append(f"{sev} finding {title!r} has no owner assigned")

    if not get_list(get_dict(data, "remediation"), "limitations"):
        warnings.append(
            "remediation.limitations is empty; state what the audit did not cover before "
            "sending it to a client"
        )

    return warnings


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise AuditError(f"could not read {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"{path!r} is not valid JSON: line {exc.lineno}, {exc.msg}") from exc
    if not isinstance(data, dict):
        raise AuditError(f"{path!r} must contain a JSON object at the top level")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a deliverability audit report from a JSON findings file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python audit_report.py --input sample-input.json --output report.md\n",
    )
    parser.add_argument("--input", required=True, help="Path to the JSON findings file")
    parser.add_argument(
        "--output", default=None, help="Write markdown here instead of stdout"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report problems with the input file and exit without rendering",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress input warnings on stderr"
    )
    args = parser.parse_args(argv)

    try:
        data = load(args.input)
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    warnings = check_input(data)

    if args.check:
        if warnings:
            print(f"{len(warnings)} issue(s) in {args.input}:")
            for w in warnings:
                print(f"  - {w}")
            return 1
        print(f"{args.input}: no issues found.")
        return 0

    if warnings and not args.quiet:
        print(f"warning: {len(warnings)} issue(s) in input:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
        print(file=sys.stderr)

    report = render_report(data)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(report + "\n")
        except OSError as exc:
            print(f"error: could not write {args.output!r}: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

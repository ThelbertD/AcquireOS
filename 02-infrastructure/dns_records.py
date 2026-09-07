#!/usr/bin/env python3
"""Generate the DNS record set for a cold-email sending domain.

Produces a copy-pasteable table of SPF, DKIM, DMARC, MX and tracking records for one sending
domain on one email service provider. With --verify it also explains what each record does and
how to confirm it took effect, so the same output doubles as a client-facing explanation.

This makes no network calls. It does not query DNS, does not talk to a registrar, and does not
talk to an ESP. It emits records a human enters at the DNS host.

Usage:
    python dns_records.py --domain example-hq.com --esp google-workspace
    python dns_records.py --domain example-hq.com --esp microsoft-365 --verify
    python dns_records.py --domain example-hq.com --esp generic --json
    python dns_records.py --domain example-hq.com --esp-config my-esp.json
    python dns_records.py --list-esps

Provider values below come from each provider's public documentation and are stable, but they
do change. Confirm the SPF include and MX hosts in the provider's own admin console before
publishing. The DKIM key is always issued per domain by the provider and is never guessable —
it is emitted as a placeholder for you to paste over.
"""

from __future__ import annotations

import argparse
import json
import sys

# --------------------------------------------------------------------------------------
# ESP profiles.
#
# `spf_include`   the include: mechanism the provider requires in SPF
# `mx`            (priority, host) pairs, in the order the provider documents them
# `dkim_selector` the default selector the provider issues; overridable with --dkim-selector
# `dkim_note`     where in the provider's console the key is generated
# --------------------------------------------------------------------------------------

ESP_PROFILES: dict[str, dict] = {
    "generic": {
        "label": "Generic / other provider",
        "spf_include": "{{SPF_INCLUDE}}",
        "mx": [(10, "{{MX_HOST}}")],
        "dkim_selector": "{{DKIM_SELECTOR}}",
        "dkim_note": (
            "Look up the provider's SPF include, MX hosts and DKIM selector in their "
            "documentation, or supply them with --esp-config."
        ),
    },
    "google-workspace": {
        "label": "Google Workspace",
        "spf_include": "_spf.google.com",
        "mx": [(1, "smtp.google.com")],
        "dkim_selector": "google",
        "dkim_note": (
            "Admin console > Apps > Google Workspace > Gmail > Authenticate email. "
            "Generate a 2048-bit key, publish the TXT record, then click Start Authentication."
        ),
    },
    "microsoft-365": {
        "label": "Microsoft 365",
        "spf_include": "spf.protection.outlook.com",
        "mx": [(0, "{{MX_HOST}}")],
        "dkim_selector": "selector1",
        "dkim_note": (
            "Microsoft 365 publishes DKIM as two CNAMEs (selector1, selector2) pointing at "
            "the tenant's onmicrosoft.com domain, not as a TXT key. The MX host is "
            "tenant-specific and shown in the Microsoft 365 admin centre under Domains. "
            "Take both from the admin centre."
        ),
        "dkim_style": "cname",
    },
}

# Records that are not required to send but that measurably help. Emitted as optional.
OPTIONAL_RECORDS_NOTE = (
    "MTA-STS and TLS-RPT are optional. They enforce and report on TLS for inbound mail. "
    "They do not affect cold-send deliverability and add a hosted policy file to maintain. "
    "Skip them unless the client already runs them on the primary domain."
)


class RecordError(ValueError):
    """Raised when the inputs cannot produce a valid record set."""


def validate_domain(domain: str) -> str:
    """Check a domain is syntactically usable and return it normalized."""
    d = domain.strip().lower().rstrip(".")
    if not d:
        raise RecordError("domain is empty")
    if "@" in d:
        raise RecordError(f"{domain!r} looks like an email address, not a domain")
    if "/" in d or ":" in d:
        raise RecordError(f"{domain!r} looks like a URL; pass the bare domain")
    if "." not in d:
        raise RecordError(f"{domain!r} has no dot; expected something like example-hq.com")
    labels = d.split(".")
    if any(not label for label in labels):
        raise RecordError(f"{domain!r} has an empty label")
    if any(len(label) > 63 for label in labels):
        raise RecordError(f"{domain!r} has a label longer than 63 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-.")
    if set(d) - allowed:
        raise RecordError(f"{domain!r} contains characters not valid in a hostname")
    return d


def load_esp(esp: str | None, esp_config: str | None) -> tuple[str, dict]:
    """Resolve the ESP profile from either a built-in name or a JSON config file."""
    if esp_config:
        try:
            with open(esp_config, encoding="utf-8") as fh:
                profile = json.load(fh)
        except OSError as exc:
            raise RecordError(f"could not read ESP config {esp_config!r}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RecordError(f"ESP config {esp_config!r} is not valid JSON: {exc}") from exc

        missing = [k for k in ("spf_include", "mx") if k not in profile]
        if missing:
            raise RecordError(
                f"ESP config is missing required key(s): {', '.join(missing)}. "
                f"Required: spf_include, mx. Optional: label, dkim_selector, dkim_note, dkim_style."
            )
        profile.setdefault("label", esp_config)
        profile.setdefault("dkim_selector", "{{DKIM_SELECTOR}}")
        profile.setdefault("dkim_note", "Generate the DKIM key in the provider's console.")
        # JSON has no tuples; accept [priority, host] pairs.
        try:
            profile["mx"] = [(int(p), str(h)) for p, h in profile["mx"]]
        except (TypeError, ValueError) as exc:
            raise RecordError(
                f"ESP config 'mx' must be a list of [priority, host] pairs: {exc}"
            ) from exc
        return profile["label"], profile

    name = (esp or "generic").strip().lower()
    if name not in ESP_PROFILES:
        raise RecordError(
            f"unknown ESP {name!r}. Known: {', '.join(sorted(ESP_PROFILES))}. "
            f"For anything else use --esp generic, or supply --esp-config with a JSON file."
        )
    return name, ESP_PROFILES[name]


def build_records(
    domain: str,
    esp: str | None = None,
    esp_config: str | None = None,
    dkim_selector: str | None = None,
    rua: str = "{{DMARC_RUA_ADDRESS}}",
    tracking_subdomain: str | None = None,
    tracking_target: str = "{{TRACKING_CNAME_TARGET}}",
    include_tracking: bool = True,
) -> dict:
    """Build the full record set for one sending domain. Pure function; no I/O beyond config load."""
    d = validate_domain(domain)
    esp_name, profile = load_esp(esp, esp_config)
    selector = dkim_selector or profile["dkim_selector"]
    track_host = tracking_subdomain or "track"

    records: list[dict] = []

    # ---- SPF ----------------------------------------------------------------------
    # One SPF record per domain, always. Two SPF TXT records is a permerror and fails
    # authentication outright. ~all (softfail) rather than -all (hardfail) while warming:
    # a hardfail on a misconfigured estate discards mail silently instead of soft-landing it.
    records.append(
        {
            "type": "TXT",
            "host": "@",
            "fqdn": d,
            "value": f"v=spf1 include:{profile['spf_include']} ~all",
            "ttl": 3600,
            "purpose": "SPF",
            "explanation": (
                "Names the servers allowed to send mail claiming to be from this domain. A "
                "receiving server checks the connecting IP against this list. Exactly one SPF "
                "record may exist per domain: a second one is a permanent error and breaks "
                "authentication for every message. '~all' softfails everything not listed, "
                "which is the correct setting while the estate is new."
            ),
            "check": f'dig +short TXT {d} | grep spf1',
        }
    )

    # ---- DKIM ---------------------------------------------------------------------
    if profile.get("dkim_style") == "cname":
        for n in (1, 2):
            records.append(
                {
                    "type": "CNAME",
                    "host": f"selector{n}._domainkey",
                    "fqdn": f"selector{n}._domainkey.{d}",
                    "value": "{{DKIM_PUBLIC_KEY}}",
                    "ttl": 3600,
                    "purpose": f"DKIM (selector{n})",
                    "explanation": (
                        "This provider serves the DKIM key itself and has the domain point at "
                        "it, rather than publishing the key in the domain's own zone. Both "
                        "selectors are required; the provider rotates between them. The target "
                        "hostname is shown in the provider's console after domain verification."
                    ),
                    "check": f"dig +short CNAME selector{n}._domainkey.{d}",
                }
            )
    else:
        records.append(
            {
                "type": "TXT",
                "host": f"{selector}._domainkey",
                "fqdn": f"{selector}._domainkey.{d}",
                "value": "v=DKIM1; k=rsa; p={{DKIM_PUBLIC_KEY}}",
                "ttl": 3600,
                "purpose": "DKIM",
                "explanation": (
                    "Publishes the public half of the key the provider signs outgoing mail "
                    "with. A receiving server verifies the signature on the message against "
                    "this key, which proves the message was not altered in transit and did "
                    "come from a sender holding the private key. Use a 2048-bit key. Some DNS "
                    "hosts require a 2048-bit value to be split into multiple quoted strings; "
                    "the host will do this automatically or tell you to."
                ),
                "check": f"dig +short TXT {selector}._domainkey.{d}",
            }
        )

    # ---- DMARC --------------------------------------------------------------------
    # Starts at p=none. Monitoring first is not caution for its own sake: publishing
    # p=reject on a domain whose alignment has never been observed will silently destroy
    # legitimate mail, including the client's own.
    records.append(
        {
            "type": "TXT",
            "host": "_dmarc",
            "fqdn": f"_dmarc.{d}",
            "value": (
                f"v=DMARC1; p=none; rua=mailto:{rua}; "
                f"adkim=r; aspf=r; fo=1; pct=100"
            ),
            "ttl": 3600,
            "purpose": "DMARC",
            "explanation": (
                "Tells receiving servers what to do with mail that fails SPF and DKIM, and "
                "where to send reports. 'p=none' means take no action, only report. Start "
                "here on every new domain: it produces the evidence needed to move to "
                "quarantine and then reject without breaking legitimate mail. 'rua' is the "
                "mailbox that receives the daily aggregate reports; it must exist and must be "
                "read. 'adkim=r' and 'aspf=r' are relaxed alignment, which allows a subdomain "
                "to authenticate against the parent domain."
            ),
            "check": f"dig +short TXT _dmarc.{d}",
        }
    )

    # ---- MX -----------------------------------------------------------------------
    # A sending domain that cannot receive mail is a spam signal and, worse, means replies
    # and bounces are lost. Every sending domain accepts inbound mail.
    for priority, host in profile["mx"]:
        records.append(
            {
                "type": "MX",
                "host": "@",
                "fqdn": d,
                "value": f"{priority} {host}",
                "ttl": 3600,
                "purpose": "MX",
                "explanation": (
                    "Names the server that accepts inbound mail for this domain. A sending "
                    "domain with no MX record looks disposable to filters, and it loses every "
                    "reply and every bounce notification. The lower the priority number, the "
                    "more preferred the host."
                ),
                "check": f"dig +short MX {d}",
            }
        )

    # ---- Tracking CNAME -----------------------------------------------------------
    if include_tracking:
        records.append(
            {
                "type": "CNAME",
                "host": track_host,
                "fqdn": f"{track_host}.{d}",
                "value": tracking_target,
                "ttl": 3600,
                "purpose": "Tracking (optional)",
                "explanation": (
                    "Serves open and click tracking from a hostname on this domain rather "
                    "than from the sending platform's shared domain. Shared tracking domains "
                    "are widely blocklisted, and a link pointing at one is a reliable way into "
                    "a spam folder. Only publish this if tracking is actually in use. Keep "
                    "open tracking off during warmup and keep click tracking off in the first "
                    "message of any sequence."
                ),
                "check": f"dig +short CNAME {track_host}.{d}",
            }
        )

    return {
        "domain": d,
        "esp": esp_name,
        "esp_label": profile["label"],
        "dkim_selector": selector,
        "dkim_note": profile["dkim_note"],
        "records": records,
        "optional_note": OPTIONAL_RECORDS_NOTE,
    }


def render_table(rs: dict) -> str:
    """Render the record set as a copy-pasteable table."""
    lines: list[str] = []
    lines.append("=" * 100)
    lines.append(f"DNS RECORDS - {rs['domain']}  ({rs['esp_label']})")
    lines.append("=" * 100)
    lines.append("")
    lines.append("Enter these at the DNS host for this domain. Values in {{DOUBLE_BRACES}} are")
    lines.append("placeholders you replace before publishing - see VARIABLES.md.")
    lines.append("")

    widths = (7, 26, 5, 55)
    header = (
        f"{'TYPE':<{widths[0]}}{'HOST':<{widths[1]}}{'TTL':<{widths[2]}}{'VALUE':<{widths[3]}}"
    )
    lines.append(header)
    lines.append("-" * 100)
    for r in rs["records"]:
        value_lines = _wrap(r["value"], widths[3])
        lines.append(
            f"{r['type']:<{widths[0]}}{r['host']:<{widths[1]}}{r['ttl']:<{widths[2]}}{value_lines[0]}"
        )
        pad = " " * (widths[0] + widths[1] + widths[2])
        for cont in value_lines[1:]:
            lines.append(f"{pad}{cont}")
    lines.append("-" * 100)
    lines.append("")

    lines.append("DKIM KEY")
    lines.append("-" * 100)
    for line in _wrap(rs["dkim_note"], 96):
        lines.append(f"  {line}")
    lines.append("")
    lines.append("  The DKIM public key is issued per domain and cannot be generated here.")
    lines.append("  Publish every other record first, then generate the key and publish it last.")
    lines.append("")

    lines.append("ORDER OF OPERATIONS")
    lines.append("-" * 100)
    lines.append("  1. Publish MX, SPF and DMARC.")
    lines.append("  2. Wait for propagation and confirm with the check commands below.")
    lines.append("  3. Generate the DKIM key in the provider's console, publish it, then")
    lines.append("     activate signing in the console. Activating before the record resolves")
    lines.append("     causes the provider to sign with a key receivers cannot find, which")
    lines.append("     fails DKIM on every message sent in the meantime.")
    lines.append("  4. Publish the tracking CNAME only if tracking will be used.")
    lines.append("  5. Send one message to a seed address and read the raw headers. All three")
    lines.append("     of spf=pass, dkim=pass and dmarc=pass must appear before any warmup")
    lines.append("     traffic starts.")
    lines.append("")

    lines.append("VERIFICATION")
    lines.append("-" * 100)
    lines.append("  Records can take up to the TTL of the previous record to propagate; on a")
    lines.append("  new domain this is usually minutes. Check each one:")
    lines.append("")
    for r in rs["records"]:
        lines.append(f"  # {r['purpose']}")
        lines.append(f"  {r['check']}")
    lines.append("")
    lines.append("  On Windows without dig, substitute:")
    lines.append(f"  nslookup -type=TXT {rs['domain']}")
    lines.append("")

    lines.append("NOT INCLUDED")
    lines.append("-" * 100)
    for line in _wrap(rs["optional_note"], 96):
        lines.append(f"  {line}")
    lines.append("")
    lines.append("  BIMI requires a registered trademark and a Verified Mark Certificate, and")
    lines.append("  it only applies once DMARC is at quarantine or reject. It is not part of a")
    lines.append("  cold sending build.")
    lines.append("")

    return "\n".join(lines)


def render_verify(rs: dict) -> str:
    """Render the client-facing explanation of what each record does."""
    lines: list[str] = []
    lines.append("=" * 88)
    lines.append(f"WHAT THESE RECORDS DO - {rs['domain']}")
    lines.append("=" * 88)
    lines.append("")
    for line in _wrap(
        "Three of the records below are the email authentication set. Together they let a "
        "receiving mail server answer one question: is this message really from this domain? "
        "A domain that cannot answer it convincingly does not reach the inbox, no matter how "
        "good the message is.",
        84,
    ):
        lines.append(line)
    lines.append("")

    for n, r in enumerate(rs["records"], start=1):
        lines.append("-" * 88)
        lines.append(f"{n}. {r['purpose']}   [{r['type']} record on {r['fqdn']}]")
        lines.append("-" * 88)
        for line in _wrap(r["explanation"], 84):
            lines.append(f"  {line}")
        lines.append("")
        lines.append("  Value:")
        for line in _wrap(r["value"], 80):
            lines.append(f"    {line}")
        lines.append("")
        lines.append(f"  Confirm with:  {r['check']}")
        lines.append("")

    lines.append("=" * 88)
    lines.append("WHY DMARC STARTS AT p=none")
    lines.append("=" * 88)
    for line in _wrap(
        "A DMARC policy of 'reject' tells the world to throw away any mail from this domain "
        "that fails authentication. That is the destination, not the starting point. Published "
        "on day one, it will discard legitimate mail from any system nobody remembered to "
        "authorise, silently, with no bounce. The correct sequence is: publish p=none, read "
        "the aggregate reports for two to four weeks until every legitimate sending source is "
        "accounted for and passing, move to p=quarantine, watch for a further two weeks, then "
        "move to p=reject. Each step is a one-line change to the same record.",
        84,
    ):
        lines.append(line)
    lines.append("")

    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    """Wrap text to `width`, returning a list of lines."""
    words = text.split()
    if not words:
        return [""]
    lines = [words[0]]
    for word in words[1:]:
        if len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the DNS record set for a cold-email sending domain.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python dns_records.py --domain example-hq.com --esp google-workspace --verify\n"
        ),
    )
    parser.add_argument("--domain", help="The sending domain, e.g. example-hq.com")
    parser.add_argument(
        "--esp",
        default=None,
        help="Built-in ESP profile name. Use --list-esps to see them. Default: generic",
    )
    parser.add_argument(
        "--esp-config",
        default=None,
        help="Path to a JSON file describing an ESP not built in. "
        'Keys: spf_include (str, required), mx ([[priority, host], ...], required), '
        "label, dkim_selector, dkim_note, dkim_style.",
    )
    parser.add_argument(
        "--dkim-selector", default=None, help="Override the ESP profile's default DKIM selector"
    )
    parser.add_argument(
        "--rua",
        default="{{DMARC_RUA_ADDRESS}}",
        help="Mailbox receiving DMARC aggregate reports",
    )
    parser.add_argument(
        "--tracking-subdomain",
        default=None,
        help="Hostname label for the tracking CNAME (default: track)",
    )
    parser.add_argument(
        "--tracking-target",
        default="{{TRACKING_CNAME_TARGET}}",
        help="Host the tracking CNAME points at",
    )
    parser.add_argument(
        "--no-tracking", action="store_true", help="Omit the tracking CNAME entirely"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Also print a plain-English explanation of every record, suitable to send to a client",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    parser.add_argument(
        "--list-esps", action="store_true", help="List the built-in ESP profiles and exit"
    )
    args = parser.parse_args(argv)

    if args.list_esps:
        print("Built-in ESP profiles:")
        print()
        for name, profile in sorted(ESP_PROFILES.items()):
            print(f"  {name:<20}{profile['label']}")
            print(f"  {'':<20}SPF include: {profile['spf_include']}")
            mx = ", ".join(f"{p} {h}" for p, h in profile["mx"])
            print(f"  {'':<20}MX:          {mx}")
            print()
        print("For any other provider use --esp generic, or supply --esp-config with a JSON file.")
        return 0

    if not args.domain:
        parser.error("--domain is required (or use --list-esps)")

    try:
        rs = build_records(
            domain=args.domain,
            esp=args.esp,
            esp_config=args.esp_config,
            dkim_selector=args.dkim_selector,
            rua=args.rua,
            tracking_subdomain=args.tracking_subdomain,
            tracking_target=args.tracking_target,
            include_tracking=not args.no_tracking,
        )
    except RecordError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(rs, indent=2))
        return 0

    print(render_table(rs))
    if args.verify:
        print()
        print(render_verify(rs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

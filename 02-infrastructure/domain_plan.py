#!/usr/bin/env python3
"""Plan a cold-email sending estate from a primary domain and a target volume.

Given a brand domain and how many emails a month the client needs to send, this works out
how many secondary domains to register, how many mailboxes to put on each, and what each
mailbox may send per day at steady state. It shows the arithmetic so the recommendation can
be argued with rather than taken on faith.

This performs no network calls. It does not check domain availability, does not register
anything, and does not touch an ESP. It produces a plan a human executes.

Usage:
    python domain_plan.py --primary-domain example.com --monthly-volume 20000
    python domain_plan.py --primary-domain example.com --monthly-volume 20000 --json
    python domain_plan.py --primary-domain example.com --monthly-volume 6000 \\
        --daily-ceiling 30 --mailboxes-per-domain 2 --sending-days 20
"""

from __future__ import annotations

import argparse
import json
import math
import sys

# --------------------------------------------------------------------------------------
# Defaults. These are deliberately conservative. Raise them only with evidence from a
# specific client's own sending history, not because a vendor's marketing page says you can.
# --------------------------------------------------------------------------------------

# Cold sends per mailbox per day once a domain is fully warmed. Mailbox providers throttle
# and filter on per-mailbox behaviour, so this is the unit that actually constrains volume.
DEFAULT_DAILY_CEILING = 40

# Mailboxes per sending domain. More than this concentrates risk: one domain-level
# reputation problem takes every mailbox on it out of service at the same time.
DEFAULT_MAILBOXES_PER_DOMAIN = 3

# Business days in a month. Cold outbound sends on weekdays.
DEFAULT_SENDING_DAYS = 22

# Spare capacity held back so a single domain can be pulled from rotation without the
# estate falling below the target volume.
DEFAULT_HEADROOM = 0.20

# Hard ceilings that indicate the plan has left the range this system is designed for.
MAX_REASONABLE_DOMAINS = 40
MAX_DAILY_CEILING = 100


class PlanError(ValueError):
    """Raised when the inputs cannot produce a sane plan."""


def validate_domain(domain: str) -> str:
    """Check a domain is syntactically usable and return it normalized.

    Deliberately permissive: this is a typo check, not a registry lookup.
    """
    d = domain.strip().lower().rstrip(".")
    if not d:
        raise PlanError("primary domain is empty")
    if "@" in d:
        raise PlanError(f"{domain!r} looks like an email address, not a domain")
    if "/" in d or ":" in d:
        raise PlanError(f"{domain!r} looks like a URL; pass the bare domain")
    if "." not in d:
        raise PlanError(f"{domain!r} has no dot; expected something like example.com")
    labels = d.split(".")
    if any(not label for label in labels):
        raise PlanError(f"{domain!r} has an empty label")
    if any(len(label) > 63 for label in labels):
        raise PlanError(f"{domain!r} has a label longer than 63 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-.")
    if set(d) - allowed:
        raise PlanError(f"{domain!r} contains characters not valid in a hostname")
    if any(label.startswith("-") or label.endswith("-") for label in labels):
        raise PlanError(f"{domain!r} has a label starting or ending with a hyphen")
    return d


def split_domain(domain: str) -> tuple[str, str]:
    """Split a domain into (stem, suffix).

    Handles the common two-part public suffixes without shipping a copy of the public
    suffix list. Getting this wrong only affects the cosmetic name suggestions, never the
    arithmetic, so the crude version is acceptable here.
    """
    two_part_suffixes = {
        "co.uk", "org.uk", "me.uk", "ac.uk", "gov.uk", "net.uk", "sch.uk",
        "com.au", "net.au", "org.au", "edu.au", "gov.au",
        "co.nz", "net.nz", "org.nz",
        "co.za", "org.za",
        "com.br", "com.mx", "com.sg", "com.hk", "co.jp", "co.in", "co.il",
    }
    parts = domain.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in two_part_suffixes:
        return ".".join(parts[:-2]), ".".join(parts[-2:])
    return ".".join(parts[:-1]), parts[-1]


# Name patterns for secondary domains, ordered by how well they usually survive a
# prospect's sniff test. A prospect who searches the domain should land somewhere that
# plausibly belongs to the client, so every one of these gets redirected to the primary.
NAME_PATTERNS: list[tuple[str, str]] = [
    ("get{stem}.{suffix}", "verb prefix, reads as a product landing domain"),
    ("{stem}hq.{suffix}", "suffix implying head office"),
    ("try{stem}.{suffix}", "verb prefix, common for trials"),
    ("{stem}-team.{suffix}", "hyphenated team suffix"),
    ("{stem}app.{suffix}", "product suffix, only if the client sells software"),
    ("{stem}group.{suffix}", "corporate suffix"),
    ("go{stem}.{suffix}", "verb prefix"),
    ("{stem}-hq.{suffix}", "hyphenated head office variant"),
    ("join{stem}.{suffix}", "verb prefix"),
    ("{stem}co.{suffix}", "company suffix"),
    ("with{stem}.{suffix}", "preposition prefix"),
    ("{stem}-group.{suffix}", "hyphenated corporate suffix"),
]

ALTERNATE_SUFFIXES = ["com", "co", "net", "io"]


def suggest_names(primary: str, count: int) -> list[dict[str, str]]:
    """Suggest `count` secondary domain names derived from the primary.

    Returns dicts with the suggested name and why that pattern is used. If the pattern list
    runs out, falls back to the same stems on alternate TLDs.
    """
    stem, suffix = split_domain(primary)
    stem = stem.replace(".", "")

    suggestions: list[dict[str, str]] = []
    for pattern, rationale in NAME_PATTERNS:
        if len(suggestions) >= count:
            break
        name = pattern.format(stem=stem, suffix=suffix)
        if name != primary:
            suggestions.append({"domain": name, "pattern": pattern, "rationale": rationale})

    # Fallback: reuse the strongest patterns against other TLDs.
    alt_index = 0
    while len(suggestions) < count:
        alt_suffix = ALTERNATE_SUFFIXES[alt_index % len(ALTERNATE_SUFFIXES)]
        pattern, rationale = NAME_PATTERNS[alt_index % len(NAME_PATTERNS)]
        name = pattern.format(stem=stem, suffix=alt_suffix)
        if name != primary and all(s["domain"] != name for s in suggestions):
            suggestions.append(
                {"domain": name, "pattern": pattern, "rationale": f"{rationale}, alternate TLD"}
            )
        alt_index += 1
        if alt_index > len(NAME_PATTERNS) * len(ALTERNATE_SUFFIXES) * 2:
            raise PlanError("could not generate enough distinct domain names")

    return suggestions[:count]


def build_plan(
    primary_domain: str,
    monthly_volume: int,
    daily_ceiling: int = DEFAULT_DAILY_CEILING,
    mailboxes_per_domain: int = DEFAULT_MAILBOXES_PER_DOMAIN,
    sending_days: int = DEFAULT_SENDING_DAYS,
    headroom: float = DEFAULT_HEADROOM,
) -> dict:
    """Compute the sending estate plan. Pure function; no I/O."""
    primary = validate_domain(primary_domain)

    if monthly_volume <= 0:
        raise PlanError("monthly volume must be greater than zero")
    if daily_ceiling <= 0:
        raise PlanError("daily ceiling must be greater than zero")
    if daily_ceiling > MAX_DAILY_CEILING:
        raise PlanError(
            f"daily ceiling of {daily_ceiling} per mailbox is beyond what this planner will "
            f"recommend (max {MAX_DAILY_CEILING}). Sustained cold volume above that per "
            f"mailbox is a filtering problem, not a capacity problem."
        )
    if mailboxes_per_domain <= 0:
        raise PlanError("mailboxes per domain must be greater than zero")
    if mailboxes_per_domain > 5:
        raise PlanError(
            f"{mailboxes_per_domain} mailboxes per domain concentrates too much volume on one "
            f"reputation. Cap is 5; 3 is the default for a reason."
        )
    if sending_days <= 0 or sending_days > 31:
        raise PlanError("sending days must be between 1 and 31")
    if not 0 <= headroom < 1:
        raise PlanError("headroom must be at least 0 and less than 1")

    # Step 1: convert a monthly target into a daily one.
    daily_target = monthly_volume / sending_days

    # Step 2: inflate by the headroom factor so the estate still hits target with one
    # domain pulled out of rotation.
    required_daily = daily_target / (1 - headroom)

    # Step 3: mailboxes needed to carry that daily figure at the per-mailbox ceiling.
    mailboxes_needed = math.ceil(required_daily / daily_ceiling)

    # Step 4: domains needed to host those mailboxes.
    domains_needed = math.ceil(mailboxes_needed / mailboxes_per_domain)

    # Step 5: round mailboxes up to fill every domain evenly. Uneven estates are harder to
    # rotate and harder to reason about when one domain misbehaves.
    total_mailboxes = domains_needed * mailboxes_per_domain

    if domains_needed > MAX_REASONABLE_DOMAINS:
        raise PlanError(
            f"this target needs {domains_needed} sending domains, past the {MAX_REASONABLE_DOMAINS} "
            f"this planner will recommend. At this volume the constraint is list quality and "
            f"reply handling capacity, not sending capacity. Reduce the target or split the "
            f"programme across separate brands with their own estates."
        )

    capacity_daily = total_mailboxes * daily_ceiling
    capacity_monthly = capacity_daily * sending_days
    utilisation = daily_target / capacity_daily

    # What the estate still delivers with one domain pulled.
    degraded_daily = (domains_needed - 1) * mailboxes_per_domain * daily_ceiling
    survives_one_loss = degraded_daily >= daily_target

    suggestions = suggest_names(primary, domains_needed)

    return {
        "inputs": {
            "primary_domain": primary,
            "monthly_volume": monthly_volume,
            "daily_ceiling_per_mailbox": daily_ceiling,
            "mailboxes_per_domain": mailboxes_per_domain,
            "sending_days_per_month": sending_days,
            "headroom": headroom,
        },
        "arithmetic": [
            f"Daily target        = {monthly_volume} sends / {sending_days} sending days "
            f"= {daily_target:.1f} sends per day",
            f"With {headroom:.0%} headroom   = {daily_target:.1f} / (1 - {headroom:.2f}) "
            f"= {required_daily:.1f} sends per day of built capacity",
            f"Mailboxes needed    = ceil({required_daily:.1f} / {daily_ceiling} per mailbox) "
            f"= {mailboxes_needed} mailboxes",
            f"Domains needed      = ceil({mailboxes_needed} / {mailboxes_per_domain} per domain) "
            f"= {domains_needed} domains",
            f"Mailboxes built     = {domains_needed} domains x {mailboxes_per_domain} "
            f"= {total_mailboxes} mailboxes (rounded up to fill every domain evenly)",
            f"Built capacity      = {total_mailboxes} x {daily_ceiling} = {capacity_daily} per day, "
            f"{capacity_monthly} per month",
            f"Utilisation         = {daily_target:.1f} / {capacity_daily} = {utilisation:.0%} of "
            f"built capacity at steady state",
        ],
        "plan": {
            "secondary_domains": domains_needed,
            "mailboxes_per_domain": mailboxes_per_domain,
            "total_mailboxes": total_mailboxes,
            "daily_ceiling_per_mailbox": daily_ceiling,
            "estate_daily_capacity": capacity_daily,
            "estate_monthly_capacity": capacity_monthly,
            "utilisation_at_target": round(utilisation, 4),
            "survives_losing_one_domain": survives_one_loss,
            "degraded_daily_capacity": degraded_daily,
        },
        "suggested_domains": suggestions,
        "notes": _notes(primary, domains_needed, survives_one_loss, utilisation),
    }


def _notes(
    primary: str, domains: int, survives_one_loss: bool, utilisation: float
) -> list[str]:
    notes = [
        f"Never send cold email from {primary}. The primary domain carries the client's "
        f"transactional mail, their sales replies and their reputation with existing "
        f"customers. A cold programme that damages it damages the business.",
        "Every secondary domain 301-redirects to the primary. A prospect who pastes the "
        "domain into a browser must land somewhere that plausibly belongs to the client.",
        "Register secondary domains with the same registrar and privacy settings as the "
        "primary, on the same renewal cycle. A lapsed sending domain is a live incident.",
        "The domain plan is a capacity ceiling, not a target. Volume is governed by list "
        "size and reply-handling capacity; do not fill the estate just because it exists.",
    ]
    if domains == 1:
        notes.append(
            "A single-domain estate has no failure isolation. If that domain's reputation "
            "degrades the programme stops entirely. Consider two domains even below the "
            "volume that requires it."
        )
    if not survives_one_loss and domains > 1:
        notes.append(
            "This estate does not hold target volume with one domain pulled from rotation. "
            "Add one domain, or accept that a reputation incident cuts throughput."
        )
    if utilisation > 0.9:
        notes.append(
            f"Utilisation at {utilisation:.0%} of built capacity leaves almost no room for a "
            f"volume increase without registering and warming more domains, which is a "
            f"four-week lead time. Plan the next tranche now."
        )
    return notes


def render_text(plan: dict) -> str:
    """Render the plan as a plain-text report."""
    i = plan["inputs"]
    p = plan["plan"]
    lines: list[str] = []

    def rule(char: str = "-") -> None:
        lines.append(char * 78)

    rule("=")
    lines.append(f"SENDING ESTATE PLAN - {i['primary_domain']}")
    rule("=")
    lines.append("")
    lines.append(f"Target volume:  {i['monthly_volume']:,} sends per month")
    lines.append(
        f"Assumptions:    {i['daily_ceiling_per_mailbox']} sends/mailbox/day, "
        f"{i['mailboxes_per_domain']} mailboxes/domain, "
        f"{i['sending_days_per_month']} sending days/month, "
        f"{i['headroom']:.0%} headroom"
    )
    lines.append("")

    rule()
    lines.append("ARITHMETIC")
    rule()
    for step in plan["arithmetic"]:
        lines.append(f"  {step}")
    lines.append("")

    rule()
    lines.append("RECOMMENDATION")
    rule()
    lines.append(f"  Secondary domains to register     {p['secondary_domains']}")
    lines.append(f"  Mailboxes per domain              {p['mailboxes_per_domain']}")
    lines.append(f"  Total mailboxes to provision      {p['total_mailboxes']}")
    lines.append(f"  Daily ceiling per mailbox         {p['daily_ceiling_per_mailbox']}")
    lines.append(
        f"  Estate capacity                   {p['estate_daily_capacity']:,}/day, "
        f"{p['estate_monthly_capacity']:,}/month"
    )
    lines.append(f"  Utilisation at target             {p['utilisation_at_target']:.0%}")
    lines.append(
        f"  Holds target losing one domain    "
        f"{'yes' if p['survives_losing_one_domain'] else 'NO'} "
        f"({p['degraded_daily_capacity']:,}/day degraded)"
    )
    lines.append("")

    rule()
    lines.append("SUGGESTED DOMAIN NAMES")
    rule()
    lines.append("  Check availability manually. Reject any that could be mistaken for a")
    lines.append("  competitor or that a trademark search flags.")
    lines.append("")
    lines.append(f"  {'#':<4}{'DOMAIN':<34}RATIONALE")
    for n, s in enumerate(plan["suggested_domains"], start=1):
        lines.append(f"  {n:<4}{s['domain']:<34}{s['rationale']}")
    lines.append("")

    rule()
    lines.append("MAILBOX ALLOCATION")
    rule()
    lines.append("  Use real human names, not role addresses. Role addresses (info@, sales@,")
    lines.append("  hello@) attract filtering and get no replies.")
    lines.append("")
    for s in plan["suggested_domains"]:
        boxes = ", ".join(
            f"{{{{SENDER_PERSONA_NAME_{k}}}}}@{s['domain']}"
            for k in range(1, p["mailboxes_per_domain"] + 1)
        )
        lines.append(f"  {s['domain']}")
        lines.append(f"      {boxes}")
    lines.append("")

    rule()
    lines.append("NOTES")
    rule()
    for note in plan["notes"]:
        wrapped = _wrap(note, 74)
        lines.append(f"  - {wrapped[0]}")
        for cont in wrapped[1:]:
            lines.append(f"    {cont}")
        lines.append("")

    rule()
    lines.append("NEXT STEPS")
    rule()
    lines.append("  1. Check availability of the suggested domains and pick the survivors.")
    lines.append("  2. Register them. Redirect each to the primary domain.")
    lines.append("  3. Run dns_records.py per domain and apply the output at the registrar.")
    lines.append("  4. Provision mailboxes, then start warmup-checklist.md week 1.")
    lines.append("")

    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    """Wrap text to `width`, returning a list of lines. Avoids importing textwrap for one call."""
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
        description="Plan a cold-email sending estate. No network calls; produces a plan a human executes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python domain_plan.py --primary-domain example.com --monthly-volume 20000\n"
        ),
    )
    parser.add_argument(
        "--primary-domain", required=True, help="The client's main brand domain, e.g. example.com"
    )
    parser.add_argument(
        "--monthly-volume", required=True, type=int, help="Target cold sends per month"
    )
    parser.add_argument(
        "--daily-ceiling",
        type=int,
        default=DEFAULT_DAILY_CEILING,
        help=f"Sends per mailbox per day at steady state (default: {DEFAULT_DAILY_CEILING})",
    )
    parser.add_argument(
        "--mailboxes-per-domain",
        type=int,
        default=DEFAULT_MAILBOXES_PER_DOMAIN,
        help=f"Mailboxes on each sending domain (default: {DEFAULT_MAILBOXES_PER_DOMAIN})",
    )
    parser.add_argument(
        "--sending-days",
        type=int,
        default=DEFAULT_SENDING_DAYS,
        help=f"Sending days per month (default: {DEFAULT_SENDING_DAYS})",
    )
    parser.add_argument(
        "--headroom",
        type=float,
        default=DEFAULT_HEADROOM,
        help=f"Spare capacity as a fraction, 0 to 1 (default: {DEFAULT_HEADROOM})",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    args = parser.parse_args(argv)

    try:
        plan = build_plan(
            primary_domain=args.primary_domain,
            monthly_volume=args.monthly_volume,
            daily_ceiling=args.daily_ceiling,
            mailboxes_per_domain=args.mailboxes_per_domain,
            sending_days=args.sending_days,
            headroom=args.headroom,
        )
    except PlanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        print(render_text(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

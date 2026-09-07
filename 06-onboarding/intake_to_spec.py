#!/usr/bin/env python3
"""Turn a completed client intake into a build specification.

Reads an intake as JSON (see sample-intake.json, which mirrors intake-form.md) and emits:

  - the domain plan, by calling 02-infrastructure/domain_plan.py
  - the cadence node map and CRM build order, by calling 04-cadence/cadence_builder.py
  - the CRM build checklist, resolved for this client's configuration
  - a list of missing or ambiguous inputs that block the build

Blockers are the point of this script. An intake that looks complete but has no lawful basis
recorded for Canadian contacts, or a reply capacity a quarter of what the volume target implies,
will produce a build that fails in week three. Finding that on day zero is cheap.

Usage:
    python intake_to_spec.py --input sample-intake.json
    python intake_to_spec.py --input intake.json --output spec.md
    python intake_to_spec.py --input intake.json --blockers-only
    python intake_to_spec.py --input intake.json --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Roughly what share of sends produce a reply on a healthy cold programme. Used only to
# sanity-check the volume target against the client's stated reply capacity.
ASSUMED_REPLY_RATE = 0.03
SENDING_DAYS_PER_MONTH = 22
WEEKS_PER_MONTH = 4.3


class IntakeError(ValueError):
    """Raised when the intake cannot be read at all."""


def load_sibling(relative_path: str, module_name: str):
    """Import a module from elsewhere in this repo by path.

    The directories are numbered (02-infrastructure), which is not a valid module name, so a
    plain import will not work. Loading by path keeps one implementation of the domain and
    cadence logic rather than a second copy that drifts.
    """
    path = REPO_ROOT / relative_path
    if not path.exists():
        raise IntakeError(f"expected to find {relative_path} at {path}, but it is not there")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise IntakeError(f"could not load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------------------
# Tolerant accessors. Intake files are filled in by hand, often partially.
# --------------------------------------------------------------------------------------


def get(data: Any, *path: str, default=None):
    """Walk a dotted path through nested dicts, returning `default` on any miss."""
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return default if cur in (None, "") else cur


def as_list(value) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "")]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def as_bool(value) -> bool | None:
    """Interpret a yes/no answer. Returns None when unanswered, which is different from False."""
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return None
    s = str(value).strip().lower()
    if s in ("yes", "y", "true", "1"):
        return True
    if s in ("no", "n", "false", "0", "none"):
        return False
    return None


def as_int(value) -> int | None:
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------
# Blockers and warnings
# --------------------------------------------------------------------------------------

# (section, field path, human label). A blocker is raised for each that is absent.
REQUIRED_FIELDS: list[tuple[str, tuple[str, ...], str]] = [
    ("1 Company", ("company", "trading_name"), "trading name"),
    ("1 Company", ("company", "legal_entity"), "legal entity name"),
    ("1 Company", ("company", "postal_address"), "physical postal address"),
    ("1 Company", ("company", "primary_domain"), "primary domain"),
    ("1 Company", ("company", "privacy_policy_url"), "privacy policy URL"),
    ("1 Company", ("company", "decision_maker_name"), "decision-maker name"),
    ("1 Company", ("company", "decision_maker_email"), "decision-maker email"),
    ("1 Company", ("company", "reply_owner"), "who owns replies"),
    ("2 Offer", ("offer", "one_sentence"), "what the client sells, in one sentence"),
    ("2 Offer", ("offer", "problem"), "the problem the offer removes"),
    ("2 Offer", ("offer", "what_changes"), "what changes for the buyer"),
    ("3 ICP", ("icp", "description"), "ICP description"),
    ("3 ICP", ("icp", "job_titles"), "job titles"),
    ("3 ICP", ("icp", "company_size_band"), "company size band"),
    ("3 ICP", ("icp", "geography"), "geography"),
    ("3 ICP", ("icp", "not_for"), "who this is explicitly not for"),
    ("3 ICP", ("icp", "never_contact"), "accounts never to contact"),
    ("4 Segmentation", ("segmentation", "segment_field"), "the field that routes contacts"),
    ("4 Segmentation", ("segmentation", "lanes"), "lane names"),
    ("4 Segmentation", ("segmentation", "default_lane"), "the lane catching unmapped values"),
    ("4 Segmentation", ("segmentation", "lane_differences"), "what differs per lane"),
    ("5 Proof", ("proof", "points"), "at least one substantiable proof point"),
    ("6 Objections", ("objections", "items"), "objections and rebuttals"),
    ("6 Objections", ("objections", "most_common"), "the most common objection"),
    ("7 Voice", ("voice", "tone"), "tone constraints"),
    ("7 Voice", ("voice", "forbidden_words"), "forbidden words (write 'none' if none)"),
    ("7 Voice", ("voice", "competitor_exclusions"), "competitors never to mention"),
    ("7 Voice", ("voice", "required_disclaimer"), "required disclaimer (write 'none' if none)"),
    ("8 The ask", ("ask", "primary_cta"), "the primary call to action"),
    ("8 The ask", ("ask", "required_input"), "what a prospect supplies to signal engagement"),
    ("8 The ask", ("ask", "what_you_do_with_it"), "what happens with that input, and how fast"),
    ("9 Sender", ("sender", "name"), "sender name"),
    ("9 Sender", ("sender", "title"), "sender title"),
    ("10 Infrastructure", ("infrastructure", "target_monthly_sends"), "target sends per month"),
    ("10 Infrastructure", ("infrastructure", "esp"), "email service provider"),
    ("10 Infrastructure", ("infrastructure", "dns_host"), "DNS host"),
    ("10 Infrastructure", ("infrastructure", "registrar"), "domain registrar"),
    ("10 Infrastructure", ("infrastructure", "crm"), "CRM or automation platform"),
    ("10 Infrastructure", ("infrastructure", "channels"), "channels in scope"),
    ("11 Reply capacity", ("reply_capacity", "replies_per_week"), "replies answerable per week"),
    ("11 Reply capacity", ("reply_capacity", "who_answers"), "who answers replies"),
    ("11 Reply capacity", ("reply_capacity", "escalation_path"), "escalation path"),
    ("11 Reply capacity", ("reply_capacity", "absence_cover"), "cover during absence"),
    ("12 Compliance", ("compliance", "jurisdictions"), "every jurisdiction the list touches"),
    ("12 Compliance", ("compliance", "unsubscribe_url"), "unsubscribe endpoint URL"),
    ("12 Compliance", ("compliance", "data_retention_days"), "data retention period in days"),
    ("13 List", ("list", "suppression_list_supplied"), "existing suppression list"),
    ("13 List", ("list", "existing_customers_supplied"), "existing customers, to suppress"),
    ("14 Commercial", ("commercial", "engagement"), "which engagement"),
    ("14 Commercial", ("commercial", "signer"), "who signs"),
]


def find_blockers(d: dict) -> list[dict]:
    """Everything that must be resolved before day 1."""
    blockers: list[dict] = []

    def block(section: str, issue: str, why: str) -> None:
        blockers.append({"section": section, "issue": issue, "why": why})

    # --- Missing required fields ---------------------------------------------------
    for section, path, label in REQUIRED_FIELDS:
        if get(d, *path) is None:
            block(section, f"Missing: {label}", "Required field. The build cannot start without it.")

    # --- Compliance: the gates that cannot be satisfied retroactively ---------------
    comp = d.get("compliance", {}) if isinstance(d.get("compliance"), dict) else {}
    jurisdictions = [j.upper() for j in as_list(comp.get("jurisdictions"))]

    counsel = as_bool(comp.get("counsel_signed_off"))
    if counsel is not True:
        block(
            "12 Compliance",
            "Counsel has not signed off on cold outbound to these jurisdictions",
            "Only the client and their counsel can determine lawful basis. The build gate in "
            "the runbook (step 0.4) will not pass without this.",
        )

    uk_eu = as_bool(comp.get("uk_eu_contacts"))
    if uk_eu is True:
        if not comp.get("lia_reference"):
            block(
                "12 Compliance",
                "UK/EU contacts are in scope but no Legitimate Interest Assessment is on file",
                "GDPR requires a documented balancing test before relying on legitimate "
                "interest. Without it, UK and EU contacts must be excluded from the list.",
            )
        if as_bool(comp.get("personal_or_sole_trader_addresses")) is True:
            block(
                "12 Compliance",
                "The UK/EU list includes personal addresses, sole traders or partnerships",
                "PECR treats sole traders and partnerships as individuals, which requires "
                "consent rather than legitimate interest. These contacts must be removed or a "
                "consent basis recorded per contact.",
            )
        if as_bool(comp.get("personal_or_sole_trader_addresses")) is None:
            block(
                "12 Compliance",
                "Unanswered: are any UK/EU contacts personal addresses, sole traders or partnerships?",
                "The answer determines whether legitimate interest is available for those "
                "contacts. Unanswered is not the same as no.",
            )

    canada = as_bool(comp.get("canadian_contacts"))
    if canada is True and not comp.get("canadian_consent_basis"):
        block(
            "12 Compliance",
            "Canadian contacts are in scope but no consent basis is recorded",
            "CASL requires a lawful basis before the first message and cannot be satisfied "
            "retroactively by good opt-out handling. Either the basis is recorded per contact, "
            "with its expiry, or Canadian contacts are excluded.",
        )

    channels = as_list(get(d, "infrastructure", "channels"))
    if any(c.strip().lower() == "sms" for c in channels):
        if not comp.get("sms_consent_basis"):
            block(
                "12 Compliance",
                "SMS is in scope but no consent basis is recorded for the numbers",
                "A number obtained from a data vendor is not consent. Cold SMS carries "
                "statutory per-message damages under the TCPA in the US and is a PECR breach "
                "in the UK. Either the basis exists per number, or SMS is out of scope.",
            )

    # --- Proof -----------------------------------------------------------------------
    proof_points = get(d, "proof", "points", default=[])
    if isinstance(proof_points, list) and proof_points:
        for n, p in enumerate(proof_points, start=1):
            if isinstance(p, dict) and not p.get("evidence"):
                block(
                    "5 Proof",
                    f"Proof point {n} has no evidence recorded",
                    "A claim that cannot be evidenced on request is a legal exposure and "
                    "cannot go in the copy.",
                )
    if as_bool(get(d, "proof", "evidence_confirmed")) is not True:
        block(
            "5 Proof",
            "The client has not confirmed every claim can be evidenced on request",
            "Unsubstantiated claims are actionable under the FTC Act in the US and the "
            "Consumer Protection from Unfair Trading Regulations in the UK.",
        )

    # --- Sender ----------------------------------------------------------------------
    if as_bool(get(d, "sender", "is_real_person_who_agreed")) is not True:
        block(
            "9 Sender",
            "The sender is not confirmed as a real person who has agreed",
            "Misleading sender identification is a specific CAN-SPAM violation. A prospect who "
            "searches the sender and finds a fabricated persona complains.",
        )

    # --- Segmentation ----------------------------------------------------------------
    lanes = as_list(get(d, "segmentation", "lanes"))
    default_lane = get(d, "segmentation", "default_lane")
    if lanes and default_lane and str(default_lane).strip().lower() not in [
        l.strip().lower() for l in lanes
    ]:
        block(
            "4 Segmentation",
            f"Default lane {default_lane!r} is not one of the lanes: {', '.join(lanes)}",
            "Contacts with a null or unmapped segment value have nowhere to go, and most "
            "platforms drop them silently.",
        )

    # --- Objections ------------------------------------------------------------------
    objections = get(d, "objections", "items", default=[])
    if isinstance(objections, list) and 0 < len(objections) < 3:
        block(
            "6 Objections",
            f"Only {len(objections)} objection(s) supplied; three are required",
            "One cadence node addresses the most common objection directly. Fewer than three "
            "means the copy has nothing to work from.",
        )

    # --- Suppression files -----------------------------------------------------------
    for key, label in (
        ("suppression_list_supplied", "existing suppression / unsubscribe list"),
        ("existing_customers_supplied", "existing customer list"),
    ):
        if as_bool(get(d, "list", key)) is False:
            block(
                "13 List",
                f"The {label} has not been supplied",
                "Loaded into suppression before day 1. An existing customer or a previous "
                "unsubscribe receiving a cold pitch is the most damaging message the pipeline "
                "can send, and it is entirely preventable.",
            )

    return blockers


def find_warnings(d: dict) -> list[dict]:
    """Things that will not stop the build but will change it."""
    warnings: list[dict] = []

    def warn(section: str, issue: str, why: str) -> None:
        warnings.append({"section": section, "issue": issue, "why": why})

    # --- Reply capacity against the volume target ------------------------------------
    volume = as_int(get(d, "infrastructure", "target_monthly_sends"))
    capacity = as_int(get(d, "reply_capacity", "replies_per_week"))
    if volume and capacity is not None:
        implied_weekly = volume * ASSUMED_REPLY_RATE / WEEKS_PER_MONTH
        if implied_weekly > capacity:
            sustainable = int(capacity * WEEKS_PER_MONTH / ASSUMED_REPLY_RATE)
            warn(
                "11 Reply capacity",
                f"Volume target of {volume:,}/month implies about {implied_weekly:.0f} replies "
                f"a week, against a stated capacity of {capacity}",
                f"Unanswered replies burn the list permanently and generate complaints. Either "
                f"raise reply capacity, or reduce the target to about {sustainable:,}/month, "
                f"which is what {capacity} replies a week supports. This is step 1.2 of the "
                f"infrastructure runbook.",
            )
        elif implied_weekly > capacity * 0.8:
            warn(
                "11 Reply capacity",
                f"Volume target implies about {implied_weekly:.0f} replies a week against a "
                f"capacity of {capacity} — close to the limit",
                "Leaves no room for a good week. Consider starting below the target.",
            )

    # --- Existing sending history ----------------------------------------------------
    if as_bool(get(d, "infrastructure", "prior_cold_sending")) is True:
        warn(
            "10 Infrastructure",
            "Cold email has been sent from existing domains before",
            "Those domains carry that history whether or not anyone remembers it. Run a "
            "03-audit/ audit before building anything on top of them.",
        )
    if get(d, "infrastructure", "blocklist_history"):
        warn(
            "10 Infrastructure",
            f"Known deliverability history: {get(d, 'infrastructure', 'blocklist_history')}",
            "Assess before the build. A previously burned domain does not recover on any "
            "timeline worth waiting for, and the correct answer is usually a new estate.",
        )

    # --- List quality ----------------------------------------------------------------
    if as_bool(get(d, "list", "has_list")) is True:
        if as_bool(get(d, "list", "verified")) is not True:
            warn(
                "13 List",
                "The supplied list has not been verified",
                "Verification is a required gate before import. An unverified list is the "
                "single most common cause of a burned estate.",
            )
        if as_bool(get(d, "list", "previously_emailed")) is True:
            warn(
                "13 List",
                "Part of the list has been emailed before",
                "Check for fatigue and for unsubscribes that were never recorded. Anyone who "
                "opted out previously must be in the suppression list.",
            )

    # --- Segmentation load -----------------------------------------------------------
    lanes = as_list(get(d, "segmentation", "lanes"))
    if len(lanes) >= 4:
        warn(
            "4 Segmentation",
            f"{len(lanes)} lanes",
            "Each lane multiplies the copy at every node and at every iteration cycle. "
            "Confirm the client has capacity, and check this against pricing driver D4.",
        )

    # --- Trigger event ---------------------------------------------------------------
    if not get(d, "icp", "trigger_event"):
        warn(
            "3 ICP",
            "No trigger event supplied",
            "Optional, but it is the highest-value field in the intake: it is the difference "
            "between a message that could have been sent to anyone and one that could only "
            "have been sent to them.",
        )

    # --- Writing samples -------------------------------------------------------------
    if not get(d, "voice", "writing_samples"):
        warn(
            "7 Voice",
            "No samples of the client's own writing supplied",
            "Worth more than the tone settings combined, because it shows the voice rather "
            "than describing it.",
        )

    # --- Procurement -----------------------------------------------------------------
    if as_bool(get(d, "commercial", "procurement_review_required")) is True:
        warn(
            "14 Commercial",
            "A procurement, security or legal review is required",
            "Frequently the longest single delay in an engagement. Start it now, in parallel "
            "with everything else.",
        )

    return warnings


# --------------------------------------------------------------------------------------
# Spec assembly
# --------------------------------------------------------------------------------------


def build_spec(d: dict) -> dict:
    """Assemble the full build specification."""
    blockers = find_blockers(d)
    warnings = find_warnings(d)

    spec: dict = {
        "client": get(d, "company", "trading_name", default="[not provided]"),
        "blockers": blockers,
        "warnings": warnings,
        "domain_plan": None,
        "domain_plan_error": None,
        "cadence": None,
        "cadence_error": None,
        "resolved_variables": _resolved_variables(d),
    }

    # --- Domain plan -----------------------------------------------------------------
    primary = get(d, "company", "primary_domain")
    volume = as_int(get(d, "infrastructure", "target_monthly_sends"))
    if primary and volume:
        try:
            domain_plan = load_sibling("02-infrastructure/domain_plan.py", "_op_domain_plan")
            spec["domain_plan"] = domain_plan.build_plan(
                primary_domain=str(primary), monthly_volume=volume
            )
        except Exception as exc:  # the planner raises PlanError; anything else is a real fault
            spec["domain_plan_error"] = str(exc)
    else:
        spec["domain_plan_error"] = (
            "Not generated: primary domain and target monthly sends are both required."
        )

    # --- Cadence ---------------------------------------------------------------------
    lanes = as_list(get(d, "segmentation", "lanes"))
    channels = as_list(get(d, "infrastructure", "channels")) or ["email"]
    if lanes:
        try:
            cadence_builder = load_sibling("04-cadence/cadence_builder.py", "_op_cadence_builder")
            default_lane = get(d, "segmentation", "default_lane")
            spec["cadence"] = cadence_builder.build_cadence(
                segments=lanes,
                channels=channels,
                length=as_int(get(d, "segmentation", "cadence_length_days")) or 8,
                segment_field=str(get(d, "segmentation", "segment_field", default="{{SEGMENT_FIELD}}")),
                default_lane=str(default_lane) if default_lane else None,
                sms_consent_confirmed=bool(get(d, "compliance", "sms_consent_basis")),
            )
        except Exception as exc:
            spec["cadence_error"] = str(exc)
    else:
        spec["cadence_error"] = "Not generated: no lanes supplied."

    return spec


def _resolved_variables(d: dict) -> dict[str, str]:
    """Map the intake onto the placeholders in VARIABLES.md, so filling templates is mechanical."""
    mapping = {
        "CLIENT_NAME": get(d, "company", "trading_name"),
        "CLIENT_LEGAL_ENTITY": get(d, "company", "legal_entity"),
        "CLIENT_POSTAL_ADDRESS": get(d, "company", "postal_address"),
        "CLIENT_CONTACT_NAME": get(d, "company", "decision_maker_name"),
        "CLIENT_CONTACT_EMAIL": get(d, "company", "decision_maker_email"),
        "PRIMARY_DOMAIN": get(d, "company", "primary_domain"),
        "PRIVACY_POLICY_URL": get(d, "company", "privacy_policy_url"),
        "DPO_CONTACT": get(d, "company", "dpo_contact"),
        "OFFER_DESCRIPTION": get(d, "offer", "one_sentence"),
        "PROBLEM_STATEMENT": get(d, "offer", "problem"),
        "ICP_DESCRIPTION": get(d, "icp", "description"),
        "SEGMENT_FIELD": get(d, "segmentation", "segment_field"),
        "SEGMENT_LANES": ", ".join(as_list(get(d, "segmentation", "lanes"))) or None,
        "CADENCE_LENGTH_DAYS": get(d, "segmentation", "cadence_length_days"),
        "CHANNELS_AVAILABLE": ", ".join(as_list(get(d, "infrastructure", "channels"))) or None,
        "PRIMARY_CTA": get(d, "ask", "primary_cta"),
        "REQUIRED_INPUT": get(d, "ask", "required_input"),
        "SENDER_PERSONA_NAME": get(d, "sender", "name"),
        "SENDER_PERSONA_TITLE": get(d, "sender", "title"),
        "TARGET_MONTHLY_SENDS": get(d, "infrastructure", "target_monthly_sends"),
        "ESP_NAME": get(d, "infrastructure", "esp"),
        "CRM_NAME": get(d, "infrastructure", "crm"),
        "SENDING_PLATFORM": get(d, "infrastructure", "sending_platform"),
        "JURISDICTIONS": ", ".join(as_list(get(d, "compliance", "jurisdictions"))) or None,
        "UNSUBSCRIBE_URL": get(d, "compliance", "unsubscribe_url"),
        "DATA_RETENTION_DAYS": get(d, "compliance", "data_retention_days"),
        "LIA_REFERENCE": get(d, "compliance", "lia_reference"),
        "TONE_CONSTRAINTS": get(d, "voice", "tone"),
        "FORBIDDEN_WORDS": get(d, "voice", "forbidden_words"),
        "COMPETITOR_EXCLUSION_LIST": get(d, "voice", "competitor_exclusions"),
        "REQUIRED_DISCLAIMER": get(d, "voice", "required_disclaimer"),
        "REPORTING_CADENCE": get(d, "commercial", "reporting_cadence"),
    }
    return {k: str(v) for k, v in mapping.items() if v is not None}


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------


def render(spec: dict, blockers_only: bool = False) -> str:
    out: list[str] = []
    a = out.append

    a(f"# Build Specification — {spec['client']}")
    a("")

    # --- Blockers --------------------------------------------------------------------
    a("## Blockers")
    a("")
    if not spec["blockers"]:
        a("None. Every required input is present and no compliance gate is unsatisfied.")
        a("")
    else:
        a(
            f"**{len(spec['blockers'])} blocker(s).** The build does not start until these are "
            f"resolved. Each needs an answer only the client can give."
        )
        a("")
        a("| # | Section | Issue | Why it blocks |")
        a("|---|---|---|---|")
        for n, b in enumerate(spec["blockers"], start=1):
            a(f"| {n} | {b['section']} | {b['issue']} | {b['why']} |")
        a("")

    # --- Warnings --------------------------------------------------------------------
    a("## Warnings")
    a("")
    if not spec["warnings"]:
        a("None.")
        a("")
    else:
        a(f"**{len(spec['warnings'])}.** These do not stop the build, but they change it.")
        a("")
        a("| # | Section | Issue | What it means |")
        a("|---|---|---|---|")
        for n, w in enumerate(spec["warnings"], start=1):
            a(f"| {n} | {w['section']} | {w['issue']} | {w['why']} |")
        a("")

    if blockers_only:
        return "\n".join(out)

    # --- Domain plan -----------------------------------------------------------------
    a("---")
    a("")
    a("## Domain plan")
    a("")
    if spec["domain_plan_error"]:
        a(f"_{spec['domain_plan_error']}_")
        a("")
    else:
        p = spec["domain_plan"]["plan"]
        a("| | |")
        a("|---|---|")
        a(f"| Secondary domains to register | {p['secondary_domains']} |")
        a(f"| Mailboxes per domain | {p['mailboxes_per_domain']} |")
        a(f"| Total mailboxes | {p['total_mailboxes']} |")
        a(f"| Daily ceiling per mailbox | {p['daily_ceiling_per_mailbox']} |")
        a(f"| Estate capacity | {p['estate_daily_capacity']:,}/day, "
          f"{p['estate_monthly_capacity']:,}/month |")
        a(f"| Utilisation at target | {p['utilisation_at_target']:.0%} |")
        a(f"| Holds target losing one domain | "
          f"{'yes' if p['survives_losing_one_domain'] else 'NO'} |")
        a("")
        a("**Arithmetic**")
        a("")
        a("```")
        for step in spec["domain_plan"]["arithmetic"]:
            a(step)
        a("```")
        a("")
        a("**Suggested domain names** — check availability and registration history manually.")
        a("")
        a("| # | Domain | Rationale |")
        a("|---|---|---|")
        for n, s in enumerate(spec["domain_plan"]["suggested_domains"], start=1):
            a(f"| {n} | {s['domain']} | {s['rationale']} |")
        a("")
        for note in spec["domain_plan"]["notes"]:
            a(f"> {note}")
            a(">")
        if spec["domain_plan"]["notes"]:
            out.pop()
        a("")

    # --- Cadence ---------------------------------------------------------------------
    a("---")
    a("")
    a("## Cadence node map")
    a("")
    if spec["cadence_error"]:
        a(f"_{spec['cadence_error']}_")
        a("")
    else:
        c = spec["cadence"]
        cfg = c["config"]
        t = c["totals"]
        a("| | |")
        a("|---|---|")
        a(f"| Lanes | {', '.join(cfg['segments'])} |")
        a(f"| Segment field | {cfg['segment_field']} |")
        a(f"| Default lane | {cfg['default_lane']} |")
        a(f"| Channels | {', '.join(cfg['channels'])} |")
        a(f"| Length | {cfg['length_days']} business days |")
        a(f"| Nodes per lane | {t['nodes_per_lane']} |")
        a(f"| Node instances | {t['main_sequence_node_instances']} |")
        a(f"| Copy pieces required | {t['copy_pieces_required']} |")
        a("")

        a("### Main sequence")
        a("")
        a("| Node | Day | Channel | Purpose |")
        a("|---|---|---|---|")
        for n in c["nodes"]:
            a(f"| {n['node']} | {n['day']} | {n['channel']} | {n['purpose']} |")
        a("")

        a("### Follow-through branch")
        a("")
        a("Days counted from the interrupt, not from cadence entry.")
        a("")
        a("| Node | Day | Channel | Purpose |")
        a("|---|---|---|---|")
        for f in c["followthrough"]:
            a(f"| {f['node']} | {f['day']} | {f['channel']} | {f['purpose']} |")
        a("")

        a("### Lanes")
        a("")
        a("| Lane | Slug | Node IDs | Default |")
        a("|---|---|---|---|")
        for lane in c["lanes"]:
            a(f"| {lane['lane']} | {lane['slug']} | "
              f"{lane['node_ids'][0]}–{lane['node_ids'][-1]} | "
              f"{'yes' if lane['is_default'] else ''} |")
        a("")

        if c["warnings"]:
            a("### Cadence warnings")
            a("")
            for w in c["warnings"]:
                a(f"- {w}")
            a("")

        a("### CRM build order")
        a("")
        a("Full checklist: `04-cadence/crm-build-checklist.md`. Build in this order; the "
          "ordering is by dependency, not by importance.")
        a("")
        for s in c["build_order"]:
            a(f"{s['step']}. **{s['title']}** — {s['detail']}")
        a("")

    # --- Resolved variables ----------------------------------------------------------
    a("---")
    a("")
    a("## Resolved variables")
    a("")
    a("Values from this intake, mapped onto the placeholders in `VARIABLES.md`. Anything not "
      "listed here is still unresolved and must be filled by hand.")
    a("")
    a("| Variable | Value |")
    a("|---|---|")
    for k, v in sorted(spec["resolved_variables"].items()):
        a(f"| `{{{{{k}}}}}` | {v} |")
    a("")

    # --- Next steps ------------------------------------------------------------------
    a("---")
    a("")
    a("## Next steps")
    a("")
    if spec["blockers"]:
        a(f"1. Resolve the {len(spec['blockers'])} blocker(s) above. Nothing else starts first.")
        a("2. Re-run this script and confirm the blocker list is empty.")
        a("3. Then follow `02-infrastructure/infrastructure-runbook.md` from phase 0.")
    else:
        a("1. Follow `02-infrastructure/infrastructure-runbook.md` from phase 0.")
        a("2. Register the domains from the plan above; check availability and history first.")
        a("3. Run `02-infrastructure/dns_records.py` per domain.")
        a("4. Build the cadence per the build order above and "
          "`04-cadence/crm-build-checklist.md`.")
        a("5. Fill `05-copy/brain-file-template.md` and generate copy with "
          "`05-copy/variant_prompt.md`.")
        a("6. Deploy `07-data/schema.sql` and load the list with `07-data/list_pipeline.py`.")
    a("")

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Turn a completed client intake into a build specification.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python intake_to_spec.py --input sample-intake.json\n",
    )
    parser.add_argument("--input", required=True, help="Path to the intake JSON file")
    parser.add_argument("--output", default=None, help="Write markdown here instead of stdout")
    parser.add_argument(
        "--blockers-only",
        action="store_true",
        help="Print only the blocker and warning lists. Exit code 1 if any blocker exists.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    args = parser.parse_args(argv)

    try:
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        print(f"error: could not read {args.input!r}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {args.input!r} is not valid JSON: line {exc.lineno}, {exc.msg}",
              file=sys.stderr)
        return 2

    if not isinstance(data, dict):
        print(f"error: {args.input!r} must contain a JSON object at the top level", file=sys.stderr)
        return 2

    try:
        spec = build_spec(data)
    except IntakeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(spec, indent=2))
    else:
        text = render(spec, blockers_only=args.blockers_only)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text + "\n")
            except OSError as exc:
                print(f"error: could not write {args.output!r}: {exc}", file=sys.stderr)
                return 2
            print(f"Wrote {args.output}", file=sys.stderr)
        else:
            sys.stdout.reconfigure(encoding="utf-8")
            print(text)

    if args.blockers_only and spec["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

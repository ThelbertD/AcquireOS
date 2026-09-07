#!/usr/bin/env python3
"""Build a concrete cadence node map from a client configuration.

Takes the segments a client is splitting on, the channels they are cleared to use, and the
cadence length, and emits the node map plus the order to build it in a CRM.

The architecture this implements is described in cadence-spec.md. This script does not invent
structure — it instantiates that structure for one client's parameters.

Usage:
    python cadence_builder.py --segments enterprise,mid-market,smb --channels email,sms
    python cadence_builder.py --segments a,b --channels email --length 12
    python cadence_builder.py --config client-cadence.json --json
    python cadence_builder.py --segments a,b --channels email,sms --sms-consent-confirmed
"""

from __future__ import annotations

import argparse
import json
import sys

# --------------------------------------------------------------------------------------
# The node skeleton, expressed as a fraction of the cadence length so it scales.
#
# `position` is the day offset divided by the reference length of 8. A 12-day cadence
# stretches the same shape; a 5-day cadence compresses it. The shape itself — front-loaded,
# then widening — does not change, because that is the part that is architecture rather
# than configuration.
# --------------------------------------------------------------------------------------

REFERENCE_LENGTH = 8

NODE_SKELETON: list[dict] = [
    {
        "key": "open",
        "position": 0 / 8,
        "channel": "email",
        "purpose": "Open. State why this contact specifically, and make the primary ask.",
        "entry": "Entry gate passed; lane assigned",
        "exit": "Sent, and no interrupt signal within the wait",
    },
    {
        "key": "nudge-1",
        "position": 1 / 8,
        "channel": "sms",
        "purpose": "Short nudge. Adds a channel without adding an argument.",
        "entry": "Previous node sent and not bounced; sms_consent = true",
        "exit": "Sent, or skipped where consent is absent",
    },
    {
        "key": "angle-2",
        "position": 2 / 8,
        "channel": "email",
        "purpose": "Second angle on the same problem. Not a follow-up on the first message.",
        "entry": "Open node sent; no interrupt signal",
        "exit": "Sent",
    },
    {
        "key": "proof",
        "position": 4 / 8,
        "channel": "email",
        "purpose": "Proof. A concrete, substantiable result. Lowest-friction ask of the sequence.",
        "entry": "Previous email node sent; no interrupt signal",
        "exit": "Sent",
    },
    {
        "key": "nudge-2",
        "position": 5 / 8,
        "channel": "sms",
        "purpose": "Second nudge, referencing the ask rather than repeating it.",
        "entry": "Proof node sent; sms_consent = true",
        "exit": "Sent, or skipped where consent is absent",
    },
    {
        "key": "objection",
        "position": 6 / 8,
        "channel": "email",
        "purpose": "Address the single most common objection directly.",
        "entry": "Proof node sent; no interrupt signal",
        "exit": "Sent",
    },
    {
        "key": "close",
        "position": 8 / 8,
        "channel": "email",
        "purpose": "Close the loop. Ask permission to stop, and make the last touch easy to reply to.",
        "entry": "Objection node sent; no interrupt signal",
        "exit": "Sent -> terminal 'completed-no-response'",
    },
]

FOLLOWTHROUGH_SKELETON: list[dict] = [
    {
        "key": "acknowledge",
        "day": 0,
        "channel": "email",
        "purpose": "Acknowledge within one business hour. Confirm what was received, state what happens next and when.",
        "entry": "Interrupt fired",
        "exit": "Sent",
    },
    {
        "key": "deliver",
        "day": 1,
        "channel": "email",
        "purpose": "Deliver what was promised in the acknowledgement, or the next concrete step.",
        "entry": "Acknowledgement sent",
        "exit": "Sent",
    },
    {
        "key": "follow-up",
        "day": 3,
        "channel": "email",
        "purpose": "One follow-up on the delivery. Not a new sequence.",
        "entry": "Delivery sent; no response",
        "exit": "Sent",
    },
    {
        "key": "final",
        "day": 6,
        "channel": "email-or-sms",
        "purpose": "Final follow-through. Explicitly offers to close the thread.",
        "entry": "Follow-up sent; no response",
        "exit": "Sent -> re-entry evaluation",
    },
]

ENTRY_GATES: list[dict] = [
    {
        "id": "G1",
        "name": "Suppression",
        "passes": "Address, and its domain where the domain is suppressed, absent from the suppression list",
        "on_failure": "Reject. Terminal. Never re-enters.",
    },
    {
        "id": "G2",
        "name": "Consent basis",
        "passes": "A lawful basis is recorded for this contact's jurisdiction",
        "on_failure": "Reject. Hold for review.",
    },
    {
        "id": "G3",
        "name": "Fit score",
        "passes": "Score at or above {{ICP_SCORE_THRESHOLD}}",
        "on_failure": "Reject to the excluded pool. Re-evaluate at next enrichment.",
    },
    {
        "id": "G4",
        "name": "Active enrolment",
        "passes": "Not already in an active cadence, and outside the cooldown window",
        "on_failure": "Reject. Queue for after the cooldown.",
    },
]

TERMINAL_STATES: list[dict] = [
    {
        "state": "replied",
        "entered": "Any human reply, at any node",
        "suppression": "Removed from automated sending; not suppressed from human contact",
        "next": "Owned by a named person. Disposition recorded within 2 business days.",
    },
    {
        "state": "bounced",
        "entered": "Hard bounce, or 3 soft bounces in 7 days",
        "suppression": "Address suppressed permanently",
        "next": "Flag the source batch. Three or more from one batch means quarantine the rest.",
    },
    {
        "state": "unsubscribed",
        "entered": "Opt-out via any mechanism, any channel",
        "suppression": "Permanent, across every sending domain and every channel",
        "next": "Propagate immediately. Record timestamp, source and channel.",
    },
    {
        "state": "completed-no-response",
        "entered": "Final main-sequence or follow-through node sent, no response",
        "suppression": "Not suppressed. Cooled down.",
        "next": "Return to pool after 90 days. Re-enrich before re-enrolling.",
    },
]

KNOWN_CHANNELS = {"email", "sms"}
MAX_LANES = 6
MIN_LENGTH = 3
MAX_LENGTH = 30


class CadenceError(ValueError):
    """Raised when the configuration cannot produce a valid cadence."""


def slug(value: str) -> str:
    """Reduce a lane name to an identifier safe for a CRM object name."""
    out = []
    for ch in value.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    s = "".join(out).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s or "unnamed"


def lane_prefix(index: int) -> str:
    """A, B, C ... for lane node IDs. Wraps to AA, AB after 26 lanes, which will never happen."""
    letters = ""
    n = index
    while True:
        letters = chr(ord("A") + n % 26) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


def scale_days(length: int) -> list[int]:
    """Map the skeleton's fractional positions onto a cadence of `length` business days.

    Guarantees the result is non-decreasing, starts at 0, ends at `length`, and never places
    two nodes on the same day when there is room to separate them.
    """
    days: list[int] = []
    for node in NODE_SKELETON:
        day = round(node["position"] * length)
        # Keep the sequence monotonic and, where the length allows, strictly increasing.
        if days:
            minimum = days[-1] + 1 if length >= len(NODE_SKELETON) - 1 else days[-1]
            day = max(day, minimum)
        days.append(day)
    # Never run past the requested length.
    days = [min(d, length) for d in days]
    # min() above can flatten the tail; re-spread backwards so ordering survives.
    for i in range(len(days) - 2, -1, -1):
        if days[i] > days[i + 1]:
            days[i] = days[i + 1]
    return days


def build_cadence(
    segments: list[str],
    channels: list[str],
    length: int = REFERENCE_LENGTH,
    segment_field: str = "{{SEGMENT_FIELD}}",
    default_lane: str | None = None,
    sms_consent_confirmed: bool = False,
) -> dict:
    """Build the node map. Pure function; no I/O."""
    lanes = [s.strip() for s in segments if s and s.strip()]
    if not lanes:
        raise CadenceError("at least one segment is required")
    if len(lanes) != len(set(slug(s) for s in lanes)):
        raise CadenceError("segment names must be distinct after normalisation")
    if len(lanes) > MAX_LANES:
        raise CadenceError(
            f"{len(lanes)} lanes exceeds the {MAX_LANES} this builder will produce. Past six "
            f"lanes the copy volume outruns any team's ability to iterate on it, and lanes "
            f"stop being distinguishable. Merge the thinnest segments."
        )

    chans = {c.strip().lower() for c in channels if c and c.strip()}
    unknown = chans - KNOWN_CHANNELS
    if unknown:
        raise CadenceError(
            f"unknown channel(s): {', '.join(sorted(unknown))}. Known: {', '.join(sorted(KNOWN_CHANNELS))}"
        )
    if "email" not in chans:
        raise CadenceError(
            "email is required. An SMS-only cold cadence is not a configuration this system "
            "produces: it has no lawful basis in any jurisdiction covered here without prior "
            "express consent, which a cold list does not have."
        )
    if not chans:
        raise CadenceError("at least one channel is required")

    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise CadenceError(f"cadence length must be between {MIN_LENGTH} and {MAX_LENGTH} days")

    # The default lane catches null, malformed and unmapped segment values. Without one,
    # contacts silently disappear at the router.
    if default_lane is None:
        default = lanes[-1]
        default_inferred = True
    else:
        default = default_lane.strip()
        default_inferred = False
        if slug(default) not in {slug(s) for s in lanes}:
            raise CadenceError(
                f"default lane {default!r} is not one of the segments: {', '.join(lanes)}"
            )

    days = scale_days(length)

    # Build the shared node skeleton, dropping channels the client cannot use.
    nodes: list[dict] = []
    n = 0
    skipped: list[dict] = []
    for template, day in zip(NODE_SKELETON, days):
        if template["channel"] not in chans:
            skipped.append({**template, "day": day, "reason": f"{template['channel']} not enabled"})
            continue
        n += 1
        nodes.append(
            {
                "node": f"N{n}",
                "key": template["key"],
                "day": day,
                "channel": template["channel"],
                "purpose": template["purpose"],
                "entry": template["entry"],
                "exit": template["exit"],
            }
        )

    lane_map = []
    for i, lane in enumerate(lanes):
        prefix = lane_prefix(i)
        lane_map.append(
            {
                "lane": lane,
                "slug": slug(lane),
                "prefix": prefix,
                "is_default": slug(lane) == slug(default),
                "node_ids": [f"{prefix}-{node['node']}" for node in nodes],
            }
        )

    followthrough = [
        {
            "node": f"F{i}",
            **template,
            "channel": (
                "email"
                if template["channel"] == "email-or-sms" and "sms" not in chans
                else template["channel"]
            ),
        }
        for i, template in enumerate(FOLLOWTHROUGH_SKELETON, start=1)
    ]

    warnings = _warnings(
        lanes=lanes,
        chans=chans,
        length=length,
        nodes=nodes,
        days=days,
        default_inferred=default_inferred,
        default=default,
        sms_consent_confirmed=sms_consent_confirmed,
    )

    return {
        "config": {
            "segments": lanes,
            "segment_field": segment_field,
            "default_lane": default,
            "channels": sorted(chans),
            "length_days": length,
            "sms_consent_confirmed": sms_consent_confirmed,
        },
        "entry_gates": ENTRY_GATES,
        "nodes": nodes,
        "skipped_nodes": skipped,
        "lanes": lane_map,
        "followthrough": followthrough,
        "terminal_states": TERMINAL_STATES,
        "totals": {
            "lanes": len(lanes),
            "nodes_per_lane": len(nodes),
            "main_sequence_node_instances": len(nodes) * len(lanes),
            "followthrough_nodes": len(followthrough),
            "copy_pieces_required": len(nodes) * len(lanes) + len(followthrough),
        },
        "build_order": _build_order(lane_map, nodes, followthrough, segment_field, chans),
        "warnings": warnings,
    }


def _warnings(
    lanes: list[str],
    chans: set[str],
    length: int,
    nodes: list[dict],
    days: list[int],
    default_inferred: bool,
    default: str,
    sms_consent_confirmed: bool,
) -> list[str]:
    w: list[str] = []

    if "sms" in chans and not sms_consent_confirmed:
        w.append(
            "SMS is enabled but consent has not been confirmed. Cold SMS to a number the "
            "prospect did not supply is a regulatory exposure in every jurisdiction this "
            "system covers, with statutory per-message damages under the TCPA in the US. The "
            "SMS nodes are built, but the entry gate will skip them for every contact without "
            "sms_consent = true. In practice that means SMS becomes usable after the interrupt "
            "branch, not before. Re-run with --sms-consent-confirmed once the client's counsel "
            "has signed off on the consent basis."
        )

    if default_inferred:
        w.append(
            f"No default lane specified, so the last segment ({default!r}) has been used. "
            f"Every contact with a null, malformed or unmapped segment value routes there. "
            f"Confirm that is the right home for them, or set --default-lane explicitly."
        )

    if len(lanes) == 1:
        w.append(
            "One lane means no segmentation. That is a valid starting configuration, but the "
            "segment router is still built so lanes can be added later without restructuring."
        )

    if len(lanes) >= 4:
        w.append(
            f"{len(lanes)} lanes requires {len(nodes) * len(lanes)} distinct messages before "
            f"launch, and the same number again for every copy iteration. Confirm the client "
            f"has the capacity, or start with fewer lanes and split later."
        )

    duplicate_days = [d for d in set(days) if days.count(d) > 1]
    if duplicate_days:
        w.append(
            f"A {length}-day cadence cannot separate all {len(NODE_SKELETON)} skeleton nodes "
            f"onto distinct days; nodes share day(s) {sorted(duplicate_days)}. The 18-hour "
            f"minimum gap between messages to the same contact still applies and will push the "
            f"second message. Consider a longer cadence or fewer nodes."
        )

    if length < REFERENCE_LENGTH:
        w.append(
            f"A {length}-day cadence compresses the reference shape. Front-loading is the point "
            f"of the design, but below about 6 days the spacing stops giving prospects room and "
            f"starts reading as pressure."
        )

    if length > 14:
        w.append(
            f"A {length}-day cadence stretches the reference shape. Past roughly two weeks the "
            f"opening message is no longer context the prospect remembers, so the later nodes "
            f"have to stand alone."
        )

    if "sms" not in chans:
        w.append(
            "SMS is not enabled, so the two nudge nodes are not built. The cadence runs on "
            "email alone, which is the correct default for a cold list."
        )

    return w


def _build_order(
    lane_map: list[dict],
    nodes: list[dict],
    followthrough: list[dict],
    segment_field: str,
    chans: set[str],
) -> list[dict]:
    """The order to build this in a CRM. Ordered by dependency, not by importance."""
    steps: list[dict] = []

    def step(title: str, detail: str) -> None:
        steps.append({"step": len(steps) + 1, "title": title, "detail": detail})

    step(
        "Create the contact fields",
        f"Required on every contact record: {segment_field} (lane routing), "
        f"cadence_state, current_node, lane, fit_score, consent_basis, consent_expiry, "
        f"sms_consent, source_name, timezone. Create these before anything references them; "
        f"a CRM that auto-creates a missing field on first write will create it with the "
        f"wrong type.",
    )
    step(
        "Build the suppression check",
        "A synchronous check against the suppression list at send time, not at enrolment "
        "time. A contact who unsubscribes on day 2 must not receive the day 4 message that "
        "was queued on day 0.",
    )
    step(
        "Build the entry gates",
        "G1 suppression, G2 consent basis, G3 fit score, G4 active enrolment. In that order. "
        "Each failure writes a rejection reason; none of them silently drops a contact.",
    )
    step(
        "Build the segment router",
        f"Reads {segment_field} and assigns one of: "
        f"{', '.join(l['lane'] for l in lane_map)}. "
        f"Default lane: {next(l['lane'] for l in lane_map if l['is_default'])}. "
        f"Routing happens once, at entry, and is never recalculated mid-cadence.",
    )

    for lane in lane_map:
        step(
            f"Build lane: {lane['lane']}",
            f"Create {len(nodes)} nodes with IDs {lane['node_ids'][0]} through "
            f"{lane['node_ids'][-1]}. Same day offsets and same exit conditions as every "
            f"other lane; only the message angle differs.",
        )

    step(
        "Set the sending window on every node",
        "08:00-17:00 in the recipient's timezone, weekdays only, randomised distribution "
        "within the window. "
        + (
            "SMS nodes narrow to 09:00-18:00 recipient local time. "
            if "sms" in chans
            else ""
        )
        + "Minimum 18 hours between any two messages to the same contact across all channels.",
    )
    step(
        "Build the interrupt listener",
        "Triggers: inbound reply on any sending mailbox, {{REQUIRED_INPUT}} supplied, meeting "
        "booked. Not opens. On trigger, cancel every unsent node for that contact atomically, "
        "set cadence_state = 'interrupted', notify a human, enter F1. Cancel, never pause.",
    )
    step(
        "Build the follow-through branch",
        f"Create {len(followthrough)} nodes, {followthrough[0]['node']} through "
        f"{followthrough[-1]['node']}, days "
        f"{followthrough[0]['day']} to {followthrough[-1]['day']} from the interrupt. "
        f"A reply during the follow-through goes to the human handling the thread; it does not "
        f"re-trigger the interrupt.",
    )
    step(
        "Build the terminal states",
        "replied, bounced, unsubscribed, completed-no-response. Every contact must end in "
        "exactly one. Verify there is no path that leaves a contact in no state.",
    )
    step(
        "Build unsubscribe propagation",
        "Immediate suppression across every sending domain and every channel, cancelling every "
        "queued message. Not a per-campaign flag, and not on the next sync.",
    )
    step(
        "Build the re-entry rules",
        "No re-entry after a reply. One re-entry only, at the proof node rather than the "
        "opening node, after a 30-day cooldown, and only where the interrupt was a form or "
        "file with no human contact.",
    )
    step(
        "Load the copy",
        f"{len(nodes) * len(lane_map)} main-sequence messages plus {len(followthrough)} "
        f"follow-through messages. Every personalisation token needs a fallback that reads "
        f"correctly when the field is empty.",
    )
    step(
        "Test with a seed contact per lane",
        f"Enrol one internal test contact in each of the {len(lane_map)} lanes. Confirm: it "
        f"routes to the right lane, every node fires on the right day, the interrupt cancels "
        f"the remainder, an unsubscribe propagates everywhere, and a bounce terminates "
        f"correctly. Do this before a single real contact is enrolled.",
    )
    step(
        "Verify instrumentation",
        "Confirm the CRM emits, on every event: node, lane, sending domain, source batch, and "
        "channel. Without these the cadence cannot be analysed and every later optimisation is "
        "guesswork.",
    )

    return steps


# --------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------


def render_text(c: dict) -> str:
    cfg = c["config"]
    lines: list[str] = []
    a = lines.append

    def rule(char: str = "-", width: int = 92) -> None:
        a(char * width)

    rule("=")
    a("CADENCE NODE MAP")
    rule("=")
    a("")
    a(f"  Segments        {', '.join(cfg['segments'])}")
    a(f"  Segment field   {cfg['segment_field']}")
    a(f"  Default lane    {cfg['default_lane']}")
    a(f"  Channels        {', '.join(cfg['channels'])}")
    a(f"  Length          {cfg['length_days']} business days")
    a("")
    t = c["totals"]
    a(f"  {t['lanes']} lanes x {t['nodes_per_lane']} nodes = "
      f"{t['main_sequence_node_instances']} main-sequence node instances")
    a(f"  Plus {t['followthrough_nodes']} follow-through nodes")
    a(f"  Copy pieces required: {t['copy_pieces_required']}")
    a("")

    if c["warnings"]:
        rule()
        a("WARNINGS")
        rule()
        for wmsg in c["warnings"]:
            wrapped = _wrap(wmsg, 86)
            a(f"  ! {wrapped[0]}")
            for cont in wrapped[1:]:
                a(f"    {cont}")
            a("")

    rule()
    a("ENTRY GATES")
    rule()
    a("  Run in order. A contact failing any gate never enters, and the reason is logged.")
    a("")
    for g in c["entry_gates"]:
        a(f"  {g['id']}  {g['name']}")
        for cont in _wrap(f"Passes when: {g['passes']}", 82):
            a(f"      {cont}")
        for cont in _wrap(f"On failure:  {g['on_failure']}", 82):
            a(f"      {cont}")
        a("")

    rule()
    a("MAIN SEQUENCE - shared skeleton")
    rule()
    a("  Every lane runs these offsets. Only the message angle differs between lanes.")
    a("")
    a(f"  {'NODE':<7}{'DAY':<6}{'CHANNEL':<10}{'PURPOSE'}")
    a("  " + "-" * 88)
    for n in c["nodes"]:
        purpose = _wrap(n["purpose"], 65)
        a(f"  {n['node']:<7}{n['day']:<6}{n['channel']:<10}{purpose[0]}")
        for cont in purpose[1:]:
            a(f"  {'':<23}{cont}")
    a("")
    for n in c["nodes"]:
        a(f"  {n['node']}  entry: {n['entry']}")
        a(f"  {'':<4}exit:  {n['exit']}")
    a("")

    if c["skipped_nodes"]:
        rule()
        a("NODES NOT BUILT")
        rule()
        for s in c["skipped_nodes"]:
            a(f"  day {s['day']:<4}{s['channel']:<8}{s['key']:<12}{s['reason']}")
        a("")

    rule()
    a("LANES")
    rule()
    for lane in c["lanes"]:
        marker = "  (default)" if lane["is_default"] else ""
        a(f"  {lane['prefix']}  {lane['lane']}{marker}")
        a(f"      slug:     {lane['slug']}")
        a(f"      node ids: {', '.join(lane['node_ids'])}")
        a("")

    rule()
    a("INTERRUPT -> FOLLOW-THROUGH BRANCH")
    rule()
    a("  Fires on: inbound reply, {{REQUIRED_INPUT}} supplied, or meeting booked.")
    a("  Not on opens. On trigger, every unsent main-sequence node is cancelled atomically.")
    a("")
    a(f"  {'NODE':<7}{'DAY':<6}{'CHANNEL':<15}{'PURPOSE'}")
    a("  " + "-" * 88)
    for f in c["followthrough"]:
        purpose = _wrap(f["purpose"], 60)
        a(f"  {f['node']:<7}{f['day']:<6}{f['channel']:<15}{purpose[0]}")
        for cont in purpose[1:]:
            a(f"  {'':<28}{cont}")
    a("")
    a("  Days are counted from the interrupt, not from cadence entry.")
    a("")

    rule()
    a("TERMINAL STATES")
    rule()
    for s in c["terminal_states"]:
        a(f"  {s['state']}")
        for label, key in (("Entered", "entered"), ("Suppression", "suppression"), ("Next", "next")):
            for i, cont in enumerate(_wrap(s[key], 74)):
                prefix = f"{label + ':':<13}" if i == 0 else " " * 13
                a(f"      {prefix}{cont}")
        a("")

    rule()
    a("BUILD ORDER")
    rule()
    a("  Ordered by dependency. Do not reorder.")
    a("")
    for s in c["build_order"]:
        a(f"  {s['step']:>2}. {s['title']}")
        for cont in _wrap(s["detail"], 82):
            a(f"      {cont}")
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
        description="Build a concrete cadence node map from a client configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python cadence_builder.py --segments enterprise,mid-market --channels email\n"
        ),
    )
    parser.add_argument(
        "--segments", help="Comma-separated lane names, e.g. enterprise,mid-market,smb"
    )
    parser.add_argument(
        "--channels", default="email", help="Comma-separated channels: email, sms (default: email)"
    )
    parser.add_argument(
        "--length",
        type=int,
        default=REFERENCE_LENGTH,
        help=f"Cadence length in business days (default: {REFERENCE_LENGTH})",
    )
    parser.add_argument(
        "--segment-field",
        default="{{SEGMENT_FIELD}}",
        help="The contact field the router reads",
    )
    parser.add_argument(
        "--default-lane",
        default=None,
        help="Lane for contacts with a null or unmapped segment value (default: the last segment)",
    )
    parser.add_argument(
        "--sms-consent-confirmed",
        action="store_true",
        help="Confirm a lawful SMS consent basis exists. Suppresses the SMS compliance warning; "
        "does not change the gate, which still checks sms_consent per contact.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="JSON file with keys: segments, channels, length, segment_field, default_lane, "
        "sms_consent_confirmed. Command-line arguments take precedence over file values.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    args = parser.parse_args(argv)

    file_cfg: dict = {}
    if args.config:
        try:
            with open(args.config, encoding="utf-8") as fh:
                file_cfg = json.load(fh)
        except OSError as exc:
            print(f"error: could not read {args.config!r}: {exc}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"error: {args.config!r} is not valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(file_cfg, dict):
            print(f"error: {args.config!r} must contain a JSON object", file=sys.stderr)
            return 2

    def resolve(name: str, cli_value, default):
        """CLI beats file beats default."""
        if cli_value != default:
            return cli_value
        return file_cfg.get(name, cli_value)

    segments_raw = args.segments or file_cfg.get("segments")
    if not segments_raw:
        parser.error("--segments is required (or supply it in --config)")
    segments = (
        segments_raw
        if isinstance(segments_raw, list)
        else str(segments_raw).split(",")
    )

    channels_raw = resolve("channels", args.channels, "email")
    channels = (
        channels_raw if isinstance(channels_raw, list) else str(channels_raw).split(",")
    )

    try:
        cadence = build_cadence(
            segments=[str(s) for s in segments],
            channels=[str(c) for c in channels],
            length=int(resolve("length", args.length, REFERENCE_LENGTH)),
            segment_field=str(resolve("segment_field", args.segment_field, "{{SEGMENT_FIELD}}")),
            default_lane=resolve("default_lane", args.default_lane, None),
            sms_consent_confirmed=bool(
                resolve("sms_consent_confirmed", args.sms_consent_confirmed, False)
            ),
        )
    except CadenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (TypeError, ValueError) as exc:
        print(f"error: invalid configuration: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(cadence, indent=2))
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(render_text(cadence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Cadence Specification

The generic multi-touch outbound cadence architecture. This document describes structure only:
nodes, timing, routing, branch conditions and terminal states.

**No message copy appears in this file, and none should be added to it.** Copy is per-client
and lives in `05-copy/`. The point of separating them is that the architecture can be reviewed,
argued with and reused without anyone reading a word of marketing.

---

## Design principles

Five constraints shape everything below.

**1. Timing is shared; messaging is not.** Every lane runs the same schedule. Only the angle
changes. This is not a stylistic choice — it means one timing change is tested once rather
than once per lane, and it means the node map stays legible when there are five lanes.

**2. A prospect is in exactly one place at a time.** No contact is ever in two active cadences,
and no contact is ever in both the main sequence and the interrupt branch. Enforced in the
database (`07-data/schema.sql`), not by convention in the CRM. A prospect receiving two
unrelated sequences from the same company complains at several times the base rate.

**3. Any signal of intent ends the pitch.** The moment a prospect does the thing the cadence was
asking for, the cadence stops. A prospect who replies and then receives touch four has been
told that nobody read their reply.

**4. Every exit is explicit.** There is no "falls off the end." Every contact ends in a named
terminal state with a defined next action, including the ones who never responded.

**5. Compliance is structural.** Suppression, consent checks and opt-out propagation are nodes
and gates in the flow, not a footer someone remembers to add.

---

## Shape of the flow

```
                          ┌─────────────────┐
                          │  Entry gate     │  eligibility, consent, suppression
                          └────────┬────────┘
                                   │ passes
                          ┌────────▼────────┐
                          │  Segment router │  reads {{SEGMENT_FIELD}}
                          └────────┬────────┘
              ┌────────────────────┼────────────────────┐
              │                    │                    │
        ┌─────▼─────┐        ┌─────▼─────┐        ┌─────▼─────┐
        │  Lane A   │        │  Lane B   │        │  Lane C   │   one lane per
        │  N1..N7   │        │  N1..N7   │        │  N1..N7   │   {{SEGMENT_LANE}}
        └─────┬─────┘        └─────┬─────┘        └─────┬─────┘
              └────────────────────┼────────────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
        ┌─────────▼─────────┐            ┌──────────▼──────────┐
        │  INTERRUPT        │            │  Main sequence      │
        │  prospect supplies│            │  runs to completion │
        │  {{REQUIRED_INPUT}}│           │                     │
        │  F1..F4           │            │                     │
        └─────────┬─────────┘            └──────────┬──────────┘
                  │                                 │
                  └────────────────┬────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Terminal state             │
                    │  replied / bounced /        │
                    │  unsubscribed / completed   │
                    └─────────────────────────────┘
```

---

## Entry gate

Before a contact enters any lane, four checks run in order. A contact failing any of them never
enters the cadence and is written to the rejection log with the reason.

| # | Gate | Passes when | On failure |
|---|---|---|---|
| G1 | **Suppression** | The address, and its domain if the domain is suppressed, is absent from the suppression list | Reject, terminal, never re-enters |
| G2 | **Consent basis** | A lawful basis is recorded for this contact's jurisdiction (see below) | Reject, hold for review |
| G3 | **Fit score** | Score is at or above `{{ICP_SCORE_THRESHOLD}}` | Reject to the excluded pool, re-evaluate at next enrichment |
| G4 | **Active enrolment** | Contact is not already in an active cadence, and has not been in one within the cooldown window | Reject, queue for after the cooldown |

**On G2, by jurisdiction.** This gate is the reason the cadence branches on geography before it
branches on anything commercial.

| Jurisdiction | Basis required before first touch | Recorded as |
|---|---|---|
| **US** (CAN-SPAM) | None required for email. Opt-out must be honoured within 10 business days. | `basis = 'can-spam-optout'` |
| **UK / EU** (GDPR + PECR) | Legitimate interest, with a completed and documented balancing test on file (`{{LIA_REFERENCE}}`). Corporate subscribers only — never a personal address, never a sole trader or partnership in the UK, which PECR treats as an individual. | `basis = 'legitimate-interest'` with the LIA reference |
| **Canada** (CASL) | Consent, express or implied. Implied consent expires: 6 months from an inquiry, 2 years from the end of a business relationship. | `basis = 'express-consent'` or `'implied-consent'` with the expiry date |
| **SMS, any jurisdiction** | Prior express consent from the individual, for that number, for marketing. A number obtained from a data vendor is not consent. | `sms_consent = true` with source and date |

**SMS is off by default.** A cold SMS to a number the prospect did not give is a regulatory
problem in every jurisdiction this system covers, and in the US it carries statutory damages per
message under the TCPA. The SMS nodes below exist for the case where the prospect has supplied
their number — which in practice means after the interrupt branch fires, not before. If a client
wants SMS in the main cold sequence, that is a conversation with their counsel, not a
configuration change. `cadence_builder.py` will build the nodes; the gate still has to pass.

---

## Segment router

A single routing node reads `{{SEGMENT_FIELD}}` on the contact record and assigns a lane.

- The field is configurable per client and is a **contact or account attribute**, not a
  behaviour: company size band, region, role seniority, technology in use, source. Behaviour is
  what the interrupt branch is for.
- Lanes are exhaustive and mutually exclusive. Every possible value maps to exactly one lane.
- A **default lane** is mandatory. Any contact whose `{{SEGMENT_FIELD}}` is null, malformed, or
  an unmapped value routes there. Without it, contacts silently vanish from the flow — the most
  common cadence bug there is, and the hardest to notice, because nothing errors.
- Routing happens **once**, at entry. A contact whose segment field changes mid-cadence stays in
  the lane it entered. Re-routing mid-flight produces prospects who receive touch 2 of one lane
  and touch 3 of another, which reads as incoherence.

Each lane has:

| Property | Shared across lanes | Varies by lane |
|---|---|---|
| Node count and numbering | yes | — |
| Day offsets | yes | — |
| Channel per node | yes | — |
| Exit and terminal conditions | yes | — |
| Messaging angle | — | yes |
| Proof points referenced | — | yes |
| The specific ask at each node | — | yes |

---

## Main sequence

Eight days, seven nodes. Day offsets are **business days from entry**, not calendar days: a
contact entering on a Thursday receives node 2 on the following Monday, not on Saturday.

### Node table

| Node | Day | Channel | Purpose | Entry condition | Exit condition |
|---|---|---|---|---|---|
| **N1** | 0 | Email | Open. State why this contact specifically, and make the primary ask. | Entry gate passed; lane assigned | Sent, and no interrupt signal within the wait |
| **N2** | 1 | SMS | Short nudge. Adds a channel without adding an argument. | N1 sent and not bounced; `sms_consent = true`; else skip to N3 | Sent, or skipped for no consent |
| **N3** | 2 | Email | Second angle on the same problem. Not a "just following up." | N1 sent; no interrupt signal | Sent |
| **N4** | 4 | Email | Proof. A concrete, substantiable result. Lowest-friction ask of the sequence. | N3 sent; no interrupt signal | Sent |
| **N5** | 5 | SMS | Second nudge, referencing the ask rather than repeating it. | N4 sent; `sms_consent = true`; else skip to N6 | Sent, or skipped for no consent |
| **N6** | 6 | Email | Address the single most common objection directly. | N4 sent; no interrupt signal | Sent |
| **N7** | 8 | Email | Close the loop. Ask permission to stop, and make the last touch easy to reply to. | N6 sent; no interrupt signal | Sent → terminal `completed-no-response` |

### Why this shape

- **Front-loaded, then spaced.** Days 0, 1, 2 then 4, 5, 6 then 8. Attention decays fast; three
  touches in the first 72 hours is where most replies come from. After that the spacing widens,
  because a prospect who has not responded to three messages needs room, not volume.
- **Seven touches, not fifteen.** Past roughly seven touches the marginal reply rate collapses
  and the complaint rate does not. A fifteen-touch sequence generates most of its complaints in
  the last eight touches and most of its meetings in the first four.
- **One ask per node.** Each node asks for one thing. Nodes that ask for two get neither.
- **N4 is the pivot.** By day four a prospect who was going to reply to a pitch has not. N4
  stops pitching and shows evidence, at the lowest-friction ask in the sequence. It is
  consistently the second-highest-replying node after N1.
- **N7 is not a threat.** "Closing the file" as a manipulation reliably generates replies from
  people who then do not convert, and irritation from everyone else. N7 asks a genuine question
  and accepts the answer.

### Timing rules

| Rule | Value |
|---|---|
| Sending window | 08:00–17:00 in the **recipient's** timezone |
| Days | Monday to Friday. No weekend sends, no public holidays in the recipient's country. |
| Distribution within the window | Randomised. Never a fixed minute, never all at the top of the hour. |
| Minimum gap between two messages to the same contact | 18 hours, across all channels combined |
| SMS-specific window | 09:00–18:00 recipient local time, weekdays only — narrower than email, because the regulatory tolerance is narrower |
| Per-mailbox daily cap | `{{DAILY_SEND_CEILING}}`, enforced at the platform, not only in the sequence |

**On timezone.** A contact with no known timezone uses the account's country, then the
company's registered country, then the default sending window. It never uses the sender's
timezone. A message arriving at 03:00 is not read at 03:00; it is read at 09:00, at the bottom
of the overnight pile.

---

## Interrupt branch

The main sequence assumes silence. The interrupt branch handles what happens when a prospect
stops being silent.

### Trigger conditions

Any of these fires the interrupt, immediately, at any point in the main sequence:

| Trigger | Detected by | Latency |
|---|---|---|
| **Reply received** | Inbound message on any sending mailbox, matched to the contact | Near-real-time; polled at most every 5 minutes |
| **`{{REQUIRED_INPUT}}` supplied** | The prospect provides the specific artifact or information the cadence asked for — a form completion, a file upload, a document, a set of numbers | On receipt |
| **Meeting booked** | Booking system webhook | On receipt |
| **Positive intent signal, if instrumented** | The client's own definition, agreed in the intake. Must be a deliberate act by the prospect, never an open. | On receipt |

**An open is not a trigger.** Open tracking is unreliable enough that treating it as intent
produces interrupts on prospects who did nothing, and those prospects then receive a message
that assumes an interaction that never happened.

### On trigger

Executed as one atomic transaction. A partial execution — main sequence cancelled but
follow-through never started, or both running at once — is the worst failure mode in the whole
architecture.

1. **Cancel every unsent node** of the main sequence for this contact, across all channels.
2. Set `cadence_state = 'interrupted'` and record which node was pending and which trigger fired.
3. **Notify a human** within the client's working hours. The interrupt branch is
   human-in-the-loop by design.
4. Enter the follow-through branch at F1.

**The reason for cancelling rather than pausing** is that a paused sequence resumes. A prospect
who replied on Tuesday and receives touch 4 on Thursday because a pause expired has been told,
unambiguously, that nobody is reading. Cancellation is recoverable — the re-entry rules below
handle the case where the conversation goes nowhere — and it fails in the safe direction.

### Follow-through branch

Days are counted from the interrupt, not from original cadence entry.

| Node | Day | Channel | Purpose | Entry condition | Exit condition |
|---|---|---|---|---|---|
| **F1** | 0 | Email | Acknowledge, within one business hour. Confirm what was received and state what happens next and when. | Interrupt fired | Sent |
| **F2** | 1 | Email | Deliver whatever was promised in F1, or the next concrete step. | F1 sent | Sent |
| **F3** | 3 | Email | Follow up on F2. One follow-up, not a new sequence. | F2 sent; no response | Sent |
| **F4** | 6 | Email or SMS | Final follow-through. Explicitly offers to close the thread. | F3 sent; no response | Sent → re-entry evaluation |

- **F1 is not optional and is not automated past the acknowledgement.** A prospect who supplied
  something and got an autoresponder has learned the whole thing was a machine.
- **A reply during the follow-through does not re-trigger the interrupt.** It goes to the human
  handling the thread. Interrupts do not nest.
- **SMS at F4 is permitted** where the prospect supplied their number as part of
  `{{REQUIRED_INPUT}}` and consent was recorded. This is the normal path by which SMS becomes
  usable at all.

### Re-entry rules

What happens when the follow-through ends without a resolution.

| Situation | Outcome |
|---|---|
| Prospect responded at any point during F1–F4 | Terminal `replied`. Handled by a human from here. Never re-enters an automated cadence. |
| Prospect explicitly declined | Terminal `replied`, disposition `not-interested`. Suppressed for 180 days, then eligible for a **new** cadence, never a resumption of this one. |
| Prospect asked to be contacted later at a stated time | Terminal `replied`, disposition `deferred`. Scheduled task at the stated date. Not an automated re-entry. |
| **No response to F1–F4, interrupt was a reply** | Terminal `completed-no-response`. Does not re-enter. A prospect who replied and then went quiet has been engaged once; putting them back into a cold sequence is a complaint waiting to happen. |
| **No response to F1–F4, interrupt was a form or file with no human contact** | Eligible to re-enter the main sequence **once**, after a 30-day cooldown, at N4, never at N1. Cap of one re-entry ever. |
| Bounced during follow-through | Terminal `bounced`. |
| Unsubscribed at any point | Terminal `unsubscribed`. Immediate, everywhere. |

**Why re-entry starts at N4 and not N1.** N1 introduces the sender and the reason for contact.
A prospect who has already interacted has had that introduction. Restarting at N1 reads as a
system that forgot them, which is worse than not contacting them at all.

---

## Terminal states

Every contact ends in exactly one of these. There is no other exit.

| State | Entered when | Suppression | Re-eligible | Next action |
|---|---|---|---|---|
| **`replied`** | Any human reply, at any node | Removed from automated sending; not suppressed from human contact | Only by a human decision | Owned by a named person. Disposition recorded within 2 business days. |
| **`bounced`** | Hard bounce, or 3 soft bounces in 7 days | Address suppressed permanently | Never for this address | Flag the `{{SOURCE_NAME}}` batch. Three or more bounces from one batch means the batch was not verified — quarantine the rest of it. |
| **`unsubscribed`** | Opt-out via any mechanism, any channel | Suppressed permanently across every domain, every channel, every future client-side campaign | Never | See propagation rules below. |
| **`completed-no-response`** | N7 sent, or F4 sent, with no response | Not suppressed. Cooled down. | After 90 days, into a different cadence with a different angle | Return to the pool. Re-enrich before re-enrolling — 90 days is long enough for the role, the company or the problem to have changed. |

### Unsubscribe propagation

An opt-out is not a per-campaign event. When it fires:

1. Add to the suppression list **immediately**, before any queued message can send. Not on the
   next sync.
2. Cancel every unsent node for that contact, in every cadence, on every channel.
3. Suppress across **every sending domain in `{{SENDING_DOMAIN_LIST}}`**, not just the one that
   sent the message. The prospect did not opt out of a domain; they opted out of the client.
4. Suppress the **contact**, not just the address, where the same person is known under more
   than one address.
5. Propagate to SMS if the opt-out arrived by email, and to email if it arrived by SMS
   (`{{SMS_STOP_KEYWORD}}`). A prospect who says stop has said stop.
6. Record the timestamp, source and channel. This record is the evidence of compliance and is
   the first thing a regulator asks for.

**Timing obligations.** CAN-SPAM allows 10 business days; CASL allows 10 business days; GDPR
and PECR require action without undue delay. Build to the strictest reading — immediate — and
the jurisdictional differences stop mattering. There is no operational reason to take ten days.

### Bounce handling

| Type | Definition | Action |
|---|---|---|
| **Hard** | Permanent: no such address, no such domain | Terminal `bounced`, suppress permanently, on the first occurrence |
| **Soft** | Temporary: mailbox full, server unavailable, greylisted | Retry at the next node. Three in 7 days is treated as hard. |
| **Block** | The receiving server refused the message | Not a contact-level event. Pause the **sending domain** and diagnose. Do not suppress the contact. |

A block response is a domain signal wearing a contact's clothes. Suppressing the contact hides
the problem and lets it continue.

---

## Instrumentation

The cadence must emit enough to answer these questions without a database migration:

| Question | Requires |
|---|---|
| Which node produces the most replies? | Reply events joined to the node that preceded them |
| Which lane converts best? | Lane recorded on every send and reply event |
| Where do prospects drop out? | Send count per node per lane |
| How often does the interrupt fire, and from which node? | Interrupt events with the pending node recorded |
| Does the follow-through convert? | F-node outcomes tracked separately from main sequence outcomes |
| Which source batch bounces? | `{{SOURCE_NAME}}` on every contact and every bounce event |
| Which domain is degrading? | Sending domain on every send event |

Every one of these is a column on the send and reply event tables in `07-data/schema.sql`. If
the CRM cannot emit them, that is a finding, not a limitation to work around.

---

## What this architecture deliberately excludes

Listed because each one gets proposed, and the reasons for refusing are the same every time.

| Excluded | Why |
|---|---|
| More than 7 main-sequence touches | Marginal reply rate collapses; complaint rate does not |
| Open-triggered branching | Open data is too unreliable to branch on, and branching on it produces messages that reference interactions that never happened |
| Mid-cadence re-segmentation | Produces incoherent sequences where consecutive touches come from different lanes |
| Automatic re-entry after a reply | The prospect engaged with a person; putting them back into automation is the fastest way to lose them |
| Cold SMS before consent | Regulatory exposure in every jurisdiction here, with statutory per-message damages in the US |
| Attachments in cold email | Strong spam signal, and most corporate filters strip or quarantine them |
| Personalisation tokens with no fallback | A message opening "Hi ," is the single most visible failure a prospect can see |
| Pausing rather than cancelling on interrupt | A pause that expires sends a pitch to someone who already replied |

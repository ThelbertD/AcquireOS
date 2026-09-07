# CRM Build Checklist

Implementing the cadence in `{{CRM_NAME}}`. Platform-agnostic: every item below is something
every automation platform can do, though they call it different things and several of them do
it wrongly by default. The **Platform differences** section at the end covers where.

Run `04-cadence/cadence_builder.py` first. It produces the node map and the build order this
checklist assumes.

**Client:** `{{CLIENT_NAME}}`
**Platform:** `{{CRM_NAME}}`
**Lanes:** `{{SEGMENT_LANES}}`
**Channels:** `{{CHANNELS_AVAILABLE}}`
**Built by:** ____________
**Date:** ____________

---

## 1. Fields

Create every field before anything references it. A platform that auto-creates a missing field
on first write will create it with the wrong type, and changing a field's type later usually
means dropping it and losing what is in it.

- [ ] `{{SEGMENT_FIELD}}` — the value the router reads. Type: single-select or text.
- [ ] `lane` — the lane assigned at entry. Written once, never recalculated.
- [ ] `cadence_state` — enum: `pending`, `active`, `interrupted`, `replied`, `bounced`,
      `unsubscribed`, `completed-no-response`
- [ ] `current_node` — the last node sent
- [ ] `fit_score` — integer, from the enrichment layer
- [ ] `consent_basis` — enum: `can-spam-optout`, `legitimate-interest`, `express-consent`,
      `implied-consent`
- [ ] `consent_expiry` — date. Required for implied consent under CASL; null otherwise.
- [ ] `sms_consent` — boolean, defaulting to **false**
- [ ] `sms_consent_source` — where and when the number was given
- [ ] `source_name` — which import batch this contact came from
- [ ] `timezone` — the recipient's, not the sender's
- [ ] `jurisdiction` — drives which compliance rules apply
- [ ] `interrupt_trigger` — what fired the interrupt, null if none
- [ ] `interrupt_pending_node` — which node was next when the interrupt fired
- [ ] `reentry_count` — integer, defaulting to 0, capped at 1

**Check:** every field exists with the right type, and `sms_consent` defaults to false rather
than null. A null boolean evaluates as truthy in more platforms than it should.

---

## 2. Suppression

This is built before anything that can send, so that no configuration mistake later can result
in a message to a suppressed address.

- [ ] Suppression list exists and is populated from `07-data/schema.sql`
- [ ] The check runs **at send time**, not at enrolment time
- [ ] The check covers the address **and** the domain, where whole domains are suppressed
- [ ] The check is synchronous and blocking. A queued message does not send while the check is
      pending.
- [ ] Suppression is **global** across every sequence, every sending domain in
      `{{SENDING_DOMAIN_LIST}}`, and every channel

**Check:** add a test address to the suppression list, enrol it, and confirm nothing sends.
Then enrol a test address, let it reach a mid-sequence node, suppress it, and confirm the
remaining nodes do not send. The second test is the one that fails on most platforms.

> **The failure this prevents.** Almost every platform's default is to evaluate enrolment
> criteria once, at entry, and then run the sequence to completion regardless of what changes.
> A contact who unsubscribes on day 2 receives the day 4 message that was queued on day 0. This
> is a compliance breach, and it is the single most common one in cold email operations.

---

## 3. Entry gates

Build in order. Each failure writes a reason to a rejection log. Nothing is silently dropped.

- [ ] **G1 Suppression** — address or domain on the suppression list → reject, terminal
- [ ] **G2 Consent basis** — `consent_basis` is null, or `consent_expiry` has passed → reject,
      hold for review
- [ ] **G3 Fit score** — `fit_score` below `{{ICP_SCORE_THRESHOLD}}` → reject to the excluded
      pool
- [ ] **G4 Active enrolment** — already in an active cadence, or within the cooldown → reject,
      queue
- [ ] Every rejection writes a reason. A contact that vanishes with no log entry is a bug you
      will not find.

**Check:** enrol one test contact that fails each gate and confirm the rejection reason appears.

---

## 4. Segment router

- [ ] Reads `{{SEGMENT_FIELD}}` and assigns `lane`
- [ ] Every possible value maps to exactly one lane
- [ ] A **default lane** exists and catches null, empty, malformed and unmapped values
- [ ] Routing runs once, at entry. It is not re-evaluated at any later node.
- [ ] `lane` is written to the contact record, not held only in the workflow's state

**Check:** enrol test contacts with (a) each valid value, (b) a null value, (c) a value that is
not in the map, (d) a value differing only in case or whitespace. All four must land in a lane.

> **The failure this prevents.** Without an explicit default, most platforms drop a contact
> whose branch condition matches nothing. It does not error and it does not log. The contact
> simply is not in the sequence, and the first sign is a list that is smaller than it should be
> three weeks later.

---

## 5. Nodes

For each lane, for each node in the map:

- [ ] Node created with the correct day offset
- [ ] Delay is measured in **business days from entry**, not from the previous node
- [ ] Sending window: 08:00–17:00 in the **recipient's** timezone
- [ ] Weekday only. No weekend sends.
- [ ] Public holidays in the recipient's country excluded
- [ ] Distribution within the window randomised — not a fixed minute, not the top of the hour
- [ ] Minimum 18 hours between any two messages to the same contact, across all channels
- [ ] Per-mailbox daily cap of `{{DAILY_SEND_CEILING}}` enforced at the platform level
- [ ] Every node writes `current_node` on send

**On day offsets.** Offsets are from entry, not cumulative from the previous node. Building them
as "wait 2 days" chained from each node produces drift: a node that is skipped, delayed by a
weekend, or held by a rate limit shifts everything after it. Anchoring to entry means one
delayed node does not move the rest.

**Check:** enrol a test contact on a Thursday. Confirm the day-1 node fires on Friday and the
day-2 node fires on Monday, not on Saturday.

---

## 6. SMS nodes

Skip this section if `sms` is not in `{{CHANNELS_AVAILABLE}}`.

- [ ] Every SMS node checks `sms_consent = true` before sending, as a hard gate
- [ ] Contacts without consent **skip** the node and continue the sequence. They do not exit.
- [ ] SMS window is 09:00–18:00 recipient local time, weekdays only
- [ ] `{{SMS_STOP_KEYWORD}}` handled automatically by `{{SMS_PROVIDER}}` **and** written back to
      the suppression list
- [ ] `{{SMS_HELP_KEYWORD}}` returns the client's identity and contact details
- [ ] Sender ID is `{{SMS_SENDER_ID}}` and is consistent across every SMS node
- [ ] Every message identifies the sender — an SMS from an unknown number with no identification
      is a complaint

**Check:** send a test SMS, reply with the stop keyword, then confirm (a) SMS stops, and (b) the
contact is suppressed for **email** as well.

> **The failure this prevents.** Most SMS providers handle opt-out at the provider level only.
> The prospect stops receiving SMS, the provider is compliant, and the email sequence keeps
> running because nothing told it. A prospect who says stop has said stop.

---

## 7. Interrupt branch

The hardest part to build correctly, and the part most worth testing hardest.

- [ ] Reply detection is connected to **every** sending mailbox, not just the primary
- [ ] Replies are matched to the contact record, not just to the thread
- [ ] `{{REQUIRED_INPUT}}` supplied fires the interrupt
- [ ] Meeting booked fires the interrupt
- [ ] **Opens do not fire the interrupt**
- [ ] Auto-replies (out-of-office, bounce notifications, delivery receipts) do **not** fire the
      interrupt
- [ ] On trigger, every unsent node for that contact is **cancelled**, not paused
- [ ] Cancellation is atomic. There is no state where the main sequence is cancelled but the
      follow-through has not started, or where both are running.
- [ ] `cadence_state` set to `interrupted`, `interrupt_trigger` and `interrupt_pending_node`
      recorded
- [ ] A human is notified within the client's working hours
- [ ] Follow-through branch entered at F1

**Check, and do all four:**

1. Enrol a test contact. Reply from the recipient side at node 2. Confirm nodes 3 onward never
   send and the follow-through starts.
2. Send an out-of-office auto-reply. Confirm the interrupt does **not** fire.
3. Reply during the follow-through. Confirm it goes to the human and does not restart anything.
4. Reply at the exact moment a node is queued to send. Confirm the queued message is cancelled
   rather than sent.

> **The failure this prevents.** Pausing instead of cancelling is the default on several
> platforms, and pauses expire. A prospect who replied on Tuesday receives touch 4 on Thursday
> because a 48-hour pause elapsed. That single behaviour ends more conversations than bad copy
> does.

---

## 8. Follow-through branch

- [ ] F1 through F4 built, with day offsets from the **interrupt**, not from cadence entry
- [ ] F1 fires within one business hour
- [ ] F1 is an acknowledgement written by a person, or approved by one, before it can send
- [ ] A reply during F1–F4 routes to the human owning the thread and does not re-trigger the
      interrupt
- [ ] Interrupts do not nest
- [ ] F4 exits to the re-entry evaluation, not to nothing

---

## 9. Terminal states

- [ ] All four states exist: `replied`, `bounced`, `unsubscribed`, `completed-no-response`
- [ ] Every path through the cadence ends in exactly one
- [ ] No path leaves a contact with `cadence_state = 'active'` and no pending node

**Check:** query for contacts in `active` with no scheduled node. The correct answer is zero,
every time. Run this weekly; it is the canary for every branch bug in the build.

### Bounces

- [ ] Hard bounce → terminal `bounced`, suppress permanently, on first occurrence
- [ ] Soft bounce → retry at the next node; 3 in 7 days is treated as hard
- [ ] Block response → does **not** suppress the contact. Alerts on the sending domain instead.

> A block is a domain problem wearing a contact's clothes. Suppressing the contact hides it and
> lets it continue.

### Unsubscribes

- [ ] Suppression is immediate, before any queued message can send
- [ ] Every unsent node for that contact is cancelled, in every cadence, on every channel
- [ ] Propagates across every domain in `{{SENDING_DOMAIN_LIST}}`
- [ ] Propagates across channels: an email opt-out stops SMS, and the reverse
- [ ] Suppresses the **contact**, not just the address, where one person is known under several
- [ ] Timestamp, source and channel recorded
- [ ] `{{UNSUBSCRIBE_URL}}` works from every message and requires no login
- [ ] `List-Unsubscribe` and `List-Unsubscribe-Post` headers present on every email

**Check:** unsubscribe a test contact from a message sent by one domain, then confirm a
sequence running on a **different** domain also stops.

---

## 10. Re-entry

- [ ] No re-entry after a reply, under any circumstances
- [ ] One re-entry only, ever. `reentry_count` capped at 1.
- [ ] Re-entry only where the interrupt was a form or file with no human contact
- [ ] Re-entry starts at the proof node, not the opening node
- [ ] 30-day cooldown enforced
- [ ] `completed-no-response` contacts return to the pool after 90 days, into a **different**
      cadence, and are re-enriched first

---

## 11. Instrumentation

Every send and reply event must carry these. Retrofitting them after launch means the first
month of data cannot be analysed.

- [ ] `node` on every event
- [ ] `lane` on every event
- [ ] `sending_domain` on every event
- [ ] `source_name` on every event
- [ ] `channel` on every event
- [ ] Interrupt events record the trigger and the pending node
- [ ] Follow-through outcomes tracked separately from main-sequence outcomes

**Check:** these are the columns on the send and reply event tables in `07-data/schema.sql`. If
`{{CRM_NAME}}` cannot emit one of them, that is a finding to raise, not a gap to work around.

---

## 12. Pre-launch test

Do this with internal test contacts before a single real contact is enrolled.

- [ ] One test contact enrolled per lane, all routing correctly
- [ ] One test contact with a null `{{SEGMENT_FIELD}}` lands in the default lane
- [ ] Every node fires on the correct day, in the correct window, in the recipient's timezone
- [ ] A Thursday enrolment skips the weekend
- [ ] Reply at node 2 cancels the remainder and starts the follow-through
- [ ] Out-of-office does not fire the interrupt
- [ ] Unsubscribe propagates across domains and channels
- [ ] Hard bounce terminates and suppresses
- [ ] Suppressed contact receives nothing
- [ ] Every personalisation token renders, and every fallback reads correctly when the source
      field is empty
- [ ] No message contains a literal `{{TOKEN}}` string
- [ ] Physical postal address `{{CLIENT_POSTAL_ADDRESS}}` present in every email
- [ ] Unsubscribe link present and working in every email
- [ ] Query for `active` contacts with no pending node returns zero

**Sign-off:** ____________  **Date:** ____________

---

## Platform differences

Where automation platforms diverge. Check each of these against `{{CRM_NAME}}` specifically —
the behaviour is rarely documented and is usually discovered in production.

### Delay handling

| Behaviour | What to check |
|---|---|
| Delays measured from the previous node rather than from entry | Chained delays drift. One skipped or rate-limited node shifts everything after it. Build offsets from entry where the platform allows it; where it does not, add a correction step at each node. |
| "Business days" excludes weekends but not holidays | Most platforms handle weekends. Almost none handle public holidays, and none handle the recipient's country's holidays. Usually needs a custom exclusion list. |
| Timezone is the account's, not the contact's | Very common default. A contact with no timezone silently uses the sender's, which means overnight delivery to another continent. |
| Delay resolution is per-day, not per-hour | Some platforms cannot express "day 4, between 09:00 and 17:00" and will fire at midnight. |
| Delays evaluated at enrolment rather than at each step | Means a delay cannot respond to anything that changed since entry. |

### Branch merging

| Behaviour | What to check |
|---|---|
| Branches cannot rejoin | Some platforms require every branch to run to its own end. With N lanes this means N complete copies of the sequence, and a timing change becomes N edits. Confirm before designing lanes. |
| Merged branches lose branch context | After a merge, `lane` may no longer be readable in the workflow's state. This is why `lane` is written to the contact record rather than held in workflow state. |
| Nested branches limited in depth | Segment routing plus the interrupt branch is two levels. A few platforms cap at two, which leaves no room. |
| An unmatched branch condition drops the contact silently | The reason the default lane is mandatory. Test it explicitly. |

### Unsubscribe propagation

| Behaviour | What to check |
|---|---|
| Unsubscribe is per-sequence, not global | The prospect opts out of one sequence and stays enrolled in others. Test with two concurrent sequences. |
| Unsubscribe is per-sending-domain | Multi-domain estates are exactly the case this breaks. Test across two domains. |
| SMS opt-out handled at the provider, not the CRM | The provider stops SMS and stays compliant; the email sequence keeps running. Test the cross-channel path in both directions. |
| Suppression checked at enrolment, not at send | The failure in section 2. Test by suppressing mid-sequence. |
| Suppression syncs on a schedule rather than immediately | A nightly sync means up to 24 hours of sends to someone who opted out. |
| `List-Unsubscribe` header not set by default | Frequently a per-sequence setting rather than an account-wide one. |

### Reply detection

| Behaviour | What to check |
|---|---|
| Only monitors the primary mailbox | Replies to the other mailboxes in the estate are never seen, so the interrupt never fires for those contacts. |
| Treats auto-replies as replies | Out-of-office fires the interrupt, cancels the sequence, and notifies a human for nothing. |
| Matches on thread, not on contact | A prospect replying from a different address, or forwarding to a colleague who replies, is not matched. |
| Polling interval measured in hours | Determines how long a replying prospect can still receive the next queued message. Anything above 15 minutes needs a compensating check immediately before send. |

### Rate limiting

| Behaviour | What to check |
|---|---|
| Platform caps are far above what a warming domain survives | Set the cap at the platform level as well as in the sequence, so a sequence misconfiguration cannot dump a week of volume in an hour. |
| Rate-limited messages queue and then burst | The burst pattern is exactly what section 5 randomisation is meant to prevent. Check what happens to a queue after a limit clears. |
| Caps are per-account, not per-mailbox | Per-mailbox is the unit that matters. An account-level cap distributed unevenly can put one mailbox far over its ceiling. |

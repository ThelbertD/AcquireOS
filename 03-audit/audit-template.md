# Deliverability Audit — `{{CLIENT_NAME}}`

**Prepared by:** `{{AUDITOR_NAME}}`, `{{AGENCY_NAME}}`
**Date:** `{{AUDIT_DATE}}`
**Sending data reviewed:** `{{AUDIT_PERIOD}}`
**Domains in scope:** `{{SENDING_DOMAIN_LIST}}`
**Primary domain:** `{{PRIMARY_DOMAIN}}`
**ESP:** `{{ESP_NAME}}`

---

## How to use this template

This is the source document for the audit deliverable. It is filled in one of two ways:

- **By hand**, working top to bottom, replacing every `{{PLACEHOLDER}}` and every
  `[ ... ]` prompt.
- **By script**, by writing findings into a JSON file matching `sample-input.json` and running
  `python 03-audit/audit_report.py --input findings.json`.

Sections with no findings are not deleted. "Checked, nothing found" is a result the client is
paying for, and an audit that only lists problems reads as a list of complaints rather than an
assessment.

**Severity levels.** Every finding carries one.

| Severity | Meaning | Response time |
|---|---|---|
| `critical` | Mail is being lost or rejected now, or a legal exposure exists now | Same day |
| `high` | Materially suppressing inbox placement, or will become critical if unaddressed | Within a week |
| `medium` | Measurable drag on performance | Within the month |
| `low` | Best practice not met; little current impact | When convenient |
| `info` | Observation with no action attached | None |

**Estimated impact.** State impact as a concrete, checkable claim, not an adjective. "Roughly
one in five messages to Microsoft 365 recipients is not being delivered" is useful. "Hurting
deliverability" is not. Where the effect cannot be quantified from available data, say so
explicitly rather than guessing.

---

## 1. Summary

[ Three to five sentences. What state is the sending programme in, what is the single most
important thing to fix, and what will change if it is fixed. Written for someone who will read
this paragraph and nothing else. No jargon — if a term needs the glossary, it does not belong
here. ]

**Overall assessment:** `{{OVERALL_ASSESSMENT}}`

| | Count |
|---|---|
| Critical findings | `{{COUNT_CRITICAL}}` |
| High findings | `{{COUNT_HIGH}}` |
| Medium findings | `{{COUNT_MEDIUM}}` |
| Low findings | `{{COUNT_LOW}}` |

---

## 2. Authentication status

Whether receiving mail servers can verify that mail claiming to be from these domains actually
is. This section comes first because nothing else can be fixed while it is broken — a domain
that fails authentication has no reputation to improve.

| Domain | SPF | DKIM | DMARC | Policy | Aligned |
|---|---|---|---|---|---|
| [ domain ] | [ pass / fail / absent ] | [ pass / fail / absent ] | [ present / absent ] | [ none / quarantine / reject ] | [ yes / no ] |

**Findings**

> **`[severity]` — [ finding title ]**
>
> *Observed:* [ what the check returned, verbatim where useful ]
>
> *Impact:* [ what this costs, in concrete terms ]
>
> *Fix:* [ the specific change, at the specific place ]

**What to check in this section**

- Exactly one SPF record per sending domain. Two is a permanent error that breaks
  authentication for every message.
- SPF stays within the 10 DNS lookup limit. Exceeding it returns permerror, which most
  receivers treat as a failure.
- DKIM key is 2048-bit and signing is active for every sending domain, not just the primary.
- DMARC exists, and its `rua` address is a real mailbox that someone reads.
- DMARC alignment: the `From:` domain matches the domain SPF or DKIM authenticated. Passing SPF
  and DKIM while failing DMARC is an alignment problem and is common when sending through a
  third-party platform.
- Whether a DMARC policy above `p=none` was published without the report history to support it.
  This is a real cause of silent mail loss, including the client's own transactional mail.

---

## 3. Domain and IP reputation

| Check | Result |
|---|---|
| Public blocklist appearances | `{{BLOCKLIST_STATUS}}` |
| Domain age (youngest sending domain) | `{{YOUNGEST_DOMAIN_AGE}}` |
| Primary domain used for cold sending | [ yes / no ] |
| Sending IP type | [ dedicated / shared / provider pool ] |
| Redirect configured on sending domains | [ yes / no / partial ] |

**Findings**

> **`[severity]` — [ finding title ]**
>
> *Observed:*
>
> *Impact:*
>
> *Fix:*

**What to check in this section**

- Any sending domain on a public blocklist, and which one. Different blocklists carry very
  different weight; name the specific list rather than reporting "blocklisted."
- Whether cold email is being sent from `{{PRIMARY_DOMAIN}}`. If it is, that is at minimum a
  high finding, and usually critical: it puts the client's transactional mail, invoices and
  customer correspondence behind the same reputation as their cold outreach.
- Domain age. Domains under 30 days sending at volume explain a great deal on their own.
- Whether sending domains resolve in a browser at all. A sending domain that returns nothing,
  or a certificate warning, is checked by prospects and by filters.

---

## 4. List hygiene

| Metric | Value | Healthy | Assessment |
|---|---|---|---|
| Hard bounce rate | `{{BOUNCE_RATE}}` | under 2% | |
| Spam complaint rate | `{{COMPLAINT_RATE}}` | under 0.1% | |
| Unsubscribe rate | `{{UNSUBSCRIBE_RATE}}` | under 1% | |
| List verified before import | [ yes / no / partial ] | yes | |
| Suppression list enforced at send time | [ yes / no ] | yes | |
| Duplicate contacts across active sequences | `{{DUPLICATE_COUNT}}` | 0 | |
| Role addresses on the list | `{{ROLE_ADDRESS_COUNT}}` | 0 | |
| Records older than `{{DATA_RETENTION_DAYS}}` days | `{{STALE_RECORD_COUNT}}` | 0 | |

**Findings**

> **`[severity]` — [ finding title ]**
>
> *Observed:*
>
> *Impact:*
>
> *Fix:*

**What to check in this section**

- Bounce rate above 5% is a critical finding regardless of anything else in the audit. It
  damages the domain faster than any other single factor and it is entirely preventable.
- Whether the same contact can enter two sequences at once. A prospect receiving two unrelated
  cold sequences from the same company generates complaints at a much higher rate.
- Whether unsubscribes propagate across every channel and every sending domain, or only the one
  that was unsubscribed from. Partial propagation is both a performance problem and a
  compliance one.
- Role addresses (`info@`, `sales@`, `admin@`) — low reply rates, high complaint rates, and a
  common source of spam trap hits.
- Records with no lawful basis recorded for the jurisdiction they are in.

---

## 5. Content and copy risk

| Check | Result |
|---|---|
| Physical postal address present in every message | [ yes / no ] |
| Unsubscribe mechanism present and working | [ yes / no ] |
| `List-Unsubscribe` header present | [ yes / no ] |
| Links in first-touch messages | `{{FIRST_TOUCH_LINK_COUNT}}` |
| Images in cold messages | `{{IMAGE_COUNT}}` |
| Tracking domain | [ dedicated / shared / none ] |
| Unsubstantiated claims present | [ yes / no ] |
| Text-to-HTML ratio | `{{TEXT_HTML_RATIO}}` |

**Findings**

> **`[severity]` — [ finding title ]**
>
> *Observed:*
>
> *Impact:*
>
> *Fix:*

**What to check in this section**

- A missing physical postal address is a CAN-SPAM violation and a CASL violation. This is a
  legal finding, not a stylistic one, and it is always at least high severity.
- A missing or broken unsubscribe mechanism is a violation in all three regimes.
- Links pointing at a shared tracking domain, which are widely blocklisted.
- Claims the client cannot substantiate. These are a legal exposure — under FTC rules in the
  US, under the Consumer Protection from Unfair Trading Regulations in the UK — and they are
  what gets a sender reported rather than ignored.
- Spam-trigger patterns: excessive capitals, multiple exclamation marks, currency amounts in
  subject lines, urgency language, obfuscated words.
- Personalization tokens that render empty or as literal `{{TOKEN}}` text. A message opening
  "Hi ," is the single most visible failure a prospect can see.

---

## 6. Sending patterns

| Metric | Value | Assessment |
|---|---|---|
| Sends per mailbox per day | `{{OBSERVED_DAILY_VOLUME}}` | |
| Mailboxes in rotation | `{{MAILBOX_COUNT}}` | |
| Sending domains in rotation | `{{DOMAIN_COUNT}}` | |
| Send timing | [ evenly distributed / bursts / fixed intervals ] | |
| Weekend sending | [ yes / no ] | |
| Volume ramp on new domains | [ gradual / immediate ] | |
| Warmup traffic maintained at steady state | [ yes / no ] | |

**Findings**

> **`[severity]` — [ finding title ]**
>
> *Observed:*
>
> *Impact:*
>
> *Fix:*

**What to check in this section**

- Volume per mailbox against domain age. New domains at high volume is the most common single
  cause of a failed programme.
- Send timing. Messages leaving at exactly regular intervals, or all at once at the top of the
  hour, is a machine pattern that receivers detect. Human mail is irregular.
- Whether new domains were ramped or switched straight to full volume.
- Whether warmup traffic was switched off after the initial period. It should stay at roughly
  20% of volume permanently; it is the floor under engagement when the cold list underperforms.

---

## 7. Inbox placement

Results from seed testing: sending the client's actual production message to accounts held
across the major mailbox providers and recording where each landed.

| Provider | Inbox | Promotions / other tab | Spam | Not delivered |
|---|---|---|---|---|
| [ consumer provider A ] | | | | |
| [ consumer provider B ] | | | | |
| [ corporate Microsoft 365 ] | | | | |
| [ corporate Google Workspace ] | | | | |
| **Overall** | `{{INBOX_PLACEMENT_RATE}}` | | | |

**Test details**

- Message tested: `{{TESTED_MESSAGE}}`
- Sending domain tested: `{{SENDING_DOMAIN}}`
- Date of test: `{{AUDIT_DATE}}`

**Findings**

> **`[severity]` — [ finding title ]**
>
> *Observed:*
>
> *Impact:*
>
> *Fix:*

**What to check in this section**

- Placement below 90% needs explaining; below 70% is a high or critical finding.
- Whether placement differs sharply between providers. A domain that reaches consumer inboxes
  but not corporate ones points at authentication or a corporate filter appliance; the reverse
  points at content and engagement.
- Whether the seed test used the real production message. A stripped-down test message tells
  you nothing about the copy that is actually sending.

---

## 8. Prioritized remediation

Ordered by severity, then by effort. Each item names an owner and a target date so the client
leaves with a plan rather than a list.

| # | Severity | Finding | Fix | Effort | Owner | Target |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

**Sequencing note**

[ Some fixes must precede others. Authentication is always first: reputation work on a domain
that fails authentication is wasted. List hygiene comes before volume changes. State the
dependencies explicitly here so the client does not start in the middle. ]

**What this does not cover**

[ State the limits of the audit honestly. Common ones: no access to the client's ESP admin
console, so authentication was assessed from public DNS only; no access to historical send
logs, so bounce and complaint rates are as reported by the client rather than observed; seed
testing covers the providers listed and not others. An audit that overstates its own coverage
produces recommendations the client cannot rely on. ]

---

## Appendix A — Raw check output

[ Paste the literal output of each DNS lookup, blocklist check and header inspection. The
client's own technical staff will want to verify the findings, and a finding that cannot be
independently checked is one they have to take on trust. ]

## Appendix B — Glossary

| Term | Meaning |
|---|---|
| SPF | A DNS record naming which servers may send mail for a domain |
| DKIM | A cryptographic signature on each message proving it was not altered and came from an authorised sender |
| DMARC | A DNS record telling receivers what to do with mail that fails SPF and DKIM, and where to send reports |
| Alignment | Whether the domain shown in the `From:` header matches the domain that SPF or DKIM authenticated |
| Seed test | Sending the real message to accounts across the major providers to observe where it lands |
| Warmup | Building a sending history on a new domain by starting at very low volume and ramping gradually |
| Suppression list | The record of addresses that must never be sent to again |
| Spam trap | An address that exists only to catch senders using unverified or purchased lists |
| Hard bounce | Permanent delivery failure, usually because the address does not exist |
| Complaint rate | The proportion of recipients who mark a message as spam |

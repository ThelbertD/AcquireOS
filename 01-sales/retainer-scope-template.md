# Managed Outbound Pipeline — Monthly Agreement

**Between:** `{{AGENCY_LEGAL_ENTITY}}` ("the Provider")
**And:** `{{CLIENT_LEGAL_ENTITY}}` ("the Client")
**Effective:** `{{EFFECTIVE_DATE}}`
**Fee:** `{{CURRENCY}}` `{{RETAINER_PRICE}}` per month
**Term:** Rolling monthly, `{{NOTICE_PERIOD_DAYS}}` days' notice

---

## 1. What this is

Ongoing operation of the Client's outbound sending estate: list building, copy iteration,
sending, monitoring, and reporting.

This assumes an estate already exists and is warmed — either built under an Infrastructure
Sprint or built elsewhere and passed as an audit. It does not include building one.

**What this is not.** The Provider operates the pipeline that puts qualified prospects in front
of the Client. Replying to those prospects, qualifying them, and selling to them is the Client's
work. Section 6 sets that boundary out precisely, because it is the boundary that gets tested.

---

## 2. Included each month

### 2.1 Sending

| | |
|---|---|
| Volume ceiling | `{{SENDING_VOLUME_CEILING}}` messages per month |
| Estate | `{{DOMAIN_COUNT}}` domains, `{{MAILBOX_COUNT}}` mailboxes |
| Per-mailbox daily cap | `{{DAILY_SEND_CEILING}}` |
| Channels | `{{CHANNELS_AVAILABLE}}` |
| Overage | Above the ceiling, `{{CURRENCY}}` `{{OVERAGE_RATE}}`, agreed in writing in advance |

The ceiling is a ceiling, not a target. The Provider sends the volume the list quality and the
Client's reply-handling capacity support, which is frequently less. Volume sent purely to reach
a number damages the estate and produces no pipeline.

### 2.2 List

| | |
|---|---|
| Refresh cadence | `{{LIST_REFRESH_CADENCE}}` |
| New contacts per refresh | Up to `{{LIST_REFRESH_SIZE}}`, meeting the agreed ICP |
| Verification | Every contact verified before import. No exceptions. |
| Enrichment and scoring | Every contact scored; those below `{{ICP_SCORE_THRESHOLD}}` are excluded rather than sent to |
| Suppression | Maintained continuously; unsubscribes and bounces propagate immediately across every domain and channel |
| Hygiene | Records over `{{DATA_RETENTION_DAYS}}` days old are re-enriched or removed |

### 2.3 Copy

| | |
|---|---|
| Iteration cycles included | `{{COPY_ITERATION_CYCLES}}` per month |
| What a cycle is | Rewriting one node, in every lane, and putting the new version live |
| Variant testing | Continuous, within the included cycles |
| Full sequence rewrite | Not included. Priced separately — see section 5. |

A cycle is one node across all lanes, not one message. Changing the opening touch across three
lanes is one cycle, not three.

### 2.4 Operations

Included and unmetered:

- Daily monitoring of bounce rate, complaint rate, reply rate and deferrals
- Monthly seed testing, per sending domain
- Monthly blocklist checks
- Weekly review of DMARC aggregate reports
- Domain and mailbox health monitoring
- Pausing and diagnosing a domain that shows failure signals
- Maintaining the cadence configuration in `{{CRM_NAME}}`
- Suppression list maintenance and cross-channel propagation

### 2.5 Reporting

| | |
|---|---|
| Cadence | `{{REPORTING_CADENCE}}` |
| Format | Written report, plus a monthly call |
| Contents | Volume sent by domain and lane; delivery, bounce, complaint and unsubscribe rates; reply rate by node and by lane; interrupts fired; terminal state distribution; list additions and exclusions; estate health; what changed and what is changing next |

Every report states what was tested, what the result was, and what will be done differently.
A report that only lists numbers is not a report.

---

## 3. Client responsibilities

The pipeline stops working without these. They are obligations, not preferences.

| # | What | Why |
|---|---|---|
| 1 | **Reply to prospects within one working day.** | The single largest determinant of results. A prospect who replies and waits three days has gone. Unanswered replies also generate complaints, which damage the estate for everyone on it. |
| 2 | A named person owning replies, with cover for absence | Replies do not pause for holidays |
| 3 | Approve copy within 2 working days of delivery | An iteration cycle not approved is a cycle not used, and it does not roll over |
| 4 | Keep proof points current, and confirm each can be evidenced | Claims that cannot be evidenced are a legal exposure for the Client |
| 5 | Notify the Provider of any change to the offer, pricing, ICP or positioning | Copy written against a stale offer wastes a cycle and misleads prospects |
| 6 | Maintain the accounts in section 8 and keep them paid | An expired domain takes every sequence running through it down with it |
| 7 | Confirm the lawful basis for every jurisdiction the list touches, and keep it current | Only the Client can make this determination |
| 8 | Forward any regulator or data subject correspondence within 2 working days | Statutory response windows are short |

**On item 1.** If reply handling falls below one working day for two consecutive weeks, the
Provider will raise it in writing and reduce sending volume until it recovers. Continuing to
generate replies nobody answers converts a working pipeline into a complaint problem, and the
complaint problem outlasts the engagement.

---

## 4. Reviewing performance

Assessed monthly on:

| Metric | Owned by | Target |
|---|---|---|
| Delivery rate | Provider | above 97% |
| Hard bounce rate | Provider | under 2% |
| Complaint rate | Provider | under 0.1% |
| Inbox placement (seed test) | Provider | above 90% |
| Reply rate | Shared | Agreed at the first review, against the first 60 days of data |
| Positive reply rate | Shared | Agreed at the first review |
| Meetings booked | Client | Client's own target |
| Pipeline and revenue | Client | Client's own target |

**Why targets are set after 60 days rather than in advance.** A reply rate target set before any
data exists is a number invented to win a signature. The first 60 days establish the baseline
against which improvement can be measured, and the targets set at that review are meaningful.

**Where a Provider metric misses target** for two consecutive months, the Provider produces a
written diagnosis and remediation plan at no charge, and the Client may terminate on 14 days'
notice regardless of the notice period in section 9.

---

## 5. Scope changes

The following require a written change order and a fee adjustment before work begins. They are
listed so nobody has to guess where the line is.

| Change | Effect |
|---|---|
| Volume above `{{SENDING_VOLUME_CEILING}}` | Overage at `{{CURRENCY}}` `{{OVERAGE_RATE}}`, or a revised ceiling |
| Additional sending domains or mailboxes | Priced as a partial sprint; includes 3–4 weeks of warmup before the capacity is usable |
| Additional segment lanes | Each lane adds a full set of copy per node, and the same again per iteration cycle |
| Additional channels beyond `{{CHANNELS_AVAILABLE}}` | Priced separately; SMS additionally requires a consent basis the Client can evidence |
| A new ICP, or entry into a new market | A new list, new scoring, and new copy. Effectively a new pipeline. |
| Full sequence rewrite | Beyond the included iteration cycles |
| Copy iterations beyond `{{COPY_ITERATION_CYCLES}}` | Per additional cycle |
| A new offer or repositioning | New brain file, new copy, new proof points |
| Migration to a different CRM or sending platform | Rebuild of the cadence |
| Reporting beyond `{{REPORTING_CADENCE}}`, or custom reporting | Priced on the requirement |
| Integration with the Client's other systems | Out of scope; priced separately |
| Any request that changes the deliverables in section 2 | By definition a scope change |

**What is not a scope change.** Diagnosing and fixing a deliverability problem, replacing a
burned domain that failed under the Provider's operation, adjusting timing or sending patterns,
re-verifying the list, and reallocating volume across the estate are all included work.

---

## 6. Explicitly excluded

- Replying to prospects, in any form
- Qualifying, nurturing or selling to prospects
- Booking or attending meetings
- Building the initial estate — that is the Infrastructure Sprint
- Warmup of new domains beyond monitoring — the time is the time
- Inbound marketing, content, paid advertising, SEO, social
- CRM work beyond the outbound cadence
- Sales training, call coaching, or proposal writing
- Legal advice of any kind
- Determining the Client's lawful basis for contacting anyone
- Responding to data subject requests or regulator correspondence on the Client's behalf
- Any guarantee of inbox placement, reply rate, meetings, or revenue

---

## 7. Payment

| | |
|---|---|
| Fee | `{{CURRENCY}}` `{{RETAINER_PRICE}}` per month |
| Billing | Monthly in advance, on the same date each month |
| Terms | Net `{{PAYMENT_TERMS_DAYS}}` days |
| First month | Due before work begins |
| Overage | Invoiced in arrears, only where agreed in writing in advance |
| Late payment | Statutory interest. Sending pauses if an invoice is more than 14 days overdue; the estate continues to be monitored. |
| Annual review | Fee reviewed once a year, with 60 days' notice of any change |

**Pass-through costs**, paid directly by the Client on the Client's own accounts: domain
renewals, `{{ESP_NAME}}` licences, `{{CRM_NAME}}` subscription, sending platform, warmup
network, email verification credits, `{{ENRICHMENT_PROVIDER}}` credits. The Provider does not
mark these up and does not hold them.

---

## 8. Accounts and access

Every account is in the Client's name, paid by the Client. The Provider holds delegated access.

| Account | Held by | Provider access |
|---|---|---|
| Domain registrar | Client | Delegated |
| DNS host | Client | Delegated, write |
| `{{ESP_NAME}}` | Client | Delegated admin |
| `{{CRM_NAME}}` | Client | Delegated |
| Sending platform | Client | Delegated |
| Warmup network | Client | Delegated |
| Email verification | Client | Delegated |
| `{{ENRICHMENT_PROVIDER}}` | Client | Delegated |
| Database | Client | Delegated |

This is deliberate. It means termination requires revoking access and nothing else, and it means
the Client is never in a position where leaving is expensive.

---

## 9. Term and termination

| | |
|---|---|
| Term | Rolling monthly |
| Notice | `{{NOTICE_PERIOD_DAYS}}` days, in writing, either party |
| Minimum commitment | None after the first month |
| Effect of notice | Service continues to the end of the notice period. Sending is wound down over the final two weeks rather than stopped, so contacts mid-cadence are not abandoned. |

**Immediate termination.** Either party may terminate immediately if the other materially
breaches and does not remedy it within 14 days of written notice. The Provider may additionally
suspend sending immediately, without notice, if instructed to send to contacts with no lawful
basis, to send content the Client cannot substantiate, or to continue at volume where reply
handling has broken down.

### At termination

| Asset | Outcome |
|---|---|
| Sending domains | Client's. Already in the Client's name. |
| Mailboxes and contents | Client's. Already in the Client's name. |
| Prospect data, including enrichment | Client's. Exported in full, in CSV and as a Postgres dump, within 5 working days. |
| Suppression list | Client's. Exported in the same window. **Must be carried into any future sending.** |
| Copy written for the Client | Client's, for all fees paid |
| Cadence configuration in the CRM | Client's. Remains in place. |
| Reports and the seed test history | Client's. Exported. |
| The Provider's templates, scripts and methodology | Provider's |

The Provider deletes its own copies of Client data within 30 days of the export and confirms in
writing. Nothing is withheld pending payment; unpaid fees are pursued as a debt, never by
holding a client's data.

**On the suppression list.** Every person who unsubscribed remains unsubscribed. Carrying the
list forward is a legal obligation on the Client under all three regimes, not a courtesy, and
sending to those contacts again after termination is a breach by the Client.

---

## 10. Data protection

- The Client is the controller. The Provider is a processor, acting on documented instructions.
- The Provider processes prospect data only to deliver this agreement, and for no other client
  or purpose.
- Sub-processors — the sending platform, verification service, enrichment provider — are listed
  in the estate register. The Client is notified 30 days before any change.
- Personal data is retained for `{{DATA_RETENTION_DAYS}}` days from last contact, then deleted.
- Data subject requests are forwarded to `{{DPO_CONTACT}}` within 2 working days.
- Where UK or EU data subjects are processed, a separate data processing agreement applies and
  forms part of this agreement.
- Where UK or EU contacts are processed on the basis of legitimate interest, the Client
  maintains the assessment at `{{LIA_REFERENCE}}` and reviews it annually.

---

## 11. Signatures

**For `{{CLIENT_LEGAL_ENTITY}}`**

Name: ____________________  Title: ____________________

Signature: ____________________  Date: ____________

**For `{{AGENCY_LEGAL_ENTITY}}`**

Name: ____________________  Title: ____________________

Signature: ____________________  Date: ____________

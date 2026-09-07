# Client Intake Form

Everything needed before the build starts. Sections marked **REQUIRED** block the build;
everything else improves it.

Each field notes which artifact consumes it, so it is clear why it is being asked and what
happens if it is missing.

**Client:** ____________________
**Completed by:** ____________________
**Date:** ____________________

> This form has a machine-readable twin. `06-onboarding/intake_to_spec.py` reads the same
> fields as JSON — see `sample-intake.json` — and emits the build specification plus a list of
> anything missing or ambiguous that blocks the build. Fill this form, transcribe to JSON, run
> the script, and resolve what it flags before day 1.

---

## Section 1 — Company

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 1.1 | Trading name | **Required** | | Every artifact. `{{CLIENT_NAME}}` |
| 1.2 | Legal entity name and company number | **Required** | | `01-sales/`. `{{CLIENT_LEGAL_ENTITY}}` |
| 1.3 | Physical postal address | **Required** | | Every message signature. `{{CLIENT_POSTAL_ADDRESS}}` |
| 1.4 | Primary domain | **Required** | | `02-infrastructure/`. `{{PRIMARY_DOMAIN}}` |
| 1.5 | Privacy policy URL | **Required** | | `05-copy/`. `{{PRIVACY_POLICY_URL}}` |
| 1.6 | Data protection contact | Required if UK/EU in scope | | `05-copy/`, `01-sales/`. `{{DPO_CONTACT}}` |
| 1.7 | Decision-maker name and email | **Required** | | `01-sales/`. `{{CLIENT_CONTACT_NAME}}`, `{{CLIENT_CONTACT_EMAIL}}` |
| 1.8 | Who owns replies day to day | **Required** | | `04-cadence/` interrupt branch |
| 1.9 | Reply cover during absence | **Required** | | Interrupt branch |

> **1.3 is not administrative.** A physical postal address in every commercial message is
> required under CAN-SPAM and CASL. A PO box is acceptable in the US; a virtual office with no
> real presence is not.

---

## Section 2 — Offer

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 2.1 | What you sell, in one sentence, in your buyer's words | **Required** | | `05-copy/`. `{{OFFER_DESCRIPTION}}` |
| 2.2 | The problem it removes | **Required** | | `05-copy/`. `{{PROBLEM_STATEMENT}}` |
| 2.3 | What changes for the buyer | **Required** | | `05-copy/` |
| 2.4 | Time from signing to that change | Optional | | `05-copy/` |
| 2.5 | Price shape (per seat, per site, retainer, usage) | Optional | | `05-copy/` |
| 2.6 | Typical deal size | Optional | | `01-sales/pricing-model.md`, viability check |
| 2.7 | Typical sales cycle length | Optional | | Cadence timing, reporting expectations |

---

## Section 3 — ICP

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 3.1 | ICP in one paragraph: who, what size, what role, in what situation | **Required** | | `05-copy/`, `07-data/enrichment-spec.md`. `{{ICP_DESCRIPTION}}` |
| 3.2 | Job titles, exactly as they appear on profiles | **Required** | | List building, scoring |
| 3.3 | Company size band | **Required** | | Scoring |
| 3.4 | Geography | **Required** | | Determines `{{JURISDICTIONS}}` |
| 3.5 | Industry or sector, if it matters | Optional | | Scoring |
| 3.6 | Who this is explicitly **not** for | **Required** | | Scoring exclusions, `05-copy/` |
| 3.7 | Technology or tooling that signals fit | Optional | | Enrichment fields |
| 3.8 | A trigger event that makes this the right week to contact them | Optional, high value | | `05-copy/`, scoring |
| 3.9 | Accounts never to contact (existing customers, partners, competitors) | **Required** | | Suppression list, before first send |

> **3.9 is required and is frequently returned empty.** An existing customer receiving a cold
> pitch for something they already pay for is the most damaging single message the pipeline can
> send. Get the list, load it into suppression before day 1.

---

## Section 4 — Segmentation

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 4.1 | Which field routes contacts into lanes | **Required** | | `04-cadence/`. `{{SEGMENT_FIELD}}` |
| 4.2 | The lane names | **Required** | | `04-cadence/`. `{{SEGMENT_LANES}}` |
| 4.3 | Which lane catches unknown or unmapped values | **Required** | | Router default lane |
| 4.4 | What is different about each lane's messaging | **Required** | | `05-copy/variant_prompt.md` |
| 4.5 | Approximate share of the list per lane | Optional | | Volume planning, test design |

> **4.3 without an explicit answer means contacts vanish silently at the router.** It is the
> most common cadence bug and the hardest to notice, because nothing errors.

---

## Section 5 — Proof

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 5.1 | Proof point 1: claim and its evidence | **Required** | | `05-copy/`. `{{PROOF_POINT_1}}` |
| 5.2 | Proof point 2 | Optional | | `{{PROOF_POINT_2}}` |
| 5.3 | Proof point 3 | Optional | | `{{PROOF_POINT_3}}` |
| 5.4 | Customers who may be named, with written permission | Optional | | `05-copy/` |
| 5.5 | Confirmation that every claim above can be evidenced on request | **Required** | | Legal exposure gate |

> **At least one substantiable proof point is required.** Copy without proof becomes copy with
> invented proof. Unsubstantiated claims are actionable under the FTC Act in the US and the
> Consumer Protection from Unfair Trading Regulations in the UK, and they are what turns an
> ignored message into a reported one.

---

## Section 6 — Objections

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 6.1 | Objection 1, in the buyer's words, and your real answer | **Required** | | `05-copy/`. `{{OBJECTION_1}}` / `{{REBUTTAL_1}}` |
| 6.2 | Objection 2 and answer | **Required** | | `{{OBJECTION_2}}` / `{{REBUTTAL_2}}` |
| 6.3 | Objection 3 and answer | **Required** | | `{{OBJECTION_3}}` / `{{REBUTTAL_3}}` |
| 6.4 | Which is most common | **Required** | | Gets its own cadence node |
| 6.5 | Why deals are actually lost | Optional | | `05-copy/` |

---

## Section 7 — Voice

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 7.1 | Tone: formal to casual, softened to blunt, plain to technical | **Required** | | `05-copy/`. `{{TONE_CONSTRAINTS}}` |
| 7.2 | Words you use for your category, product and customers | Optional | | `05-copy/` |
| 7.3 | Words and claims never to use | **Required** | | `05-copy/`. `{{FORBIDDEN_WORDS}}` |
| 7.4 | Competitors never to mention | **Required** | | `05-copy/`. `{{COMPETITOR_EXCLUSION_LIST}}` |
| 7.5 | Disclaimers your counsel requires in every message | **Required** (write "none") | | `05-copy/`. `{{REQUIRED_DISCLAIMER}}` |
| 7.6 | Two or three samples of your own writing | Optional, high value | | `05-copy/` voice calibration |

> **7.5 must be answered even when the answer is "none".** A blank is indistinguishable from an
> unanswered question, and the difference matters for regulated clients.

---

## Section 8 — The ask

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 8.1 | The single action the cadence asks for | **Required** | | `05-copy/`. `{{PRIMARY_CTA}}` |
| 8.2 | What a prospect can supply that means they are engaged | **Required** | | `04-cadence/` interrupt trigger. `{{REQUIRED_INPUT}}` |
| 8.3 | What you do with it, and how fast | **Required** | | Follow-through branch |
| 8.4 | Lower-friction fallback ask | Optional | | `05-copy/` |
| 8.5 | Booking link, if a call is the ask | Optional | | Cadence, from node 2 onward |

---

## Section 9 — Sender

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 9.1 | Name messages are sent from | **Required** | | `02-infrastructure/`, `05-copy/`. `{{SENDER_PERSONA_NAME}}` |
| 9.2 | Their title | **Required** | | `05-copy/`. `{{SENDER_PERSONA_TITLE}}` |
| 9.3 | Is this a real person at your company who has agreed? | **Required** | | Compliance gate |
| 9.4 | Will they see the replies? | **Required** | | Interrupt branch |
| 9.5 | Additional sender personas, if the estate needs several | Optional | | Mailbox allocation |

> **9.3 must be yes.** A prospect who searches the sender and finds nothing is lost; one who
> finds a fabricated persona complains. Misleading sender identification is a specific CAN-SPAM
> violation.

---

## Section 10 — Volume and infrastructure

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 10.1 | Target sends per month | **Required** | | `02-infrastructure/domain_plan.py`. `{{TARGET_MONTHLY_SENDS}}` |
| 10.2 | Email service provider | **Required** | | `02-infrastructure/`. `{{ESP_NAME}}` |
| 10.3 | Where DNS is hosted | **Required** | | `02-infrastructure/` |
| 10.4 | Domain registrar | **Required** | | `02-infrastructure/` |
| 10.5 | CRM or automation platform | **Required** | | `04-cadence/`. `{{CRM_NAME}}` |
| 10.6 | Sending platform | Optional | | `{{SENDING_PLATFORM}}` |
| 10.7 | Any existing sending domains | Optional | | Audit scope |
| 10.8 | Has cold email been sent from any of them before? | **Required** | | Reputation risk assessment |
| 10.9 | Any known blocklist or deliverability history | **Required** | | Audit scope |
| 10.10 | Channels in scope | **Required** | | `04-cadence/`. `{{CHANNELS_AVAILABLE}}` |

> **10.8 and 10.9 change the build.** A domain with prior cold sending history carries that
> history whether or not anyone remembers it. If either answer is yes, run a
> `03-audit/` audit before building anything on top.

---

## Section 11 — Reply capacity

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 11.1 | How many replies per week can you answer within one working day? | **Required** | | Volume viability check |
| 11.2 | Who answers them | **Required** | | Interrupt branch |
| 11.3 | Escalation path for technical or pricing questions | **Required** | | Follow-through branch |
| 11.4 | Coverage during holidays and absence | **Required** | | Interrupt branch |

> **11.1 constrains 10.1 and frequently reduces it.** Expect roughly 3% of sends to produce a
> reply. If the volume target implies more replies than the client can answer, the target is
> wrong: unanswered replies burn the list permanently and generate complaints. This check is
> step 1.2 of the infrastructure runbook and it is not optional.

---

## Section 12 — Compliance

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 12.1 | Every country your list touches | **Required** | | `{{JURISDICTIONS}}` |
| 12.2 | US contacts on the list? | **Required** | | CAN-SPAM: opt-out model |
| 12.3 | UK or EU contacts? | **Required** | | GDPR + PECR |
| 12.4 | If yes to 12.3: is a Legitimate Interest Assessment complete and on file? | **Required** | | `{{LIA_REFERENCE}}` |
| 12.5 | If yes to 12.3: are any contacts personal addresses, sole traders or partnerships? | **Required** | | PECR treats these as individuals — consent required |
| 12.6 | Canadian contacts? | **Required** | | CASL |
| 12.7 | If yes to 12.6: express or implied consent, recorded per contact, with expiry? | **Required** | | Blocks Canadian contacts if absent |
| 12.8 | Has your counsel signed off on cold outbound to these jurisdictions? | **Required** | | Build gate |
| 12.9 | Unsubscribe endpoint URL | **Required** | | `{{UNSUBSCRIBE_URL}}` |
| 12.10 | Data retention period in days | **Required** | | `{{DATA_RETENTION_DAYS}}` |
| 12.11 | If SMS is in scope: consent basis and source for every number | Required if SMS | | Blocks SMS if absent |

> **12.7 cannot be answered retroactively.** CASL requires a lawful basis *before* the first
> message, unlike CAN-SPAM's opt-out model. If the client cannot say which basis applies to
> their Canadian contacts, those contacts are excluded from the build. This is not a step to
> work around.

---

## Section 13 — Existing list

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 13.1 | Do you have a list? | **Required** | | `07-data/` |
| 13.2 | How many contacts | Required if 13.1 is yes | | Volume planning |
| 13.3 | Where it came from | **Required** if 13.1 is yes | | Lawful basis, quality assessment |
| 13.4 | Has it been verified, and when? | **Required** if 13.1 is yes | | Bounce risk |
| 13.5 | Has any of it been emailed before? | **Required** if 13.1 is yes | | Suppression, fatigue |
| 13.6 | Existing suppression or unsubscribe list | **Required** | | Loaded before day 1 |
| 13.7 | Existing customers, to suppress | **Required** | | Loaded before day 1 |
| 13.8 | Format and column headers | Required if 13.1 is yes | | `07-data/list_pipeline.py` mapping |

> **13.6 and 13.7 are loaded into suppression before a single message sends.** An existing
> customer or a previous unsubscribe receiving a cold pitch is the worst message the pipeline
> can produce, and both are entirely preventable.

---

## Section 14 — Commercial

| # | Field | Required | Value | Consumed by |
|---|---|---|---|---|
| 14.1 | Which engagement: sprint, retainer, audit, or sprint plus retainer | **Required** | | `01-sales/` |
| 14.2 | Target start date | **Required** | | Timeline |
| 14.3 | Reporting cadence expected | **Required** | | `{{REPORTING_CADENCE}}`, pricing driver D6 |
| 14.4 | Budget range, if it can be shared | Optional | | Scoping |
| 14.5 | Who signs | **Required** | | `01-sales/` |
| 14.6 | Procurement, security review or legal review required? | **Required** | | Timeline. Frequently the longest single delay. |

---

## Completeness check

- [ ] Every **Required** field has an answer, including the ones answered "none"
- [ ] Section 5 has at least one substantiable proof point, and 5.5 is confirmed
- [ ] Section 6 has three real objections with real answers
- [ ] Section 9.3 is yes
- [ ] Section 11.1 is consistent with section 10.1 at a 3% reply rate
- [ ] Section 12 has a lawful basis for every jurisdiction in 12.1
- [ ] Sections 13.6 and 13.7 have been supplied as files, not promised
- [ ] Transcribed to JSON and run through `intake_to_spec.py` with no blockers remaining

**Outstanding blockers:**

| Section | What is missing | Who owns it | Needed by |
|---|---|---|---|
| | | | |

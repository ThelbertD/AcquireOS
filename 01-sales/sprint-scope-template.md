# Statement of Work — Outbound Infrastructure Sprint

**Between:** `{{AGENCY_LEGAL_ENTITY}}` ("the Provider")
**And:** `{{CLIENT_LEGAL_ENTITY}}` ("the Client")
**Effective:** `{{EFFECTIVE_DATE}}`
**Fee:** `{{CURRENCY}}` `{{SPRINT_PRICE}}`, fixed
**Duration:** 7 working days from kickoff

---

## 1. What this is

A fixed-scope, fixed-price build that takes the Client from no cold outbound capability to a
sending estate that is authenticated, monitored, warming, and connected to a live multi-touch
sequence.

This is a build, not a campaign. At the end of seven days the estate exists and is correct. It
is not yet sending at volume, because the domains are still warming — that takes three to four
weeks and cannot be compressed by paying more. Section 4 sets out what "done" means precisely.

---

## 2. Deliverables

Each item below is delivered or it is not. There is no partial credit and no interpretation
required.

### 2.1 Sending estate

- `{{DOMAIN_COUNT}}` secondary sending domains, registered in the Client's name, each
  redirecting to `{{PRIMARY_DOMAIN}}` over HTTPS with a valid certificate
- `{{MAILBOX_COUNT}}` mailboxes provisioned on `{{ESP_NAME}}`, `{{MAILBOXES_PER_DOMAIN}}` per
  domain, each with display name, profile photo and a signature containing
  `{{CLIENT_POSTAL_ADDRESS}}`
- A written estate register: every domain, every mailbox, where DNS is hosted, where DMARC
  reports go, and every renewal date

### 2.2 Authentication

For every sending domain:

- SPF, published as exactly one record, within the 10-lookup limit
- DKIM, 2048-bit, published and signing active
- DMARC at `p=none` with a working `rua` address, and that mailbox created
- MX records, verified as able to receive
- A dedicated tracking CNAME, where tracking is in use
- Evidence of `spf=pass`, `dkim=pass` and `dmarc=pass` in the raw headers of a test message
  from each domain

### 2.3 Warmup

- Every mailbox enrolled in a warmup network at the correct starting volume
- The week-by-week warmup schedule, with the volume ramps and the signals to watch
- Two seed tests during the sprint, with results recorded per provider
- A written clearance standard: the specific conditions under which a domain moves to full
  production volume

### 2.4 Data pipeline

- A Postgres database with the prospect schema deployed: raw imports, normalised contacts,
  enrichment, suppression, send events, reply events
- A CSV ingestion pipeline that normalises, deduplicates, validates syntax and checks the
  suppression list, logging every rejected row with its reason
- One list of up to `{{INITIAL_LIST_SIZE}}` contacts ingested, verified and loaded

### 2.5 Cadence

- A multi-touch sequence of `{{CADENCE_LENGTH_DAYS}}` days across `{{CHANNELS_AVAILABLE}}`,
  built in `{{CRM_NAME}}`
- Segment routing into `{{SEGMENT_LANES}}`, with a default lane for unmapped values
- An interrupt branch that cancels the remaining sequence when a prospect replies or supplies
  `{{REQUIRED_INPUT}}`, and a follow-through branch
- Four terminal states with defined handling: replied, bounced, unsubscribed,
  completed-no-response
- Unsubscribe propagation across every sending domain and every channel
- Tested end to end with seed contacts before any real contact is enrolled

### 2.6 Copy

- A completed brain file capturing the Client's ICP, offer, proof points, objections and voice
- Copy for every node in every lane, within the length limits, with personalisation fallbacks
  that render correctly when a field is empty
- Every claim traced to a proof point the Client has confirmed can be evidenced

### 2.7 Handover

- A recorded walkthrough of the estate and the cadence
- The estate register, the warmup schedule, and the clearance standard, in writing
- Written confirmation that the Client owns every domain, every mailbox and all data

---

## 3. Timeline

Seven working days. Days are sequential from kickoff, which is the first working day after this
document is signed and section 5 is complete.

| Day | Provider does | Client does |
|---|---|---|
| **1** | Kickoff call. Complete the intake. Produce the domain plan and the build specification. Identify blockers. | Attend kickoff. Answer the intake. Confirm the volume target. |
| **2** | Register domains. Configure redirects. Add domains to the ESP and verify. Generate the DNS record set. | Provide registrar and DNS access. Provide ESP admin access. |
| **3** | Publish MX, SPF, DMARC. Create the DMARC reporting mailbox. Generate and publish DKIM. Verify authentication end to end on every domain. | Approve the sender personas. |
| **4** | Provision and configure every mailbox. Set per-mailbox sending limits. Verify inbound. Begin warmup. | Confirm signature details and postal address. |
| **5** | Deploy the database schema. Ingest, verify and load the list. Build the cadence structure in the CRM. | Supply the prospect list. Complete the brain file. |
| **6** | Write the copy. Load it into the CRM. Test end to end with seed contacts in every lane. | Review and approve the copy. |
| **7** | First seed test. Fix anything it surfaces. Handover walkthrough. Deliver the estate register. | Attend handover. |

**Warmup continues past day 7.** Domains reach production volume three to four weeks after day
4, subject to the clearance standard. This is a property of how mailbox providers assess new
domains, not a service level, and no fee accelerates it.

### If the Client is late

Each of the Client responsibilities in section 5 has a day it is needed by. If one arrives late,
the sprint extends by the number of working days it was late, and the fee does not change. The
Provider will state in writing on the day it happens which deliverable is blocked and by what.

---

## 4. Acceptance criteria

The sprint is complete when all of the following are demonstrably true. Each is objectively
checkable and the Provider will demonstrate each one at handover.

| # | Criterion | How it is verified |
|---|---|---|
| 1 | Every sending domain resolves and redirects to `{{PRIMARY_DOMAIN}}` over HTTPS without a certificate warning | Browser check, each domain |
| 2 | Every sending domain has exactly one SPF record, within the 10-lookup limit | `dig` output, each domain |
| 3 | Every sending domain has a published 2048-bit DKIM key with signing active | `dig` output plus ESP console, each domain |
| 4 | Every sending domain has a DMARC record at `p=none` with a `rua` address that receives mail | `dig` output plus a delivered test report |
| 5 | A test message from each domain shows `spf=pass`, `dkim=pass`, `dmarc=pass` | Raw headers, each domain |
| 6 | Every mailbox sends and receives, with the correct display name, photo and signature including the postal address | Test message from and to each mailbox |
| 7 | Every mailbox is enrolled in warmup and sending at the scheduled volume | Warmup platform dashboard |
| 8 | The database schema is deployed and the list is loaded | Row counts, plus the rejection log |
| 9 | Every rejected row from ingestion has a recorded reason | Rejection log |
| 10 | The cadence is built, with segment routing, the interrupt branch, and all four terminal states | Walkthrough in the CRM |
| 11 | A seed contact in each lane routes correctly, receives each node on the correct day, and exits correctly on reply | Test run, recorded |
| 12 | An unsubscribe from one domain propagates to every domain and every channel | Test run, recorded |
| 13 | Every message contains the postal address and a working unsubscribe link | Inspection of each node |
| 14 | Every claim in the copy traces to a proof point the Client has confirmed | The brain file, signed |
| 15 | The estate register is delivered and the Client holds all credentials | The document, plus a Client-side login check |

**Acceptance.** The Client has 5 working days from handover to test these criteria and raise any
that fail. The Provider fixes anything that fails at no charge. If nothing is raised within 5
working days, the sprint is accepted.

**Acceptance is not conditional on results.** These criteria test whether the estate was built
correctly. Reply rates, meetings booked and pipeline generated depend on the Client's offer,
their market and their list, and are addressed by the retainer in a separate agreement.

---

## 5. Client responsibilities

The Provider cannot deliver without these. Each is listed with the day it is needed.

| # | What | Needed by | If it is late |
|---|---|---|---|
| 1 | A named decision-maker (`{{CLIENT_CONTACT_NAME}}`) available for the kickoff and for approvals within one working day | Day 1 | Everything slips |
| 2 | Registrar access, or authority for the Provider to register domains in the Client's name | Day 2 | Days 2–7 slip |
| 3 | DNS write access for the sending domains | Day 2 | Days 3–7 slip |
| 4 | `{{ESP_NAME}}` admin access sufficient to add domains, provision users and generate DKIM keys | Day 2 | Days 3–7 slip |
| 5 | `{{CRM_NAME}}` access sufficient to build sequences and create fields | Day 5 | Days 5–7 slip |
| 6 | Approval of the sender personas, each a real person who has agreed to be used | Day 3 | Day 4 slips |
| 7 | `{{CLIENT_POSTAL_ADDRESS}}` — a valid physical postal address | Day 4 | Day 4 slips |
| 8 | A prospect list, or a written specification of the ICP for the Provider to build one | Day 5 | Days 5–7 slip |
| 9 | A completed brain file: ICP, offer, proof points, objections, voice, forbidden words | Day 5 | Days 6–7 slip |
| 10 | Written confirmation that every proof point can be evidenced on request | Day 5 | Copy cannot be written |
| 11 | Copy approval within one working day of delivery | Day 6 | Day 7 slips |
| 12 | Confirmation of every jurisdiction the list touches (`{{JURISDICTIONS}}`), and the lawful basis for each | Day 1 | Build cannot start |
| 13 | Where any UK or EU contact is on the list, a completed Legitimate Interest Assessment | Day 1 | UK/EU contacts are excluded |
| 14 | Where any Canadian contact is on the list, the consent basis recorded per contact | Day 1 | Canadian contacts are excluded |

**On items 12 to 14.** The Provider builds compliant infrastructure. Whether the Client has a
lawful basis to contact a given person is a determination only the Client and their counsel can
make, and it cannot be made retroactively — CASL in particular requires the basis to exist
before the first message. Contacts without a recorded basis are excluded from the build.

---

## 6. Explicitly excluded

These are not in scope for this fee. Each is available separately.

**Not included in the sprint:**

- Sending at production volume. The estate warms for three to four weeks after day 4.
- Ongoing list building beyond the initial load
- Ongoing copy iteration beyond the initial set
- Replying to prospects, booking meetings, or any sales activity
- Managing the pipeline after handover
- Reporting beyond the handover walkthrough
- CRM configuration beyond the cadence itself
- Integration with the Client's other systems
- Any inbound marketing, content, paid advertising, or social activity
- Website changes, other than the redirects on the sending domains
- Legal advice of any kind
- Determining the Client's lawful basis for contacting anyone
- Data subject access requests, erasure requests, or regulator correspondence
- Recovery of a domain or IP the Client burned before this engagement
- Any guarantee of inbox placement, reply rate, meetings booked, or revenue

**On the last item.** Inbox placement depends on the Client's offer, their list, their reply
handling, and decisions made by mailbox providers that nobody outside them can see. The Provider
delivers a correctly built estate and a documented warmup process. No supplier who claims to
guarantee placement can control it.

---

## 7. Payment

| | |
|---|---|
| Fee | `{{CURRENCY}}` `{{SPRINT_PRICE}}`, fixed |
| 50% on signature | Due before kickoff. Work does not begin until it clears. |
| 50% on handover | Invoiced on the day of the handover walkthrough |
| Terms | Net `{{PAYMENT_TERMS_DAYS}}` days |
| Late payment | Statutory interest, and work pauses until the account is current |
| Expenses | Domain registration and third-party tooling are passed through at cost and invoiced separately. Estimated at `{{CURRENCY}}` `{{PASSTHROUGH_ESTIMATE}}`. |

**Not included in the fee, and paid directly by the Client:** domain registration, `{{ESP_NAME}}`
mailbox licences, `{{CRM_NAME}}` subscription, sending platform subscription, warmup network
subscription, email verification credits, and any enrichment provider. These are the Client's
accounts in the Client's name, which is how the Client keeps ownership of the estate.

---

## 8. Ownership

| Asset | Owner |
|---|---|
| Sending domains | Client |
| Mailboxes and their contents | Client |
| Prospect data, including all enrichment | Client |
| Suppression list | Client |
| Copy written for the Client | Client, on final payment |
| The database and its contents | Client |
| The Provider's templates, scripts, schemas and methodology | Provider |

The Provider's underlying system — the scripts, schemas, checklists and templates used to
produce the deliverables — remains the Provider's, and the Client receives a perpetual licence
to use the outputs produced with them for their own business.

Every account is created in the Client's name from the outset. There is no transfer step and no
point at which the Client depends on the Provider's access.

---

## 9. Confidentiality and data protection

- Each party keeps the other's confidential information confidential, during and after the
  engagement.
- The Client is the data controller for all prospect data. The Provider is a processor, acting
  on the Client's documented instructions.
- The Provider processes prospect data only to deliver this Statement of Work.
- The Provider will not use the Client's prospect data for any other client or purpose.
- On termination, the Provider deletes its copies of the Client's prospect data within 30 days
  and confirms in writing.
- Where the parties process personal data of UK or EU data subjects, a separate data processing
  agreement applies and forms part of this engagement.

---

## 10. Termination

Either party may terminate before completion on written notice.

| Terminated by | Fee outcome |
|---|---|
| Client, before kickoff | Deposit refunded in full |
| Client, during days 1–3 | Deposit retained; nothing further due |
| Client, during days 4–7 | Deposit retained; balance due pro rata against the deliverables completed |
| Provider, for non-payment | Balance due for work completed |
| Provider, for any other reason | Deposit refunded; no further fee due |

On termination the Client keeps everything already delivered: domains, mailboxes, DNS records,
data, and any copy already paid for. Nothing is withheld.

---

## 11. Signatures

By signing, both parties agree to the scope, timeline, acceptance criteria and payment terms set
out above. This document is the whole agreement for this sprint and supersedes anything
discussed before it.

**For `{{CLIENT_LEGAL_ENTITY}}`**

Name: ____________________  Title: ____________________

Signature: ____________________  Date: ____________

**For `{{AGENCY_LEGAL_ENTITY}}`**

Name: ____________________  Title: ____________________

Signature: ____________________  Date: ____________

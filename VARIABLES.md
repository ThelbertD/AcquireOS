# Variables

Every client-specific value used anywhere in this repository. Nothing outside this list should
appear as a `{{PLACEHOLDER}}` in any artifact — if you add one, register it here.

**Format.** `{{UPPER_SNAKE_CASE}}`, double braces, no spaces inside the braces.

**Example values** below are illustrative and fictional. Domains use the IANA reserved
`example.com` / `example.org` / `example.net` names, which belong to nobody.

A filled artifact is ready to deliver when this returns nothing:

```bash
grep -rno '{{[A-Z0-9_]*}}' path/to/filled/document
```

Some variables are numbered when an artifact needs several instances of the same kind of value
— `{{PROOF_POINT_1}}`, `{{PROOF_POINT_2}}`, `{{OBJECTION_1}}`, and so on. The numbered forms
are registered below by their base name only.

---

## Parties and identity

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{AGENCY_NAME}}` | Trading name of the service provider (you) | Northbound Outbound | `01-sales/`, `03-audit/` |
| `{{AGENCY_LEGAL_ENTITY}}` | Full registered entity name and company number of the provider | Northbound Outbound Ltd (12345678) | `01-sales/` |
| `{{CLIENT_NAME}}` | Trading name of the client, as it should appear in copy and documents | Contoso Analytics | almost every artifact |
| `{{CLIENT_LEGAL_ENTITY}}` | Full registered entity name of the client, for contracts | Contoso Analytics Inc. | `01-sales/` |
| `{{CLIENT_POSTAL_ADDRESS}}` | Physical mailing address required in every commercial message | 100 Example Plaza, Suite 400, Denver, CO 80202, USA | `05-copy/`, `04-cadence/` |
| `{{CLIENT_CONTACT_NAME}}` | Named individual on the client side who signs off on decisions | A. Rivera | `01-sales/`, `06-onboarding/` |
| `{{CLIENT_CONTACT_EMAIL}}` | Working email for that individual | a.rivera@example.com | `01-sales/`, `06-onboarding/` |
| `{{SENDER_PERSONA_NAME}}` | The human name messages are sent from | J. Okafor | `05-copy/`, `02-infrastructure/` |
| `{{SENDER_PERSONA_TITLE}}` | That person's title, as it appears in the signature | Head of Partnerships | `05-copy/` |
| `{{EFFECTIVE_DATE}}` | Date an agreement takes effect | 2026-03-01 | `01-sales/` |

## Offer and audience

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{ICP_DESCRIPTION}}` | One-paragraph definition of the ideal customer profile: who, what size, what role, in what situation | Operations leaders at 50-500 employee firms that run scheduling on spreadsheets | `05-copy/`, `06-onboarding/`, `07-data/enrichment-spec.md` |
| `{{OFFER_DESCRIPTION}}` | What the client sells, in one sentence, in the buyer's language | Software that turns a spreadsheet schedule into a live board | `05-copy/`, `06-onboarding/` |
| `{{PROBLEM_STATEMENT}}` | The specific, expensive problem the offer removes | Schedulers rebuild the same plan three times a day because nothing syncs | `05-copy/brain-file-template.md` |
| `{{PROOF_POINT}}` | A substantiable claim: a metric, named reference, certification, or case outcome. Numbered where several are needed | Cut rework from three passes a day to one at a 120-unit operator | `05-copy/` |
| `{{OBJECTION}}` | A recurring buyer objection, in the buyer's own words. Numbered where several are needed | "We already have a system for this" | `05-copy/brain-file-template.md` |
| `{{REBUTTAL}}` | The client's answer to the matching objection. Numbered to match | "It sits on top of it; no migration" | `05-copy/brain-file-template.md` |
| `{{PRIMARY_CTA}}` | The single action a message asks for | A 20-minute call this week or next | `05-copy/`, `04-cadence/` |
| `{{REQUIRED_INPUT}}` | The artifact or information a prospect supplies that triggers the interrupt branch | A current schedule export | `04-cadence/`, `06-onboarding/` |
| `{{COMPETITOR_EXCLUSION_LIST}}` | Competitor names never to be mentioned in copy | comma-separated list supplied by the client | `05-copy/` |

## Segmentation and cadence

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{SEGMENT_FIELD}}` | The contact field whose value routes a contact into a lane at cadence entry | `employee_band` | `04-cadence/`, `07-data/` |
| `{{SEGMENT_LANES}}` | The set of lane names the segment field maps to | enterprise, mid-market, smb | `04-cadence/` |
| `{{SEGMENT_LANE}}` | A single lane name, where one is referenced | mid-market | `04-cadence/`, `05-copy/` |
| `{{CADENCE_LENGTH_DAYS}}` | Days from first touch to the terminal node of the main sequence | 8 | `04-cadence/`, `06-onboarding/` |
| `{{CHANNELS_AVAILABLE}}` | Channels the client is cleared to use | email, sms | `04-cadence/` |
| `{{NODE_ID}}` | Identifier of a single cadence node, used when referencing one | N4 | `04-cadence/`, `05-copy/variant_prompt.md` |
| `{{VARIANT_COUNT}}` | How many copy variants to generate per node | 3 | `05-copy/variant_prompt.md` |

## Infrastructure

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{PRIMARY_DOMAIN}}` | The client's main brand domain. Never used for cold sending | example.com | `02-infrastructure/`, `03-audit/` |
| `{{SENDING_DOMAIN}}` | A single secondary domain used for cold sending | example-hq.com | `02-infrastructure/`, `03-audit/`, `05-copy/` |
| `{{SENDING_DOMAIN_LIST}}` | All secondary sending domains in the estate | example-hq.com, get-example.com, example-team.com | `02-infrastructure/` |
| `{{DOMAIN_COUNT}}` | Number of secondary sending domains | 3 | `02-infrastructure/`, `01-sales/pricing-model.md` |
| `{{MAILBOX_COUNT}}` | Total mailboxes across the estate | 9 | `02-infrastructure/`, `01-sales/pricing-model.md` |
| `{{MAILBOXES_PER_DOMAIN}}` | Mailboxes on each sending domain | 3 | `02-infrastructure/` |
| `{{DAILY_SEND_CEILING}}` | Maximum sends per mailbox per day at steady state | 40 | `02-infrastructure/`, `04-cadence/` |
| `{{TARGET_MONTHLY_SENDS}}` | Total sends per month the estate must sustain | 20000 | `02-infrastructure/`, `01-sales/` |
| `{{ESP_NAME}}` | Email service provider hosting the mailboxes | google-workspace | `02-infrastructure/`, `03-audit/` |
| `{{SENDING_PLATFORM}}` | The tool that executes sends against those mailboxes | client's chosen sequencer | `02-infrastructure/`, `04-cadence/` |
| `{{CRM_NAME}}` | The CRM or automation platform the cadence is built in | client's chosen CRM | `04-cadence/`, `06-onboarding/` |
| `{{SPF_INCLUDE}}` | The `include:` mechanism the ESP requires in SPF | `_spf.example.net` | `02-infrastructure/dns_records.py` |
| `{{DKIM_SELECTOR}}` | Selector label in the DKIM record hostname | `s1` | `02-infrastructure/dns_records.py` |
| `{{DKIM_PUBLIC_KEY}}` | The base64 public key the ESP issues after domain verification | issued by the ESP; paste verbatim | `02-infrastructure/dns_records.py` |
| `{{DMARC_RUA_ADDRESS}}` | Mailbox receiving DMARC aggregate reports | dmarc-reports@example.com | `02-infrastructure/`, `03-audit/` |
| `{{MX_HOST}}` | Mail exchanger hostname for the sending domain | mx.example.net | `02-infrastructure/dns_records.py` |
| `{{TRACKING_SUBDOMAIN}}` | Hostname used for click and open tracking | `track.example-hq.com` | `02-infrastructure/dns_records.py`, `05-copy/copy-rules.md` |
| `{{TRACKING_CNAME_TARGET}}` | The host that tracking subdomain points at | tracking.example.net | `02-infrastructure/dns_records.py` |
| `{{SMS_PROVIDER}}` | SMS platform, if SMS is in scope | client's chosen provider | `04-cadence/`, `05-copy/copy-rules.md` |
| `{{SMS_SENDER_ID}}` | The number or alphanumeric ID SMS is sent from | +1 555 0100 | `04-cadence/`, `05-copy/` |
| `{{SMS_STOP_KEYWORD}}` | Opt-out keyword honoured on the SMS channel | STOP | `05-copy/copy-rules.md`, `04-cadence/` |
| `{{SMS_HELP_KEYWORD}}` | Help keyword honoured on the SMS channel | HELP | `05-copy/copy-rules.md` |

## Compliance

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{JURISDICTIONS}}` | Jurisdictions the list touches, which determines which rule set applies | US, UK, CA | every outbound artifact |
| `{{UNSUBSCRIBE_URL}}` | One-click opt-out endpoint | https://example.com/unsubscribe | `05-copy/`, `04-cadence/`, `07-data/` |
| `{{PRIVACY_POLICY_URL}}` | Public privacy notice covering the outbound processing | https://example.com/privacy | `05-copy/` |
| `{{DATA_CONTROLLER_NAME}}` | The entity acting as controller for GDPR purposes | Contoso Analytics Inc. | `01-sales/`, `05-copy/` |
| `{{DPO_CONTACT}}` | Data protection contact address, where one is required | privacy@example.com | `05-copy/`, `01-sales/` |
| `{{LIA_REFERENCE}}` | Reference to the completed Legitimate Interest Assessment on file for UK/EU sending | LIA-2026-014 | `01-sales/`, `05-copy/copy-rules.md` |
| `{{DATA_RETENTION_DAYS}}` | How long prospect records are kept before deletion | 730 | `07-data/`, `01-sales/retainer-scope-template.md` |
| `{{REQUIRED_DISCLAIMER}}` | Any wording the client's counsel requires in every message | regulated clients only; often none | `05-copy/` |
| `{{FORBIDDEN_WORDS}}` | Words and claims the client bans, beyond the universal list | guarantee, risk-free, certified | `05-copy/` |
| `{{TONE_CONSTRAINTS}}` | How the client's copy should sound, on the formality / directness / depth / warmth / length axes | Direct and plain; formality 2 of 5, directness 4 of 5 | `05-copy/`, `06-onboarding/` |

## Commercial

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{CURRENCY}}` | Currency all amounts are quoted in | USD | `01-sales/` |
| `{{SPRINT_PRICE}}` | Fixed price for the infrastructure sprint | 6,000 | `01-sales/sprint-scope-template.md` |
| `{{RETAINER_PRICE}}` | Monthly price for the managed pipeline | 3,500 | `01-sales/retainer-scope-template.md` |
| `{{AUDIT_PRICE}}` | Price for a standalone deliverability audit | 1,500 | `01-sales/pricing-model.md` |
| `{{FLOOR_PRICE}}` | Price below which the engagement loses money, computed in the pricing model | 4,200 | `01-sales/pricing-model.md` |
| `{{HOURLY_COST_RATE}}` | Fully loaded internal cost of an hour of delivery time | 85 | `01-sales/pricing-model.md` |
| `{{PAYMENT_TERMS_DAYS}}` | Days from invoice to payment due | 14 | `01-sales/` |
| `{{NOTICE_PERIOD_DAYS}}` | Days of notice to terminate the retainer | 30 | `01-sales/retainer-scope-template.md` |
| `{{SENDING_VOLUME_CEILING}}` | Monthly send ceiling included in the retainer before overage applies | 20000 | `01-sales/retainer-scope-template.md` |
| `{{OVERAGE_RATE}}` | Price per additional block of sends above the ceiling | 90 per 1,000 | `01-sales/retainer-scope-template.md` |
| `{{LIST_REFRESH_CADENCE}}` | How often new contacts are added to the pipeline | monthly | `01-sales/retainer-scope-template.md` |
| `{{COPY_ITERATION_CYCLES}}` | Copy revision rounds included per month | 2 | `01-sales/retainer-scope-template.md` |
| `{{REPORTING_CADENCE}}` | How often the client receives performance reporting | weekly | `01-sales/` |
| `{{INITIAL_LIST_SIZE}}` | Contacts ingested and loaded as part of the sprint | 5000 | `01-sales/sprint-scope-template.md` |
| `{{LIST_REFRESH_SIZE}}` | New contacts added per refresh under the retainer | 1500 | `01-sales/retainer-scope-template.md` |
| `{{PASSTHROUGH_ESTIMATE}}` | Estimated third-party costs invoiced at cost, separately from the fee | 800 | `01-sales/sprint-scope-template.md` |

## Audit

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{AUDIT_DATE}}` | Date the audit was performed | 2026-03-14 | `03-audit/` |
| `{{AUDITOR_NAME}}` | Who performed the audit | J. Okafor | `03-audit/` |
| `{{AUDIT_PERIOD}}` | The window of sending data the audit covers | 2026-01-01 to 2026-03-13 | `03-audit/` |
| `{{OVERALL_ASSESSMENT}}` | One-line verdict on the state of the sending programme | Fixable; two specific technical faults account for most of the loss | `03-audit/audit-template.md` |
| `{{COUNT_CRITICAL}}` | Number of critical findings in the audit | 2 | `03-audit/audit-template.md` |
| `{{COUNT_HIGH}}` | Number of high-severity findings | 5 | `03-audit/audit-template.md` |
| `{{COUNT_MEDIUM}}` | Number of medium-severity findings | 7 | `03-audit/audit-template.md` |
| `{{COUNT_LOW}}` | Number of low-severity findings | 1 | `03-audit/audit-template.md` |
| `{{BLOCKLIST_STATUS}}` | Result of the public blocklist check across the estate | none | `03-audit/audit-template.md` |
| `{{YOUNGEST_DOMAIN_AGE}}` | Age of the newest sending domain | 11 months | `03-audit/audit-template.md` |
| `{{BOUNCE_RATE}}` | Observed hard bounce rate over the audit period | 6.1% | `03-audit/audit-template.md` |
| `{{COMPLAINT_RATE}}` | Observed spam complaint rate over the audit period | 0.08% | `03-audit/audit-template.md` |
| `{{UNSUBSCRIBE_RATE}}` | Observed unsubscribe rate over the audit period | 0.4% | `03-audit/audit-template.md` |
| `{{DUPLICATE_COUNT}}` | Contacts enrolled in more than one active cadence | 412 | `03-audit/audit-template.md` |
| `{{ROLE_ADDRESS_COUNT}}` | Role addresses found on the list | 233 | `03-audit/audit-template.md` |
| `{{STALE_RECORD_COUNT}}` | Records older than the retention period | 0 | `03-audit/audit-template.md` |
| `{{FIRST_TOUCH_LINK_COUNT}}` | Links found in the opening message of each sequence | 2 | `03-audit/audit-template.md` |
| `{{IMAGE_COUNT}}` | Images found in cold messages | 0 | `03-audit/audit-template.md` |
| `{{TEXT_HTML_RATIO}}` | Balance of text to HTML in the sending templates | high, mostly plain text | `03-audit/audit-template.md` |
| `{{OBSERVED_DAILY_VOLUME}}` | Sends per mailbox per day actually observed, against the planned ceiling | 52 | `03-audit/audit-template.md` |
| `{{INBOX_PLACEMENT_RATE}}` | Overall inbox placement across the seed test providers | 61% | `03-audit/audit-template.md` |
| `{{TESTED_MESSAGE}}` | Which message the seed test used | Node 1, mid-market lane, production copy | `03-audit/audit-template.md` |

## Data pipeline

| Variable | Meaning | Example | Used by |
|---|---|---|---|
| `{{DATABASE_URL}}` | Postgres connection string. Supply via the `DATABASE_URL` environment variable, never written to a file | postgresql://user:pass@localhost:5432/outbound | `07-data/` |
| `{{ENRICHMENT_PROVIDER}}` | The enrichment vendor in use for this client | whichever satisfies the provider interface | `07-data/enrichment-spec.md` |
| `{{ICP_SCORE_THRESHOLD}}` | Minimum fit score for a contact to be sent to | 60 | `07-data/enrichment-spec.md`, `06-onboarding/` |
| `{{SOURCE_NAME}}` | Label identifying where an imported list came from | conference-attendee-list-q1 | `07-data/` |

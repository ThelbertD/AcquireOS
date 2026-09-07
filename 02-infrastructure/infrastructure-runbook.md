# Infrastructure Runbook

The ordered operational procedure for building a cold email sending estate from nothing to
cleared-for-production. Every step states what to do, what you should see when it worked, and
what to check when it did not.

This is written to be executable by someone who has not done it before. Do not skip steps
because they look obvious; the failure modes in cold email infrastructure are almost all
silent, and most of them are introduced in the first two hours.

**Client:** `{{CLIENT_NAME}}`
**Primary domain:** `{{PRIMARY_DOMAIN}}`
**ESP:** `{{ESP_NAME}}`
**Sending platform:** `{{SENDING_PLATFORM}}`
**Started:** ____________
**Operator:** ____________

---

## Phase 0 — Prerequisites

Nothing in this runbook can start until these exist.

### 0.1 Completed intake

**Do:** Confirm `06-onboarding/intake-form.md` is filled and run
`06-onboarding/intake_to_spec.py` against it.

**Expect:** A build spec with an empty blocker list.

**If it fails:** The script prints what is missing or ambiguous. Those are answers only the
client has. Get them before starting; a build that begins on assumptions gets rebuilt.

### 0.2 Registrar and DNS access

**Do:** Confirm you have an account with write access to DNS for the domains you will
register. Note whether DNS is hosted at the registrar or elsewhere.

**Expect:** You can create and delete a test TXT record and see it resolve.

**If it fails:** DNS hosted at a third party the client controls is the most common cause of a
stalled build. Establish the access route on day 0, not on the day you need to publish records.

### 0.3 ESP admin access

**Do:** Confirm admin access to `{{ESP_NAME}}` with the ability to add domains, provision
users, and generate DKIM keys.

**Expect:** Admin console loads and shows the domain management section.

**If it fails:** Delegated admin is usually enough; full super-admin is usually not required.
Ask for the least access that lets you add a domain and generate a key.

### 0.4 Compliance clearance

**Do:** Confirm which jurisdictions the list will touch (`{{JURISDICTIONS}}`), and that the
client's counsel has signed off on cold outbound to them.

**Expect:** A written answer naming the jurisdictions, and for any UK/EU sending, a completed
Legitimate Interest Assessment on file with reference `{{LIA_REFERENCE}}`.

**If it fails:** For Canada specifically, do not proceed on assumption. CASL requires consent
— express or implied — before the first message, not an opt-out after it, and implied consent
has a defined and short window. If the client cannot say which basis applies to their Canadian
contacts, exclude Canada from the list until they can. This is not a step to work around.

---

## Phase 1 — Plan the estate

### 1.1 Run the domain plan

**Do:**

```bash
python 02-infrastructure/domain_plan.py \
    --primary-domain {{PRIMARY_DOMAIN}} \
    --monthly-volume {{TARGET_MONTHLY_SENDS}}
```

**Expect:** A domain count, a mailbox count, a per-mailbox daily ceiling, and a list of
suggested domain names, with the arithmetic shown.

**If it fails:** The script refuses inputs it cannot produce a sane plan from — a target above
about 40 domains, or a requested per-mailbox ceiling above 100. Both mean the volume target
needs revisiting with the client rather than the tool needing overriding.

### 1.2 Sanity-check the plan against reply capacity

**Do:** Multiply the monthly volume by 3%. That is roughly how many replies a month the client
will receive, and every one needs a human answer within a working day.

**Expect:** A number the client's team can actually handle.

**If it fails:** An estate that generates more replies than the client can answer is worse than
no estate. Unanswered replies burn the list permanently and generate complaints. Reduce the
volume target and re-run 1.1.

### 1.3 Check the suggested names

**Do:** For each suggested domain, check availability at the registrar, and search the name to
confirm it is not an existing company, not close to a competitor's name, and has no history.

**Expect:** Enough clean, available names to cover `{{DOMAIN_COUNT}}`.

**If it fails:** A previously-owned domain carries its previous owner's reputation, which you
cannot see and cannot fix. Prefer a never-registered name over a better-looking one with
history. Check any candidate's registration history before buying.

---

## Phase 2 — Register and configure domains

### 2.1 Register the domains

**Do:** Register all `{{DOMAIN_COUNT}}` domains at once, with the same registrar, same WHOIS
privacy setting, and auto-renew on.

**Expect:** All domains show as active in the registrar account.

**If it fails:** If one name in the set is unavailable, take the next one from the suggestion
list rather than mutating the pattern into something odd. Consistency across the estate is
worth more than any individual name.

**Note:** Register now even though warmup starts later. Domain age accrues from registration,
it is free, and it is the one input to deliverability that cannot be bought back later.

### 2.2 Redirect each domain to the primary

**Do:** Configure a 301 redirect from each sending domain (and its `www`) to
`{{PRIMARY_DOMAIN}}`.

**Expect:** `curl -sI https://{{SENDING_DOMAIN}}` returns a 301 with a `Location` header
pointing at the primary domain.

**If it fails:** Some registrars' forwarding does not cover HTTPS without a certificate. A
sending domain that throws a browser certificate warning is worse than one that does not
resolve — a prospect who checks will see a security warning attached to the client's name. Use
a host that issues a certificate, or serve the redirect from the client's existing web host.

### 2.3 Add each domain to the ESP

**Do:** Add each sending domain in the `{{ESP_NAME}}` admin console and complete domain
verification.

**Expect:** Each domain shows as verified.

**If it fails:** Verification records are usually a TXT record at the apex. If verification
does not complete after 30 minutes, check the record has not been double-appended — some DNS
hosts add the domain name to a record automatically, producing
`verification.example-hq.com.example-hq.com`.

---

## Phase 3 — DNS records

### 3.1 Generate the record set

**Do:** For each domain:

```bash
python 02-infrastructure/dns_records.py \
    --domain {{SENDING_DOMAIN}} \
    --esp {{ESP_NAME}} \
    --rua {{DMARC_RUA_ADDRESS}}
```

**Expect:** A table of MX, SPF, DMARC, DKIM and tracking records.

**If it fails:** If `{{ESP_NAME}}` is not a built-in profile, use `--esp generic` and fill the
`{{SPF_INCLUDE}}` and `{{MX_HOST}}` placeholders from the provider's documentation, or write
an `--esp-config` JSON file so the next build gets it for free.

### 3.2 Create the DMARC reporting mailbox

**Do:** Create `{{DMARC_RUA_ADDRESS}}` before publishing any DMARC record.

**Expect:** The mailbox exists and receives mail.

**If it fails:** A `rua` address that bounces means the aggregate reports are lost, and the
DMARC record is then decoration. This mailbox must be real and must be read weekly — it is the
only view you get of who is sending as this domain.

### 3.3 Publish MX, SPF and DMARC

**Do:** Enter the MX, SPF and DMARC records at the DNS host. Publish all three before DKIM.

**Expect:**

```bash
dig +short MX {{SENDING_DOMAIN}}
dig +short TXT {{SENDING_DOMAIN}} | grep spf1
dig +short TXT _dmarc.{{SENDING_DOMAIN}}
```

Each returns exactly one relevant answer.

**If it fails:**

- *SPF returns two records* — this is a permanent error and breaks authentication entirely.
  Merge them into one record with multiple `include:` mechanisms. Never publish two.
- *SPF exceeds 10 DNS lookups* — each `include:` costs at least one lookup and nested includes
  cost more. Over ten and receivers return permerror. Count them; flatten if needed.
- *Nothing resolves* — check the record was created at the apex (`@`) and not at a subdomain.
  Many DNS hosts append the domain to whatever you type in the host field.

### 3.4 Generate and publish DKIM

**Do:** In the `{{ESP_NAME}}` console, generate a 2048-bit DKIM key for the domain. Publish
the record. Wait for it to resolve. **Then** activate signing in the console.

**Expect:** `dig +short TXT {{DKIM_SELECTOR}}._domainkey.{{SENDING_DOMAIN}}` returns the key,
and the console shows signing as active.

**If it fails:**

- *Activated before the record resolved* — the provider signs with a key receivers cannot
  find, so DKIM fails on every message sent in the window. Deactivate, wait for the record,
  reactivate.
- *Key value rejected as too long* — a 2048-bit key exceeds the 255-character limit for a
  single TXT string and must be split into multiple quoted strings within one record. Most DNS
  hosts do this automatically; a few require it manually.
- *Provider offers a 1024-bit key* — use 2048. 1024-bit DKIM is treated as weak by some
  receivers.

### 3.5 Publish the tracking CNAME, if tracking is used

**Do:** Only if `{{SENDING_PLATFORM}}` will use link or open tracking, publish the CNAME for
`{{TRACKING_SUBDOMAIN}}`.

**Expect:** The CNAME resolves to `{{TRACKING_CNAME_TARGET}}`.

**If it fails:** If tracking is not being used in the first weeks, skip this and add it later.
Never use the sending platform's shared tracking domain — those are widely blocklisted, and a
single link pointing at one can put an otherwise clean message in spam.

### 3.6 Verify end to end

**Do:** Send one message from each domain to a seed address on a provider that exposes
authentication results. Read the raw headers.

**Expect:** `spf=pass`, `dkim=pass`, and `dmarc=pass` all present.

**If it fails:**

- *`dmarc=fail` with SPF and DKIM both passing* — an alignment problem. The domain in the
  `From:` header must match the domain that SPF or DKIM authenticated. This usually means the
  sending platform is putting its own domain in the envelope sender and the record set has not
  accounted for it.
- *`dkim=none`* — signing is not active, or is active for a different domain in the tenant.
- *`spf=softfail`* — the sending IP is not covered by the `include:`. If sending through
  `{{SENDING_PLATFORM}}` rather than directly through `{{ESP_NAME}}`, the platform's own
  include is also required.

**Do not proceed past this step with any failure.** Everything after this builds a reputation
on top of the authentication set. Building on a broken one wastes the entire warmup period.

---

## Phase 4 — Mailboxes

### 4.1 Provision mailboxes

**Do:** Create `{{MAILBOXES_PER_DOMAIN}}` mailboxes on each domain, named after real people
who have agreed to it.

**Expect:** `{{MAILBOX_COUNT}}` mailboxes total, all able to send and receive.

**If it fails:** Do not invent people. A prospect who searches the sender's name and finds
nothing is a lost prospect; one who finds a fabricated persona is a complaint. Use real staff,
with permission. If the client has fewer people than the estate needs mailboxes, the estate is
too large for the client — go back to 1.2.

### 4.2 Configure each mailbox

**Do:** For every mailbox, set:

- Display name: the person's real name, formatted consistently across the estate
- Profile photo: a real photo of that person
- Signature: name, title, company, and `{{CLIENT_POSTAL_ADDRESS}}`
- Reply-to: the mailbox itself, not a central address

**Expect:** A test message from each mailbox arrives with the correct display name, photo and
signature.

**If it fails:** A missing physical postal address in the signature is a CAN-SPAM violation and
a CASL violation, not a styling issue. Check every mailbox individually; a signature template
applied at the tenant level frequently does not apply to all users.

### 4.3 Set per-mailbox sending limits

**Do:** In `{{SENDING_PLATFORM}}`, cap each mailbox at the current warmup week's volume, not
at the steady-state ceiling.

**Expect:** Configured limit matches week 1 of `warmup-checklist.md`.

**If it fails:** Platforms default to their own limits, which are far above what a new domain
survives. Setting this at the platform level rather than trusting the sequence configuration
prevents a mistake in a sequence from dumping a week of volume in an hour.

### 4.4 Verify inbound

**Do:** Send a message *to* every mailbox from an external address and confirm it arrives.

**Expect:** Delivery within a minute.

**If it fails:** MX misconfiguration. A mailbox that cannot receive loses every reply — which
is the entire point of the exercise — and loses bounce notifications, so the list quality
signal disappears too.

---

## Phase 5 — Warmup

### 5.1 Run the pre-warmup gate

**Do:** Work through the gate checklist at the top of `02-infrastructure/warmup-checklist.md`.

**Expect:** Every line checked.

**If it fails:** Fix before starting. Warming a domain with broken authentication builds a
history of authentication failures, which is worse than having no history at all.

### 5.2 Enrol mailboxes in the warmup network

**Do:** Add every mailbox to the warmup network at week 1 volumes.

**Expect:** Warmup traffic sending and being replied to within 24 hours.

**If it fails:** If the warmup network shows messages landing in spam from day one, the problem
is authentication or domain history, not warmup. Stop and re-check phase 3.

### 5.3 Run the manual warmup

**Do:** For the first week, send 2–3 real messages per mailbox per day by hand to real people
who will reply, including accounts on the major consumer providers. Ask them to reply and to
move the message to the inbox if it lands elsewhere.

**Expect:** Real replies in the mailbox.

**If it fails:** This step gets skipped more than any other because it is manual and boring. It
is also the highest-value step in week 1. Do not skip it.

### 5.4 Follow the schedule

**Do:** Follow `warmup-checklist.md` week by week. Check the daily signals table every day.

**Expect:** Volume rising ~30–40% weekly, bounce rate under 2%, complaints under 0.1%.

**If it fails:** The failure signs table in that document maps each symptom to its most likely
cause. The pause rule is: drop to the previous week's volume, hold for three days of recovery,
resume the ramp. Do not stop entirely and do not push through.

---

## Phase 6 — Data and cadence

These run in parallel with warmup. Warmup takes three to four weeks of waiting; use it.

### 6.1 Stand up the database

**Do:**

```bash
psql "$DATABASE_URL" -f 07-data/schema.sql
```

**Expect:** Tables created without error.

**If it fails:** The schema is idempotent — re-running is safe. A permissions error means the
role cannot create extensions; `citext` requires it.

### 6.2 Load and validate the list

**Do:** Dry run first, always:

```bash
python 07-data/list_pipeline.py --csv list.csv --mapping mapping.json --dry-run
```

**Expect:** A summary of accepted and rejected rows with a reason per rejection.

**If it fails:** Read the rejection reasons before adjusting anything. A high invalid-syntax
count usually means a column mapping error rather than a bad list.

### 6.3 Verify deliverability of the list

**Do:** Run the list through email verification before the first send.

**Expect:** Under 2% projected bounce rate.

**If it fails:** Do not send an unverified list from a new domain. This single decision causes
more failed builds than anything else in this runbook. The cost of verification is trivial
against the cost of burning a warmed estate.

### 6.4 Build the cadence

**Do:**

```bash
python 04-cadence/cadence_builder.py \
    --segments {{SEGMENT_LANES}} \
    --channels {{CHANNELS_AVAILABLE}} \
    --length {{CADENCE_LENGTH_DAYS}}
```

Then implement it in `{{CRM_NAME}}` following `04-cadence/crm-build-checklist.md`.

**Expect:** A node map and a build order.

**If it fails:** See the platform differences section of the CRM checklist. Delay handling and
branch merging are where implementations diverge.

### 6.5 Write the copy

**Do:** Fill `05-copy/brain-file-template.md` with the client, then generate variants per node
using `05-copy/variant_prompt.md`, constrained by `05-copy/copy-rules.md`.

**Expect:** Copy for every node, within length limits, no unsubstantiated claims, correct
unsubscribe handling for every jurisdiction in `{{JURISDICTIONS}}`.

**If it fails:** The most common blocker is an empty proof points section in the brain file.
Copy without proof becomes copy with invented proof. Go back to the client.

---

## Phase 7 — Clearance and handover

### 7.1 Run the clearance decision

**Do:** Work through the clearance checklist in `warmup-checklist.md` for each domain.

**Expect:** Every line passing, per domain.

**If it fails:** Do not clear a domain that fails any line, and do not add domains to
compensate for one that is underperforming.

### 7.2 Go live at full volume

**Do:** Raise `{{SENDING_PLATFORM}}` limits to `{{DAILY_SEND_CEILING}}` per mailbox. Keep the
warmup network running at ~20% of volume permanently.

**Expect:** Volume at the planned steady state, signals unchanged.

**If it fails:** If any signal degrades in the first week at full volume, drop back to 60% and
hold for a week. A domain that cannot hold full volume was cleared too early.

### 7.3 Hand over the register

**Do:** Give the client a document listing every domain, every mailbox, where DNS is hosted,
where the DMARC reports go, and what the renewal dates are.

**Expect:** The client can operate the estate without you.

**If it fails:** Per `01-sales/sprint-scope-template.md` and
`01-sales/retainer-scope-template.md`, the client owns the domains and the data. A handover
that leaves them dependent on your access is a scope violation, and it makes the renewal
conversation adversarial.

### 7.4 Set the recurring checks

**Do:** Diarise: DMARC reports weekly, seed test monthly, blocklist check monthly, domain
renewals annually.

**Expect:** Owned, dated, recurring tasks.

**If it fails:** An expired sending domain takes its mailboxes with it and takes down every
active sequence running through them. This is entirely preventable and entirely avoidable with
auto-renew plus a calendar entry.

---

## Rollback

Nothing in this runbook is destructive to the client's existing mail. The estate is built
entirely on new domains, which is the point: `{{PRIMARY_DOMAIN}}` is never touched, so the
worst case is the loss of the new estate rather than the client's ability to send mail.

To roll back a domain:

1. Pause every sequence sending through its mailboxes in `{{SENDING_PLATFORM}}`.
2. Leave the DNS records published. Removing them does not repair reputation and destroys the
   ability to diagnose what went wrong.
3. Leave the domain registered and redirecting. A dead redirect on a domain that has sent mail
   is a worse signal than a live one.
4. Record what happened and at what volume, in the seed test log.
5. If the domain must be replaced, register the new one and start phase 2. A burned domain does
   not recover to a usable state on any timeline worth waiting for.

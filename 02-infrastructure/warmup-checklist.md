# Warmup Checklist

**Domain:** `{{SENDING_DOMAIN}}`
**Mailboxes:** `{{MAILBOXES_PER_DOMAIN}}`
**Target steady-state volume:** `{{DAILY_SEND_CEILING}}` cold sends per mailbox per day
**Warmup started:** ____________
**Cleared for live sending:** ____________ (signed off by ____________)

---

## What warmup actually is

A new domain has no sending history. To a receiving mail server, a domain that appears from
nowhere and immediately sends four hundred messages to strangers is indistinguishable from a
domain bought that morning to send spam — because that is usually what it is.

Warmup builds the missing history. It generates a record of low-volume mail that gets opened,
replied to, and moved out of the spam folder, so that by the time real cold volume starts, the
domain has a track record that says "mail from here gets engaged with."

Two things follow from this, and they are the whole discipline:

1. **Volume ramps slowly, and only ever upward.** A drop back to zero and a jump back up is
   worse than a flat line.
2. **Engagement matters more than volume.** A domain sending 20 messages a day with a 30%
   reply rate warms faster and safer than one sending 100 with a 2% reply rate.

Warmup is not a countdown. It is a set of conditions. A domain that has been warming for six
weeks and still fails the gate conditions is not ready, and the fix is diagnosis, not patience.

---

## Before week 1 — the gate

Do not start warmup until every one of these is true. Warming a domain with broken
authentication builds a history of failed authentication, which is worse than no history.

- [ ] Domain registered and 301-redirecting to `{{PRIMARY_DOMAIN}}`
- [ ] MX record published and resolving
- [ ] SPF published, exactly one record, resolving
- [ ] DKIM key generated in `{{ESP_NAME}}`, published, and signing activated
- [ ] DMARC published at `p=none` with a working `rua` address
- [ ] A test message sent to a seed inbox shows `spf=pass`, `dkim=pass`, `dmarc=pass` in the
      raw headers
- [ ] Every mailbox has a real human display name, a signature with a physical address, and a
      profile photo
- [ ] Mailboxes are named after people, not roles. No `info@`, `sales@`, `hello@`, `team@`
- [ ] Domain checked against public blocklists and clean
- [ ] Domain age is at least 14 days since registration

**On domain age.** A domain registered yesterday is treated with more suspicion than one
registered a month ago, regardless of what it has sent. Register domains as soon as the
engagement is signed, then let them sit while the rest of the build proceeds. This is free
time that costs nothing to spend.

---

## The schedule

Volumes below are **per mailbox, per day**. Multiply by `{{MAILBOXES_PER_DOMAIN}}` for the
domain total. All sending is weekdays only; weekend sending during warmup is a pattern signal
that does not appear in normal business mail.

Ramp roughly 30–40% week over week. Do not double.

### Week 1 — warmup network only

| | |
|---|---|
| **Volume** | 5 → 15 per mailbox per day, increasing daily |
| **Recipients** | Warmup network only. No prospects. |
| **Content** | Short, plain, conversational. No links. No images. No attachments. |
| **Required** | Every message gets a reply. This is what the warmup network is for. |

- [ ] Day 1: 5/mailbox
- [ ] Day 2: 7/mailbox
- [ ] Day 3: 9/mailbox
- [ ] Day 4: 12/mailbox
- [ ] Day 5: 15/mailbox
- [ ] Check: zero bounces, zero spam placements

**Alongside the automated warmup network, send 2–3 real messages per mailbox per day by hand**
to colleagues, the client's own team, and personal accounts on the major consumer providers.
Ask each recipient to reply, and to drag the message to the inbox if it lands in spam or
Promotions. Hand-sent, hand-replied mail from real accounts is worth more per message than
anything automated, and it is the single highest-leverage thing in week 1.

### Week 2 — warmup network, higher volume

| | |
|---|---|
| **Volume** | 15 → 25 per mailbox per day |
| **Recipients** | Warmup network. Still no prospects. |
| **Content** | Still no links. Vary subject lines and opening sentences between mailboxes. |

- [ ] Ramp to 25/mailbox by end of week
- [ ] Seed test run (see **Seed testing** below). Record inbox placement per provider.
- [ ] Check: bounce rate under 2%, spam placement under 5%

### Week 3 — first live sending

The first real prospects. This is the week the domain is actually tested, because warmup
networks reply to everything and prospects do not.

| | |
|---|---|
| **Volume** | 25 → 35 per mailbox per day total, of which live sends start at 5 and reach 15 |
| **Split** | Keep the warmup network running underneath. Live sends are added on top, not substituted. |
| **Recipients** | The best-scoring, most clearly in-ICP contacts on the list. Do not test a new domain on the marginal end of the list. |
| **Content** | Still no links in the first message of any sequence. Plain text only. |

- [ ] Day 1–2: 5 live sends/mailbox
- [ ] Day 3–4: 10 live sends/mailbox
- [ ] Day 5: 15 live sends/mailbox
- [ ] Check: bounce rate under 2% on live sends, at least one genuine reply per mailbox
- [ ] Second seed test. Compare placement against week 2.

### Week 4 — ramp to steady state

| | |
|---|---|
| **Volume** | Live sends 15 → `{{DAILY_SEND_CEILING}}` per mailbox per day |
| **Warmup network** | Reduce to roughly 20% of total volume and keep it there permanently |
| **Content** | Links may be introduced from the second message of a sequence onward, one link maximum |

- [ ] Ramp live sends to `{{DAILY_SEND_CEILING}}`/mailbox
- [ ] Third seed test
- [ ] Review the first DMARC aggregate reports; confirm no unexpected sending sources
- [ ] Run the **clearance decision** below

### Week 5 onward — steady state

- [ ] Keep the warmup network running at roughly 20% of volume indefinitely. It is not
      scaffolding to be removed; it is the floor under the domain's engagement rate when the
      cold list is performing badly.
- [ ] Seed test monthly, and after every material copy change
- [ ] Read DMARC reports weekly
- [ ] Move DMARC to `p=quarantine` once four consecutive weeks of reports show every
      legitimate source passing, then to `p=reject` two weeks after that

---

## Signals to watch

Check these daily during warmup. The first three are the ones that matter.

| Signal | Healthy | Investigate | Stop sending |
|---|---|---|---|
| **Bounce rate** (hard) | under 2% | 2–5% | over 5% |
| **Spam complaint rate** | under 0.1% | 0.1–0.3% | over 0.3% |
| **Reply rate on live sends** | over 3% | 1–3% | under 1% for 3 consecutive days |
| Inbox placement (seed test) | over 90% | 70–90% | under 70% |
| Open rate, if tracked | over 30% | 15–30% | under 15% |
| Sends deferred by the receiving server | occasional | rising day over day | sustained |

**On bounce rate.** This is a list quality signal, not a domain signal, but it damages the
domain. A bounce rate over 5% means the list was not verified before import. Stop, fix the
list, resume. Continuing to send at that bounce rate will do more damage in three days than
the warmup built in three weeks.

**On complaint rate.** 0.3% sounds small. It is three complaints per thousand sends, and it is
the level at which the major consumer providers begin routing a sender's mail to spam by
default. There is no gradual recovery from a complaint problem; the only fix is to stop, work
out which segment or which message is generating them, and remove it.

**On reply rate.** A reply rate under 1% on live sends is usually a targeting or copy problem
rather than a deliverability one, but the effect on the domain is the same: no engagement
signal. Fix the list or the copy before adding volume.

**On open rate.** Open tracking is unreliable — privacy proxies pre-fetch images and inflate
it, and blocked images deflate it. Treat it as a trend line, never as a number. Do not enable
open tracking at all before week 4.

---

## Failure signs: pause and diagnose

Any one of these means stop adding volume today and find the cause before sending more.

| Sign | Most likely cause | First thing to check |
|---|---|---|
| Bounce rate jumps above 5% | Unverified list segment imported | The `{{SOURCE_NAME}}` of the batch that bounced |
| Sudden drop in replies with volume unchanged | Newly landing in spam | Run a seed test immediately |
| Seed test placement falls below 70% | Reputation damage, or a content trigger | Compare against the last passing seed test; what changed in the copy? |
| Messages deferred or rate-limited by a receiving server | Sending too fast for the domain's age | Reduce volume by half for three days |
| One mailbox performs far worse than its siblings | Mailbox-level problem: signature, display name, or a bad first batch | Compare that mailbox's config field by field against a healthy one |
| A domain appears on a blocklist | Complaints, spam-trap hit, or shared IP contamination | The blocklist's own removal page; identify the cause before requesting delisting |
| DMARC reports show mail from an IP you do not recognise | Domain is being spoofed, or a forgotten system is sending | Do not raise the DMARC policy until this is identified |
| Authentication passes intermittently | Two SPF records, or DKIM activated before the record propagated | Re-run `dns_records.py --verify` and check each record resolves once and only once |

**The pause rule.** When pausing, drop to the previous week's volume, do not stop entirely. A
domain that goes silent for a week loses ramp progress and has to rebuild. Hold at the lower
volume until the signal recovers for three consecutive days, then resume the ramp from there.

---

## Seed testing

A seed test sends the actual production message to a set of accounts held across the major
mailbox providers, then records where each one landed: inbox, Promotions, or spam.

It is the only direct measurement of inbox placement. Everything else — opens, replies,
bounces — is inference.

- [ ] Seed set covers at least: two major consumer webmail providers, one corporate
      Microsoft 365 tenant, one corporate Google Workspace tenant
- [ ] Test with the real message, not a test message. A stripped-down test tells you nothing
      about the copy that is actually sending.
- [ ] Test each sending domain separately. Placement is per-domain.
- [ ] Record the result per provider, dated, in the same place every time. The trend is the
      finding; a single test is close to meaningless.

Record results here:

| Date | Consumer A | Consumer B | Microsoft 365 | Google Workspace | Notes |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |

---

## Clearance decision

A domain moves to full production volume when **all** of the following hold. This is a
checklist, not a judgement call — if one line fails, the domain is not cleared.

- [ ] At least 21 days elapsed since the first warmup send
- [ ] At least 14 days of live sending to real prospects
- [ ] Hard bounce rate under 2% across the last 7 days
- [ ] Spam complaint rate under 0.1% across the last 7 days
- [ ] Reply rate on live sends at or above 3% across the last 7 days
- [ ] Most recent seed test at or above 90% inbox placement, and not lower than the previous one
- [ ] Two consecutive weeks of DMARC aggregate reports with no unrecognised sending sources
- [ ] Zero appearances on any public blocklist
- [ ] Every mailbox on the domain passes independently — one failing mailbox holds the whole
      domain back, because domain reputation is shared

**If the domain fails on time only** — every rate is healthy but it has not been 21 days — wait.
The rates look good because the volume is low. They are not evidence of anything yet.

**If the domain fails on a rate**, do not clear it and do not compensate by adding domains. A
second unhealthy domain sends twice as much unhealthy mail. Diagnose the failing rate first.

---

## Per-domain sign-off

Copy this block once per domain in `{{SENDING_DOMAIN_LIST}}`.

```
Domain:              {{SENDING_DOMAIN}}
Warmup started:      ____________
Live sending from:   ____________
Cleared:             ____________
Cleared by:          ____________

At clearance:
  Bounce rate (7d):        _____%
  Complaint rate (7d):     _____%
  Reply rate (7d):         _____%
  Seed placement:          _____%
  Blocklist appearances:   _____
  DMARC anomalies:         _____

Notes:
```

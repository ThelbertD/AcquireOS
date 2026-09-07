# Pricing Model

A framework for pricing an engagement, not a price list. Prices in this document are worked
examples using placeholder inputs; the inputs are what you fill in.

The purpose is to make two things visible before a number is quoted: **what actually drives the
cost of delivery**, and **the point below which the engagement loses money**. Most
underperforming service businesses are not underpriced in general — they are underpriced on the
specific engagements whose cost drivers they did not measure.

---

## 1. The cost drivers

Six things determine how much work an engagement is. Nothing else moves the number much.

| # | Driver | Why it costs | Scales with |
|---|---|---|---|
| D1 | **Domain count** | Each domain is registration, redirect, four DNS records, verification, and a separate warmup track with its own signals to watch | Volume target |
| D2 | **Mailbox count** | Each mailbox is provisioning, configuration, signature, warmup enrolment, and independent monitoring | Volume target, domain count |
| D3 | **List size and quality** | Sourcing, verification, enrichment, scoring, dedupe, and the rejection triage that follows | Volume target, ICP breadth |
| D4 | **Segment count** | Each lane multiplies the copy: every node, every iteration cycle, every test | Client's segmentation |
| D5 | **Cadence complexity** | Nodes, channels, branches, and the test matrix to prove they work | Node count x lanes x channels |
| D6 | **Reporting depth** | Weekly costs roughly four times monthly, and custom reporting costs more than either | Client's expectations |

**The one people get wrong is D4.** Segment count feels free at the sales stage because it is
just a routing rule. It is not: three lanes across seven nodes is 21 pieces of copy to write, 21
to review, 21 to test, and 21 again for every iteration cycle. A three-lane engagement is close
to three times the copy work of a one-lane engagement forever, not once.

**The one people underestimate is D3.** List work is not a one-off import. It is monthly
sourcing, verification, enrichment, scoring, and the triage of everything that gets rejected —
and the rejections are where the time goes, because each one is a judgement about whether the
list is wrong or the rule is.

---

## 2. Sizing an engagement

Score each driver 1 to 5. The total maps to a price band.

### D1 — Domain count

Derive it, do not guess it. Run `02-infrastructure/domain_plan.py` with the volume target.

| Domains | Score |
|---|---|
| 1–2 | 1 |
| 3–4 | 2 |
| 5–8 | 3 |
| 9–15 | 4 |
| 16+ | 5 |

### D2 — Mailbox count

| Mailboxes | Score |
|---|---|
| 1–6 | 1 |
| 7–12 | 2 |
| 13–24 | 3 |
| 25–45 | 4 |
| 46+ | 5 |

### D3 — List size and quality

| Situation | Score |
|---|---|
| Client supplies a verified list, no sourcing needed | 1 |
| Client supplies a list needing verification and cleaning | 2 |
| Provider sources from a clear, well-defined ICP | 3 |
| Provider sources from a broad or ambiguous ICP | 4 |
| Provider sources from a niche where no data source covers it well | 5 |

### D4 — Segment count

| Lanes | Score |
|---|---|
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |
| 4–5 | 4 |
| 6 | 5 |

### D5 — Cadence complexity

| Configuration | Score |
|---|---|
| Email only, 5 or fewer nodes, no interrupt branch | 1 |
| Email only, 6–8 nodes, interrupt branch | 2 |
| Email only, 6–8 nodes, interrupt branch, multiple lanes | 3 |
| Email plus SMS, full branching | 4 |
| Multi-channel, custom branching, integrations | 5 |

### D6 — Reporting depth

| Cadence | Score |
|---|---|
| Monthly written report | 1 |
| Monthly report plus a call | 2 |
| Fortnightly | 3 |
| Weekly report plus a call | 4 |
| Weekly plus custom dashboards or bespoke metrics | 5 |

### Total

`Complexity score = D1 + D2 + D3 + D4 + D5 + D6`

Range 6 to 30.

| Score | Band | Typical shape |
|---|---|---|
| 6–10 | **Band A** | One lane, small estate, client-supplied list, monthly reporting |
| 11–15 | **Band B** | Two lanes, moderate estate, provider-sourced list, monthly reporting |
| 16–20 | **Band C** | Three lanes, larger estate, multi-channel or weekly reporting |
| 21–25 | **Band D** | Four-plus lanes, large estate, multi-channel, weekly reporting |
| 26–30 | **Band E** | At the ceiling of every driver. Scope it down or price it as a programme. |

---

## 3. From band to price

### 3.1 Estimate the hours

Delivery hours per band, from the work each driver actually requires.

**Sprint (one-off)**

| Band | Setup | Cadence build | Copy | List | Testing and handover | Total |
|---|---|---|---|---|---|---|
| A | 8 | 6 | 6 | 4 | 6 | **30** |
| B | 12 | 9 | 12 | 8 | 8 | **49** |
| C | 18 | 13 | 20 | 12 | 11 | **74** |
| D | 26 | 18 | 30 | 18 | 15 | **107** |
| E | 36 | 26 | 44 | 26 | 20 | **152** |

**Retainer (per month)**

| Band | List | Copy iteration | Monitoring | Reporting | Total |
|---|---|---|---|---|---|
| A | 3 | 3 | 3 | 2 | **11** |
| B | 5 | 6 | 5 | 3 | **19** |
| C | 8 | 10 | 8 | 5 | **31** |
| D | 12 | 16 | 12 | 8 | **48** |
| E | 18 | 24 | 18 | 12 | **72** |

### 3.2 Apply the formula

```
Delivery cost   = hours x {{HOURLY_COST_RATE}}
Tooling cost    = per-engagement tooling not passed through to the client
Overhead        = (delivery cost + tooling) x overhead_rate
Total cost      = delivery cost + tooling + overhead
Price           = total cost / (1 - target_margin)
```

**Defaults, all of which you should replace with your own measured figures:**

| Input | Default | What it means |
|---|---|---|
| `{{HOURLY_COST_RATE}}` | 85 | Fully loaded cost of an hour of delivery: salary, employer taxes, benefits, equipment, and non-billable time. Not a salary divided by 2,080. |
| `overhead_rate` | 0.35 | Sales, admin, software, premises, finance — everything not attributable to one engagement |
| `target_margin` | 0.45 | Gross margin before overhead is recovered a second time. Below 0.35, one bad engagement erases a quarter. |

### 3.3 Worked example — Band B sprint

```
Hours                49
Delivery cost        49 x 85                      = 4,165
Tooling              per-engagement, not passed through =   250
Subtotal                                          = 4,415
Overhead             4,415 x 0.35                 = 1,545
Total cost                                        = 5,960
Price                5,960 / (1 - 0.45)           = 10,836
Quoted               rounded                      = 11,000
```

### 3.4 Worked example — Band B retainer

```
Hours per month      19
Delivery cost        19 x 85                      = 1,615
Tooling              per-engagement, not passed through =   120
Subtotal                                          = 1,735
Overhead             1,735 x 0.35                 =   607
Total cost                                        = 2,342
Price                2,342 / (1 - 0.45)           = 4,258
Quoted               rounded                      = 4,300
```

---

## 4. The floor price

**The floor is the price below which the engagement destroys value.** It is not the price at
which margin is thin. It is the price at which taking the work makes the business worse off than
turning it down.

### 4.1 Deriving it

The floor is the higher of two numbers.

**Floor 1 — total cost.** Below total cost, every month of delivery consumes cash. Overhead is
included because overhead is real whether or not it is attributed to this engagement.

```
Floor 1 = hours x {{HOURLY_COST_RATE}} x (1 + overhead_rate) + tooling
```

**Floor 2 — opportunity cost.** Delivery capacity is finite. An engagement priced below what the
same hours would earn at target margin is not merely low-margin; it occupies the capacity that a
correctly-priced engagement would have used.

```
Floor 2 = hours x {{HOURLY_COST_RATE}} / (1 - target_margin) x displacement_factor
```

Where `displacement_factor` is how full the delivery pipeline is:

| Utilisation | Factor | Reasoning |
|---|---|---|
| Under 50% | 0.6 | Capacity is genuinely idle; some contribution beats none |
| 50–75% | 0.85 | Some displacement |
| Over 75% | 1.0 | Every hour taken is an hour unavailable to a better engagement |

```
{{FLOOR_PRICE}} = max(Floor 1, Floor 2)
```

### 4.2 Worked example — Band B retainer at 80% utilisation

```
Floor 1 = 19 x 85 x 1.35 + 120        = 2,300
Floor 2 = 19 x 85 / (1 - 0.45) x 1.0  = 2,936

{{FLOOR_PRICE}} = max(2,300, 2,936)   = 2,936, round to 2,950
```

Against a quoted 4,300 that is a 31% discount available before the engagement stops being worth
taking. **At 4,300 the margin is 45%; at 2,950 it is 20%; at 2,300 it is zero.**

### 4.3 Worked example — the same engagement at 40% utilisation

```
Floor 1 = 2,300
Floor 2 = 19 x 85 / (1 - 0.45) x 0.6  = 1,762

{{FLOOR_PRICE}} = max(2,300, 1,762)   = 2,300
```

With idle capacity the floor drops to total cost, because there is no better use for the hours.
It does not drop below it: work priced below cost gets worse the more of it you do.

### 4.4 Why the floor is not a target

Discounting to the floor is a decision to earn nothing on the engagement while carrying all of
its risk — the client who does not answer replies, the domain that burns, the scope that drifts.
A quote at the floor should be rare and deliberate: a reference client in a segment you want to
enter, a first engagement with an account that has obvious expansion, or genuinely idle capacity.

**Never discount for the reason clients ask you to.** "We'll give you more work later" is not a
term. If later work is real, price the later work now and put it in the agreement.

### 4.5 What to do instead of discounting

| Instead of cutting the price | Cut the scope |
|---|---|
| Discount 20% | Move from 3 lanes to 2. Saves D4, saves a third of the copy work. |
| Discount 20% | Move from weekly to monthly reporting. Saves D6. |
| Discount 20% | Client supplies the list. Saves D3. |
| Discount 20% | Email only, no SMS. Saves D5. |
| Discount 20% | Halve the volume ceiling. Saves D1 and D2. |

Every row keeps the margin intact and gives the client a real choice about what they are buying.
A discount teaches a client that the first number was not the real one, and every subsequent
number will be negotiated from that assumption.

---

## 5. The audit

The standalone deliverability audit is priced differently: it is fixed-effort, and it is a
qualification tool as much as a product.

| | |
|---|---|
| Hours | 6–10, largely independent of the client's size |
| Price | `{{CURRENCY}}` `{{AUDIT_PRICE}}` |
| Floor | Total cost. It is priced to be easy to say yes to. |
| Purpose | Produces a scoped remediation plan, which is the sprint or the retainer, specified |

**Credit the audit fee against a sprint** commissioned within 30 days. It converts at a high
enough rate to be worth it, and a prospect who has read their own findings needs no convincing
about the sprint's scope — they have already seen what is broken.

---

## 6. Structural rules

**Price the sprint and the retainer separately.** A bundled price hides which part is
unprofitable, and it makes the retainer feel like something already paid for.

**Never quote a retainer without a sprint or an audit first.** Operating an estate you did not
build and have not assessed means inheriting problems you priced as if they did not exist.

**Re-score annually.** Engagements accumulate scope. A Band B engagement that has grown to four
lanes and weekly reporting is a Band C engagement being paid Band B money, and nobody noticed
because it happened one small request at a time. Re-run section 2 at each annual review.

**Recalculate `{{HOURLY_COST_RATE}}` annually.** It is the input every other number depends on,
and it is the one most often left at whatever it was when it was first guessed.

**Track actual hours against the estimates in 3.1.** They are starting points, and they will be
wrong for your delivery in ways only your own data can show. After ten engagements, replace
them.

---

## 7. Quoting worksheet

```
Client:                     {{CLIENT_NAME}}
Date:                       ____________

DRIVERS
  D1 Domain count           ____  (domains: ____)
  D2 Mailbox count          ____  (mailboxes: ____)
  D3 List size and quality  ____
  D4 Segment count          ____  (lanes: ____)
  D5 Cadence complexity     ____
  D6 Reporting depth        ____
                            ----
  Complexity score          ____     Band: ____

INPUTS
  {{HOURLY_COST_RATE}}      ____
  overhead_rate             ____
  target_margin             ____
  current utilisation       ____%   displacement factor: ____

SPRINT
  Hours (3.1)               ____
  Delivery cost             ____
  Tooling                   ____
  Overhead                  ____
  Total cost                ____
  Price                     ____     Quoted {{SPRINT_PRICE}}: ____
  Floor 1                   ____
  Floor 2                   ____
  {{FLOOR_PRICE}}           ____     Headroom: ____%

RETAINER (per month)
  Hours (3.1)               ____
  Delivery cost             ____
  Tooling                   ____
  Overhead                  ____
  Total cost                ____
  Price                     ____     Quoted {{RETAINER_PRICE}}: ____
  Floor 1                   ____
  Floor 2                   ____
  {{FLOOR_PRICE}}           ____     Headroom: ____%

CHECKS
  [ ] Quote is above the floor
  [ ] Volume ceiling {{SENDING_VOLUME_CEILING}} matches the estate the domain plan produced
  [ ] Reply capacity checked: volume x 3% is a number the client can actually answer
  [ ] Every driver above 3 is reflected in the scope document, not just in the price
  [ ] Pass-through costs excluded from the fee and stated separately
```

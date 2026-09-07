# Enrichment and ICP Scoring Specification

What gets enriched, how a contact is scored for fit, what happens below the threshold, and the
interface an enrichment provider must satisfy so providers can be swapped without touching
anything else.

Two things this specification exists to prevent:

1. **Enriching everything.** Enrichment costs money per contact and most contacts do not
   deserve it. The cheap fields decide who is worth the expensive ones.
2. **Sending to everyone who survived ingestion.** A contact who passes syntax validation is
   not a contact worth a message. Scoring is what turns a list into a target, and the
   threshold is what stops volume pressure from quietly widening the ICP.

---

## 1. Enrichment layers

Three tiers, run in order. Each tier only runs on contacts that survived the one before, which
is what keeps the cost per *usable* contact down rather than the cost per row.

### Tier 0 — derived, free

Computed from the import itself. No provider, no cost, runs on every row.

| Field | Derived from | Used for |
|---|---|---|
| `email_domain` | The address | Account keying, domain suppression |
| `email_pattern` | Local part shape (`first.last`, `flast`, `first`) | Guessing colleagues' addresses later |
| `is_role_address` | Local part against the role list | Rejection at ingestion |
| `is_free_mail` | Domain against the consumer provider list | Scoring signal, B2B fit |
| `is_disposable` | Domain against the throwaway list | Rejection at ingestion |
| `first_name`, `last_name` | Split from a full name column | Personalisation, with fallbacks |
| `employee_band` | Bucketed headcount | Segment routing |
| `country` / `jurisdiction` | Country column, or account country | Compliance gate G2 |

Tier 0 runs inside `list_pipeline.py`. It is enough on its own to reject perhaps a fifth of a
typical purchased list, before a single credit is spent.

### Tier 1 — cheap, high coverage

Account-level. One call per **domain**, not per contact — a 4,000-contact list across 1,200
companies is 1,200 calls, not 4,000. This is the single largest cost saving available.

| Field | Type | Used for | Scoring weight |
|---|---|---|---|
| `company_name` | text | Personalisation | — |
| `employee_count` | integer | Size fit, segment routing | High |
| `industry` | text | Sector fit | Medium |
| `country`, `region` | text | Geography fit, jurisdiction | High |
| `website_status` | enum | Does the company still exist? | High |
| `founded_year` | integer | Maturity signal | Low |
| `technologies` | text[] | Fit signal, where the ICP names one | Medium |
| `has_multiple_sites` | boolean | Complexity signal, where the ICP names one | Medium |

**Cache tier 1 by domain, indefinitely.** Headcount does not change weekly, and re-enriching a
domain already in the `account` table is money spent to learn what is already known. Refresh on
a schedule, not on every import.

### Tier 2 — expensive, low coverage

Person-level. Runs **only** on contacts already scoring above the threshold on tiers 0 and 1.
This ordering is the whole design.

| Field | Type | Used for | Scoring weight |
|---|---|---|---|
| `job_title_normalised` | text | Role fit | High |
| `seniority` | enum | Decision authority | High |
| `department` | text | Function fit | High |
| `linkedin_url` | text | Manual verification before a high-value send | — |
| `tenure_months` | integer | Someone new to a role is more open to change | Medium |
| `timezone` | text | Send timing. Never the sender's. | — |
| `email_deliverable` | enum | Verification result | **Gate** |

**Verification is not optional and is not a scoring input.** It is a gate. A contact that does
not verify as deliverable is not sent to, whatever it scores. An unverified list is the single
most common cause of a burned sending estate, and no fit score compensates for a 9% bounce rate.

### Order of operations

```
ingestion (tier 0)
      │  rejects role, disposable, malformed, suppressed, duplicate
      ▼
tier 1, per domain
      │  cached in `account`; one call per company
      ▼
provisional score  ──── below threshold ──► excluded pool, no tier 2 spend
      │
      │ above threshold
      ▼
tier 2, per contact
      ▼
verification gate  ──── not deliverable ──► suppressed
      │
      ▼
final score  ──── below {{ICP_SCORE_THRESHOLD}} ──► excluded pool
      │
      ▼
eligible for enrolment
```

---

## 2. The scoring rubric

A contact scores 0 to 100 across four dimensions. Fill the criteria per client from
`06-onboarding/intake-form.md` section 3; the dimensions and weights are the system's, the
criteria within them are the client's.

Every score is written to `score_run` with its per-component breakdown and the rubric version,
so "why was this contact excluded" is answerable without rerunning anything.

### Dimension A — Company fit (0–35)

| Criterion | Points | Source |
|---|---|---|
| Headcount inside the ICP band | 15 | Tier 1 |
| Headcount within 20% of the band | 8 | Tier 1 |
| Headcount well outside the band | 0 | Tier 1 |
| Industry named in the ICP | 10 | Tier 1 |
| Industry adjacent to one named | 5 | Tier 1 |
| Industry explicitly excluded | **−25** | Tier 1 |
| Geography in the target list | 10 | Tier 1 |
| Geography outside it | 0 | Tier 1 |

### Dimension B — Person fit (0–35)

| Criterion | Points | Source |
|---|---|---|
| Job title matches one named in the ICP | 20 | Tier 2 |
| Title in the right function, wrong level | 10 | Tier 2 |
| Title in an adjacent function | 5 | Tier 2 |
| Title unrelated | 0 | Tier 2 |
| Seniority owns the budget | 15 | Tier 2 |
| Seniority influences the decision | 10 | Tier 2 |
| Seniority is an end user | 3 | Tier 2 |
| Role address, not a person | **−40** | Tier 0 |

### Dimension C — Signal (0–20)

The evidence that this company has the problem, rather than merely resembling companies that do.

| Criterion | Points | Source |
|---|---|---|
| A trigger event from the intake, within 90 days | 12 | Tier 1 |
| Same trigger, 90 to 180 days | 6 | Tier 1 |
| A technology or operating signal named in the ICP | 8 | Tier 1 |
| A signal the ICP names as disqualifying | **−20** | Tier 1 |

Dimension C is the one most often left empty, and it is the one that separates a list of
plausible companies from a list of companies with the problem this week. If the client could not
answer intake 3.8, this dimension scores zero for everyone and the ICP is broader than they think.

### Dimension D — Data quality (0–10)

| Criterion | Points | Source |
|---|---|---|
| Email verified as deliverable | 5 | Tier 2 |
| Email is catch-all or risky | 1 | Tier 2 |
| Corporate domain, not consumer | 3 | Tier 0 |
| Consumer mailbox provider | 0 | Tier 0 |
| Personalisation fields present (name, title, company) | 2 | Tier 0–2 |

### Total

```
score = clamp(A + B + C + D, 0, 100)
```

Negative criteria can pull a dimension below zero; the total is clamped at 0 and 100. A single
disqualifier — an excluded industry, a role address — is weighted heavily enough to sink an
otherwise strong contact on its own. That is deliberate: those are not weak signals to be
outvoted, they are reasons not to send.

### Bands

| Score | Band | Treatment |
|---|---|---|
| 80–100 | Priority | Send first. Worth manual personalisation on the opening touch. |
| 60–79 | Standard | Standard cadence, standard copy. |
| 40–59 | Marginal | Held in the excluded pool. Re-enrich in 90 days; a role or headcount change moves them. |
| 0–39 | Excluded | Not sent to. Not deleted — the score is a judgement about now, not forever. |

**Default threshold: `{{ICP_SCORE_THRESHOLD}}` = 60.**

---

## 3. Below the threshold

**A contact below the threshold is excluded, not sent to.** This is the rule that comes under
pressure the moment a volume target is behind, and it is the one that matters most.

| Rule | Detail |
|---|---|
| Excluded contacts are **not deleted** | The score reflects what is known today. People change roles; companies change size. |
| Excluded contacts are **not suppressed** | Suppression is for people who said no, or who bounced. Not for people who did not score. |
| They sit in the excluded pool | Re-enriched and re-scored on the `{{LIST_REFRESH_CADENCE}}` schedule |
| A score change above the threshold makes them eligible | Automatically, at the next scoring run |
| Marginal contacts are re-enriched at 90 days | Below 40, at 180 |
| Contacts past `{{DATA_RETENTION_DAYS}}` are deleted, whatever they score | A retention obligation, not housekeeping |

### Why the threshold is not negotiable for volume

Sending to a 45-scoring contact costs more than it appears to.

- **It does not reply.** Below-threshold contacts reply at a fraction of the rate, so the volume
  produces no pipeline.
- **It lowers the domain's engagement rate.** The mailbox provider sees mail that nobody
  engages with, and applies that judgement to every message from the domain — including the
  ones to contacts who would have replied.
- **It complains at a higher rate.** A message to someone clearly outside the ICP reads as spam
  because, from their side, it is.
- **It is unrecoverable.** Reputation damage from a month of poorly-targeted sending takes
  longer to repair than the month took to cause.

If the volume target cannot be met above the threshold, the list is too small or the ICP is too
narrow. Both are real problems with real fixes — a broader ICP agreed with the client, a new
source, more enrichment coverage. Lowering the threshold is not one of them; it converts a list
problem into a deliverability problem, which is harder and more expensive.

---

## 4. The provider interface

Any enrichment provider must satisfy this interface. Nothing outside the adapter knows which
provider is in use, which is what makes swapping one for another a config change.

### Contract

```python
class EnrichmentProvider(Protocol):
    """An enrichment source. One adapter per provider; nothing else imports the provider's SDK."""

    name: str          # stable identifier, written to enrichment.provider
    tier: int          # 1 = account-level, 2 = person-level

    def enrich_account(self, domain: str) -> EnrichmentResult:
        """Look up a company by its email domain. Tier 1 providers must implement this."""

    def enrich_contact(self, email: str, domain: str) -> EnrichmentResult:
        """Look up a person by email address. Tier 2 providers must implement this."""

    def cost_per_call(self) -> float:
        """Credits consumed per successful lookup, for budget tracking."""


@dataclass
class EnrichmentResult:
    status: str              # 'found' | 'not_found' | 'error' | 'rate_limited'
    fields: dict[str, Any]   # canonical field names only - see the mapping table below
    confidence: float | None # 0.0 to 1.0, or None if the provider does not report it
    provider_ref: str | None # the provider's own record id, for support queries
    raw: dict[str, Any]      # the unmodified provider response
    error: str | None
    cost: float              # credits actually consumed, including on a miss
```

### Rules an adapter must follow

| # | Rule | Why |
|---|---|---|
| 1 | Return **canonical field names**, never the provider's | The scoring rubric must not know which provider produced a field |
| 2 | Never raise on a miss | `status='not_found'` is a normal outcome, not an exception. Most lookups miss. |
| 3 | Preserve `raw` unmodified | When a provider changes its schema, the raw response is the only evidence of what changed and when |
| 4 | Report cost even on a miss | Most providers charge for the attempt. A cost model that only counts hits is wrong by a wide margin. |
| 5 | Handle rate limits by returning `rate_limited` | Never sleep inside the adapter. The caller owns the retry policy. |
| 6 | Never mutate the contact record | The adapter returns data; the pipeline decides what to write |
| 7 | Be deterministic for a given input within a run | Two calls for the same domain in one run return the same answer, from cache |
| 8 | Normalise nothing beyond the field mapping | No inferring seniority from a title. That is scoring, and it belongs in the rubric where it can be versioned. |

### Canonical field mapping

Adapters translate to these names. Anything not on this list goes into `raw` and is not scored.

| Canonical | Type | Tier | Notes |
|---|---|---|---|
| `company_name` | text | 1 | |
| `employee_count` | integer | 1 | The number, not a band. Banding is the pipeline's job. |
| `industry` | text | 1 | Provider taxonomies differ; map to the client's list in the adapter |
| `country` | text | 1 | ISO 3166-1 alpha-2 |
| `region` | text | 1 | |
| `website_status` | enum | 1 | `live` \| `parked` \| `dead` |
| `founded_year` | integer | 1 | |
| `technologies` | text[] | 1 | |
| `has_multiple_sites` | boolean | 1 | |
| `job_title_normalised` | text | 2 | |
| `seniority` | enum | 2 | `c-level` \| `vp` \| `director` \| `manager` \| `individual` |
| `department` | text | 2 | |
| `linkedin_url` | text | 2 | |
| `tenure_months` | integer | 2 | |
| `timezone` | text | 2 | IANA name |
| `email_deliverable` | enum | 2 | `valid` \| `invalid` \| `catch-all` \| `risky` \| `unknown` |

### Adapter checklist

Before a new provider goes into production:

- [ ] Every canonical field the provider supplies is mapped; the rest go to `raw`
- [ ] A miss returns `status='not_found'`, never an exception
- [ ] An outage returns `status='error'` with the detail, never a partial result
- [ ] A rate limit returns `status='rate_limited'` without sleeping
- [ ] Cost is reported on hits *and* misses
- [ ] Run against 100 known-good domains and compare coverage against the incumbent
- [ ] Run against 20 domains where the answer is known by hand and compare accuracy
- [ ] Confirm the provider's terms permit the use, and that they hold a lawful basis for the
      personal data they supply
- [ ] Record the provider as a sub-processor in the estate register, and notify the client 30
      days before switching

**On the last two.** An enrichment provider supplying personal data is a sub-processor under
GDPR. The client is the controller and must be told who processes their prospects' data. A
provider that cannot say where its personal data came from is a liability that transfers to the
client, and switching to one quietly is a breach of the retainer agreement.

---

## 5. Operating it

### Budget

```
Cost per import ≈ (distinct domains × tier 1 rate)
                + (contacts above provisional threshold × tier 2 rate)
                + (contacts above provisional threshold × verification rate)
```

The second and third terms are governed by the threshold. Raising the threshold reduces spend
and raises quality at the same time, which is unusual enough to be worth stating: this is the
one lever in the system where the cheaper option is also the better one.

Track cost per **eligible** contact, never cost per row. A provider with a low per-call price
and 40% coverage is more expensive than one at twice the price with 85% coverage, and the
per-call figure is what vendors quote.

### Refresh

| Data | Refresh | Trigger |
|---|---|---|
| Tier 1, account | Every 180 days | Scheduled |
| Tier 2, person | Every 90 days for eligible contacts | Scheduled |
| Verification | Before every send to a contact not sent to in 90 days | Pre-send |
| Scoring | Every `{{LIST_REFRESH_CADENCE}}`, and on any enrichment change | Both |
| Excluded pool, marginal | 90 days | Scheduled |
| Excluded pool, low | 180 days | Scheduled |

### Rubric versioning

Every `score_run` records `rubric_version`. When the rubric changes:

1. Bump the version.
2. Re-score the whole list under the new version. Do not mix versions in one send.
3. Compare the eligible population before and after. A rubric change that moves the eligible
   count by more than about 20% is a change to the ICP, not a tuning adjustment, and the client
   needs to agree to it.
4. Keep the old scores. `score_run` is append-only, so the comparison is always available.

### Monitoring

| Question | Query against |
|---|---|
| What share of contacts are eligible? | `score_run` where `passed = true` |
| Is coverage falling? | `enrichment` where `status = 'not_found'`, by provider over time |
| What is cost per eligible contact? | `enrichment.cost_credits` over the eligible count |
| Which dimension is excluding most contacts? | `score_run.components` |
| Are excluded contacts being re-scored? | `score_run` grouped by `contact_id`, most recent |
| Did the last rubric change move the population? | `score_run` grouped by `rubric_version` |

**The one to watch is coverage.** Enrichment providers degrade quietly: coverage drifts down
over months, more contacts score low on dimension D through missing data rather than poor fit,
and the eligible population shrinks without anyone changing anything. A rising `not_found` rate
is the early signal, and it is the reason `enrichment` is append-only.

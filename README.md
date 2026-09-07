# Outbound System

A client-agnostic toolkit for building and running cold email infrastructure and managed
outbound pipelines. This repository is the internal system — templates, scripts, and
specifications — not an implementation for any single customer.

Nothing here contains client data. Every client-specific value is a placeholder registered
in [`VARIABLES.md`](VARIABLES.md).

## What this is for

A productized service with two products:

1. **Infrastructure sprint** — a fixed-scope, fixed-price build that takes a client from no
   outbound capability to a warmed, authenticated, monitored sending estate with a live cadence.
2. **Managed pipeline retainer** — ongoing list building, copy iteration, sending, and reporting
   against that estate.

Each numbered directory maps to one stage of delivering those two products.

## Directory map

| Directory | Stage | What lives here |
|---|---|---|
| `01-sales/` | Before the deal | Scope templates a prospect can sign without a call, and the pricing framework behind them |
| `02-infrastructure/` | Build week | Domain planning, DNS generation, warmup schedule, and the operational runbook |
| `03-audit/` | Diagnosis | The deliverability audit deliverable and its renderer |
| `04-cadence/` | Design | The multi-touch cadence architecture, the node-map builder, and the CRM build checklist |
| `05-copy/` | Voice | Client brain file, universal copy constraints, and the variant generation prompt |
| `06-onboarding/` | Kickoff | Intake form, and the script that turns a completed intake into a build spec |
| `07-data/` | Runtime | Postgres schema, list ingestion pipeline, and the enrichment/scoring specification |

## Typical engagement flow

```
06-onboarding/intake-form.md          client fills this
        │
        ▼
06-onboarding/intake_to_spec.py       produces the build spec + blocker list
        │
        ├──► 02-infrastructure/domain_plan.py   ──► 02-infrastructure/dns_records.py
        │            │
        │            ▼
        │    02-infrastructure/warmup-checklist.md   (2-4 weeks, runs in parallel)
        │
        ├──► 04-cadence/cadence_builder.py      ──► 04-cadence/crm-build-checklist.md
        │
        ├──► 05-copy/brain-file-template.md     ──► 05-copy/variant_prompt.md
        │
        └──► 07-data/schema.sql                 ──► 07-data/list_pipeline.py
                     │
                     ▼
              live sending, then 03-audit/ on a recurring basis
```

`03-audit/` also runs standalone: it is the diagnostic offer sold to prospects who already
have infrastructure that is underperforming.

## Requirements

- Python 3.11 or later
- PostgreSQL 14 or later (only for `07-data/`)

- Node 18 or later (only for the dashboard)

**Nothing in this repository needs a dependency to run.** Every planner in the numbered
directories is standard-library Python, and so is every API function in `api/`. Two exceptions,
both optional:

```bash
pip install -r requirements-cli.txt   # Postgres driver, only to LOAD with list_pipeline.py
npm install                           # the dashboard
```

`07-data/list_pipeline.py --dry-run` performs the full parse, validate, dedupe and suppression
pass with no database and no install at all.

## Dashboard

A Next.js app over the same planners. It is a thin layer with no logic of its own: each page
calls a Python function in `api/`, which imports the planner out of the numbered directories and
calls the same function the CLI calls. The dashboard and the command line cannot disagree.

```
app/            Next.js App Router pages
components/     UI primitives and the sidebar
lib/api.ts      typed client for the functions below
api/*.py        one Vercel serverless function per endpoint, standard library only
scripts/dev_api.py   serves those same functions locally
```

Two processes in development — Next.js proxies `/api/*` to the Python server (see
`next.config.mjs`):

```bash
npm run api     # terminal 1 — Python functions on :8787
npm run dev     # terminal 2 — dashboard on :3000
```

| Page | |
|---|---|
| `/` | Overview, the seven stages, the compliance position |
| `/tools/domain-plan` | Volume target to domain and mailbox count |
| `/tools/dns-records` | SPF, DKIM, DMARC, MX and tracking, with the client-facing explanation |
| `/tools/cadence` | Node map, lanes, interrupt branch, CRM build order |
| `/tools/audit` | Render an audit from a findings file |
| `/tools/intake` | Intake to build spec, with blockers and warnings surfaced |
| `/docs` | All fifteen templates and specifications |

| Endpoint | |
|---|---|
| `POST /api/domain-plan` · `POST /api/dns-records` · `POST /api/cadence` | the planners |
| `POST /api/audit` · `POST /api/intake` | render from a JSON document |
| `GET /api/docs` | index, or one document with `?path=` |
| `GET /api/health` | whether every tool and document loaded |

**Deployment.** Vercel builds the Next.js app and deploys each `api/*.py` as its own function.
`vercel.json` sets `includeFiles` so the numbered directories ship with those functions —
without it the app deploys but every tool reports "not bundled". **`/api/health` is the fastest
way to confirm a deployment is intact:** it loads all five planners, checks all fifteen
documents, and returns 503 naming whatever is missing.

Markdown rendered in the browser is sanitized with DOMPurify before it is inserted. The audit
and intake documents are built from user-supplied JSON, so a `client_name` of `<script>…</script>`
reaches the page; without sanitizing it would execute.

**Nothing here should be public.** The dashboard serves your pricing model — cost rates, margins,
floor-price headroom — and your scope templates. The app sets `noindex`, but that is not access
control. Put the deployment behind Vercel's deployment protection, or keep it local.

## Running the scripts

Each script is standalone and self-documenting via `--help`.

```bash
python 02-infrastructure/domain_plan.py --primary-domain example.com --monthly-volume 20000
python 02-infrastructure/dns_records.py --domain mail.example.com --esp google-workspace --verify
python 03-audit/audit_report.py --input 03-audit/sample-input.json
python 04-cadence/cadence_builder.py --segments enterprise,mid-market --channels email,sms
python 06-onboarding/intake_to_spec.py --input 06-onboarding/sample-intake.json
python 07-data/list_pipeline.py --csv leads.csv --mapping mapping.json --dry-run
```

All example domains in this repository use the IANA reserved names `example.com`,
`example.org`, and `example.net`, which exist for exactly this purpose and belong to nobody.

## Conventions

**Placeholders.** Client-specific values appear as `{{VARIABLE_NAME}}` in uppercase snake case.
Every one is registered in [`VARIABLES.md`](VARIABLES.md) with its meaning and an example value.
A template is ready to deliver when no `{{` remains in it.

Find unfilled placeholders in a working copy:

```bash
grep -rno '{{[A-Z0-9_]*}}' path/to/filled/document
```

**Compliance.** CAN-SPAM (US), GDPR + PECR (UK/EU), and CASL (Canada) are treated as build
requirements, not review items. Where the three regimes differ, the artifact branches by
jurisdiction rather than picking the loosest rule. The short version of the difference:

| | US (CAN-SPAM) | UK/EU (GDPR + PECR) | Canada (CASL) |
|---|---|---|---|
| Cold B2B email to a corporate address | Permitted | Permitted for corporate subscribers under legitimate interest, with a balancing test on file | Requires consent, express or implied |
| Implied consent window | n/a | n/a | 6 months from an inquiry; 2 years from a business relationship |
| Unsubscribe | Required, honoured within 10 business days | Required, honoured without undue delay | Required, honoured within 10 business days |
| Physical postal address in every message | Required | Required in practice as sender identification | Required |
| Sender identity | No deceptive headers or subject lines | Controller identity and purpose disclosed | Sender clearly identified with contact details valid 60 days |

The per-artifact rules live in [`05-copy/copy-rules.md`](05-copy/copy-rules.md). Nothing in
this repository is legal advice; a client's counsel signs off before first send.

**No client data.** No real company, person, product, domain, or copy sample appears anywhere
in this repository, including in sample inputs. Sample data is fictional and marked as such.

## Adding to this system

New artifacts follow three rules:

1. Anything client-specific is a `{{PLACEHOLDER}}` registered in `VARIABLES.md`.
2. Nothing assumes an industry. If a file mentions a vertical, it is a leak — generalize it.
3. Nothing is prose-only. A deliverable is either runnable or fillable.

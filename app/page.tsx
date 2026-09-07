import Link from 'next/link'
import { PageHeader } from '@/components/ui'

const TOOLS = [
  {
    href: '/tools/domain-plan',
    stage: '02 · Infrastructure',
    name: 'Domain plan',
    desc: 'Turn a monthly volume target into a domain and mailbox count, with the arithmetic shown and name suggestions to check.',
  },
  {
    href: '/tools/dns-records',
    stage: '02 · Infrastructure',
    name: 'DNS records',
    desc: 'The SPF, DKIM, DMARC, MX and tracking set for one sending domain, with a client-facing explanation of each.',
  },
  {
    href: '/tools/cadence',
    stage: '04 · Cadence',
    name: 'Cadence builder',
    desc: 'The node map, segment lanes, interrupt branch and CRM build order for your channels and cadence length.',
  },
  {
    href: '/tools/audit',
    stage: '03 · Audit',
    name: 'Audit report',
    desc: 'Render a deliverability audit from a findings file. The remediation plan is built from the findings, so it cannot drift.',
  },
  {
    href: '/tools/intake',
    stage: '06 · Onboarding',
    name: 'Intake to spec',
    desc: 'Turn a completed client intake into a build specification, with everything that blocks the build flagged.',
  },
]

const STAGES = [
  ['01', 'Sales', 'Fixed-scope sprint and retainer agreements, and the pricing framework behind them.'],
  ['02', 'Infrastructure', 'Domain planning, DNS generation, warmup schedule, and the operational runbook.'],
  ['03', 'Audit', 'The deliverability audit deliverable and its renderer.'],
  ['04', 'Cadence', 'Multi-touch architecture, the node-map builder, and the CRM build checklist.'],
  ['05', 'Copy', 'Client brain file, universal copy constraints, and the variant generation prompt.'],
  ['06', 'Onboarding', 'Intake form, and the script that turns it into a build specification.'],
  ['07', 'Data', 'Postgres schema, list ingestion pipeline, and the enrichment and scoring spec.'],
]

export default function Home() {
  return (
    <>
      <PageHeader
        title="AcquireOS"
        lede="The internal toolkit for building and running cold email infrastructure and managed outbound pipelines. Client-agnostic: every client-specific value is a placeholder, and no client data lives here."
      />

      <h2 className="text-xl font-semibold tracking-tight text-ink">Planners</h2>
      <ul className="mt-4 grid gap-4 sm:grid-cols-2">
        {TOOLS.map((t) => (
          <li key={t.href}>
            <Link
              href={t.href}
              className="group flex h-full flex-col rounded-xl border border-edge bg-paper p-5 shadow-card transition-all hover:-translate-y-px hover:border-brand-400 hover:shadow-lift"
            >
              <span className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
                {t.stage}
              </span>
              <span className="mt-1.5 text-lg font-semibold text-ink group-hover:text-brand-700">
                {t.name}
              </span>
              <span className="mt-1.5 text-sm leading-relaxed text-ink-muted">{t.desc}</span>
            </Link>
          </li>
        ))}
      </ul>

      <h2 className="mt-12 text-xl font-semibold tracking-tight text-ink">The seven stages</h2>
      <p className="mt-1 max-w-[80ch] text-sm text-ink-muted">
        Each numbered directory maps to one stage of delivering the two products: a fixed-scope
        infrastructure sprint, and a managed pipeline retainer.
      </p>
      <ol className="mt-4 overflow-hidden rounded-xl border border-edge bg-paper shadow-card">
        {STAGES.map(([n, name, desc], i) => (
          <li
            key={n}
            className={`flex gap-4 px-5 py-4 ${i > 0 ? 'border-t border-edge-soft' : ''}`}
          >
            <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-brand-50 font-mono text-xs font-bold text-brand-700">
              {n}
            </span>
            <span>
              <span className="block font-semibold text-ink">{name}</span>
              <span className="block text-sm leading-relaxed text-ink-muted">{desc}</span>
            </span>
          </li>
        ))}
      </ol>

      <h2 className="mt-12 text-xl font-semibold tracking-tight text-ink">Compliance</h2>
      <p className="mt-2 max-w-[80ch] text-base leading-relaxed text-ink-soft">
        CAN-SPAM, GDPR + PECR and CASL are build requirements here, not review items. Where the
        three regimes differ, the artifacts branch by jurisdiction rather than picking the
        loosest rule. The per-artifact rules live in{' '}
        <Link href="/docs/05-copy/copy-rules.md" className="font-medium text-brand-600 underline underline-offset-2">
          copy rules
        </Link>
        .
      </p>
      <div className="mt-4 rounded-xl border border-warn-line bg-warn-bg px-4 py-3.5 text-sm text-warn-text">
        <strong className="font-semibold">
          Canada is the one case that cannot be handled by building to the strictest reading.
        </strong>{' '}
        CASL requires a lawful basis <em>before</em> the first message, so it cannot be satisfied
        retroactively by good opt-out handling. Either the basis is recorded per contact, with its
        expiry, or Canadian contacts are excluded from the list.
      </div>

      <h2 className="mt-12 text-xl font-semibold tracking-tight text-ink">Command line</h2>
      <p className="mt-1 max-w-[80ch] text-sm text-ink-muted">
        Every planner in this app is the same code the CLI runs — imported, not reimplemented.
        Nothing here can disagree with the scripts.
      </p>
      <pre className="mt-4 overflow-x-auto rounded-xl border border-edge bg-[#fbfbfd] p-4 font-mono text-sm leading-relaxed text-ink-soft">
{`python 02-infrastructure/domain_plan.py --primary-domain example.com --monthly-volume 20000
python 02-infrastructure/dns_records.py --domain example-hq.com --esp google-workspace --verify
python 04-cadence/cadence_builder.py --segments enterprise,mid-market --channels email
python 03-audit/audit_report.py --input 03-audit/sample-input.json
python 06-onboarding/intake_to_spec.py --input 06-onboarding/sample-intake.json
python 07-data/list_pipeline.py --csv leads.csv --mapping mapping.json --dry-run`}
      </pre>
    </>
  )
}

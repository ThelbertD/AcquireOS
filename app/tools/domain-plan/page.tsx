'use client'

import { useState } from 'react'
import {
  Button, Card, Field, Input, Notice, PageHeader, Pre, Section, Stat, Table, Td, Code,
} from '@/components/ui'
import { api, ApiError, DomainPlan } from '@/lib/api'

const DEFAULTS = {
  primary_domain: 'example.com',
  monthly_volume: '20000',
  daily_ceiling: '40',
  mailboxes_per_domain: '3',
  sending_days: '22',
  headroom: '0.2',
}

export default function DomainPlanPage() {
  const [form, setForm] = useState(DEFAULTS)
  const [result, setResult] = useState<DomainPlan | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (k: keyof typeof DEFAULTS) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      setResult(await api.post<DomainPlan>('/api/domain-plan', form))
    } catch (err) {
      setResult(null)
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  const p = result?.plan

  return (
    <>
      <PageHeader
        eyebrow="02 · Infrastructure"
        title="Domain plan"
        lede="How many sending domains and mailboxes a volume target needs, and what each mailbox may send. No availability lookups — this produces a plan a human executes."
      />

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-5">
          <Field
            label="Primary domain"
            htmlFor="primary_domain"
            hint="The client's main brand domain. Never used for cold sending."
          >
            <Input id="primary_domain" value={form.primary_domain} onChange={set('primary_domain')} required />
          </Field>

          <div className="grid gap-5 sm:grid-cols-3">
            <Field label="Sends per month" htmlFor="monthly_volume">
              <Input id="monthly_volume" type="number" min={1} value={form.monthly_volume} onChange={set('monthly_volume')} required />
            </Field>
            <Field label="Daily ceiling / mailbox" htmlFor="daily_ceiling">
              <Input id="daily_ceiling" type="number" min={1} max={100} value={form.daily_ceiling} onChange={set('daily_ceiling')} />
            </Field>
            <Field label="Mailboxes / domain" htmlFor="mailboxes_per_domain">
              <Input id="mailboxes_per_domain" type="number" min={1} max={5} value={form.mailboxes_per_domain} onChange={set('mailboxes_per_domain')} />
            </Field>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Sending days per month" htmlFor="sending_days">
              <Input id="sending_days" type="number" min={1} max={31} value={form.sending_days} onChange={set('sending_days')} />
            </Field>
            <Field
              label="Headroom"
              htmlFor="headroom"
              hint="0 to 1. Spare capacity so one domain can be pulled without missing target."
            >
              <Input id="headroom" value={form.headroom} onChange={set('headroom')} />
            </Field>
          </div>

          <Button type="submit" busy={busy}>
            {busy ? 'Planning…' : 'Build the plan'}
          </Button>
        </form>
      </Card>

      {error && (
        <div className="mt-6">
          <Notice tone="bad" title="Cannot plan that">{error}</Notice>
        </div>
      )}

      {result && p && (
        <>
          <div className="mt-8 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
            <Stat label="Domains" value={p.secondary_domains} />
            <Stat label="Mailboxes" value={p.total_mailboxes} />
            <Stat label="Per day" value={p.estate_daily_capacity.toLocaleString()} />
            <Stat
              label="Utilisation"
              value={`${Math.round(p.utilisation_at_target * 100)}%`}
              tone={p.utilisation_at_target > 0.9 ? 'warn' : undefined}
            />
          </div>

          <div className="mt-4">
            {p.survives_losing_one_domain ? (
              <Notice tone="good" title="Survives losing one domain">
                Still holds target volume with one domain pulled from rotation —{' '}
                {p.degraded_daily_capacity.toLocaleString()}/day degraded.
              </Notice>
            ) : (
              <Notice tone="warn" title="Does not survive losing one domain">
                Degraded capacity is {p.degraded_daily_capacity.toLocaleString()}/day, below
                target. Add a domain, or accept that a reputation incident cuts throughput.
              </Notice>
            )}
          </div>

          <Section title="Arithmetic" hint="Shown so the recommendation can be argued with rather than taken on faith.">
            <Pre>{result.arithmetic.join('\n')}</Pre>
          </Section>

          <Section
            title="Suggested domain names"
            hint="Check availability and registration history manually. A previously-owned domain carries its previous owner's reputation, which you cannot see and cannot fix."
          >
            <Table head={['#', 'Domain', 'Rationale']}>
              {result.suggested_domains.map((s, i) => (
                <tr key={s.domain}>
                  <Td muted>{i + 1}</Td>
                  <Td><Code>{s.domain}</Code></Td>
                  <Td muted>{s.rationale}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          <Section title="Notes">
            <ul className="space-y-2.5">
              {result.notes.map((n, i) => (
                <li key={i} className="flex gap-3 text-base leading-relaxed text-ink-soft">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />
                  <span className="max-w-[80ch]">{n}</span>
                </li>
              ))}
            </ul>
          </Section>
        </>
      )}
    </>
  )
}

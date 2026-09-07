'use client'

import { useState } from 'react'
import {
  Button, Card, Checkbox, Code, Field, Input, Notice, PageHeader, Section, Table, Td,
} from '@/components/ui'
import { api, ApiError, Cadence } from '@/lib/api'

export default function CadencePage() {
  const [form, setForm] = useState({
    segments: 'enterprise, mid-market, smb',
    segment_field: '{{SEGMENT_FIELD}}',
    default_lane: '',
    length: '8',
    sms: false,
    sms_consent_confirmed: false,
  })
  const [result, setResult] = useState<Cadence | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      setResult(
        await api.post<Cadence>('/api/cadence', {
          segments: form.segments,
          segment_field: form.segment_field,
          default_lane: form.default_lane,
          length: form.length,
          channels: form.sms ? ['email', 'sms'] : ['email'],
          sms_consent_confirmed: form.sms_consent_confirmed,
        }),
      )
    } catch (err) {
      setResult(null)
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="04 · Cadence"
        title="Cadence builder"
        lede="The concrete node map for one client, plus the order to build it in a CRM. Every lane runs the same timing skeleton — only the messaging angle differs."
      />

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-5">
          <Field
            label="Segment lanes"
            htmlFor="segments"
            hint="Comma-separated. Maximum six — past that the copy volume outruns any team's ability to iterate on it."
          >
            <Input id="segments" value={form.segments} onChange={(e) => setForm({ ...form, segments: e.target.value })} required />
          </Field>

          <div className="grid gap-5 sm:grid-cols-3">
            <Field label="Segment field" htmlFor="segment_field" hint="The contact field the router reads.">
              <Input id="segment_field" value={form.segment_field} onChange={(e) => setForm({ ...form, segment_field: e.target.value })} />
            </Field>
            <Field label="Default lane" htmlFor="default_lane" hint="Catches null and unmapped values. Blank uses the last lane.">
              <Input id="default_lane" value={form.default_lane} onChange={(e) => setForm({ ...form, default_lane: e.target.value })} placeholder="last lane" />
            </Field>
            <Field label="Length in business days" htmlFor="length">
              <Input id="length" type="number" min={3} max={30} value={form.length} onChange={(e) => setForm({ ...form, length: e.target.value })} />
            </Field>
          </div>

          <Field label="Channels">
            <div className="flex flex-wrap gap-x-8 gap-y-3 pt-1">
              <Checkbox label="Email" hint="Always required." checked disabled onChange={() => {}} />
              <Checkbox
                label="SMS"
                checked={form.sms}
                onChange={(e) => setForm({ ...form, sms: e.target.checked })}
              />
              <Checkbox
                label="SMS consent basis confirmed"
                hint="Counsel has signed off on the basis for every number."
                checked={form.sms_consent_confirmed}
                disabled={!form.sms}
                onChange={(e) => setForm({ ...form, sms_consent_confirmed: e.target.checked })}
              />
            </div>
          </Field>

          <Button type="submit" busy={busy}>{busy ? 'Building…' : 'Build the node map'}</Button>
        </form>
      </Card>

      {error && (
        <div className="mt-6"><Notice tone="bad" title="Cannot build that cadence">{error}</Notice></div>
      )}

      {result && (
        <>
          <div className="mt-8 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
            {[
              ['Lanes', result.totals.lanes],
              ['Nodes per lane', result.totals.nodes_per_lane],
              ['Node instances', result.totals.main_sequence_node_instances],
              ['Copy pieces', result.totals.copy_pieces_required],
            ].map(([label, value]) => (
              <Card key={String(label)} className="px-4 py-3.5">
                <div className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</div>
                <div className="mt-1 text-2xl font-semibold tracking-tight text-ink">{value}</div>
              </Card>
            ))}
          </div>

          {result.warnings.length > 0 && (
            <div className="mt-5 space-y-3">
              {result.warnings.map((w, i) => (
                <Notice key={i} tone="warn">{w}</Notice>
              ))}
            </div>
          )}

          <Section title="Entry gates" hint="Run in order. A contact failing any gate never enters, and the reason is logged.">
            <Table head={['#', 'Gate', 'Passes when', 'On failure']}>
              {result.entry_gates.map((g) => (
                <tr key={g.id}>
                  <Td mono>{g.id}</Td>
                  <Td className="whitespace-nowrap font-medium">{g.name}</Td>
                  <Td>{g.passes}</Td>
                  <Td muted>{g.on_failure}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          <Section title="Main sequence" hint="Day offsets are business days from entry, not calendar days.">
            <Table head={['Node', 'Day', 'Channel', 'Purpose', 'Exit']}>
              {result.nodes.map((n) => (
                <tr key={n.node}>
                  <Td mono>{n.node}</Td>
                  <Td muted>{n.day}</Td>
                  <Td className="whitespace-nowrap">{n.channel}</Td>
                  <Td>{n.purpose}</Td>
                  <Td muted>{n.exit}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          {result.skipped_nodes.length > 0 && (
            <div className="mt-4">
              <Notice tone="info" title="Nodes not built">
                {result.skipped_nodes.map((s) => `${s.key} (${s.channel}): ${s.reason}`).join(' · ')}
              </Notice>
            </div>
          )}

          <Section title="Lanes">
            <Table head={['Lane', 'Slug', 'Node IDs', 'Default']}>
              {result.lanes.map((l) => (
                <tr key={l.slug}>
                  <Td className="font-medium">{l.lane}</Td>
                  <Td mono>{l.slug}</Td>
                  <Td mono muted className="text-[0.85em]">{l.node_ids.join(', ')}</Td>
                  <Td>{l.is_default ? 'yes' : ''}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          <Section
            title="Interrupt → follow-through"
            hint="Fires on an inbound reply, the required input being supplied, or a meeting booked. Never on opens. Days count from the interrupt, not from cadence entry."
          >
            <Table head={['Node', 'Day', 'Channel', 'Purpose']}>
              {result.followthrough.map((f) => (
                <tr key={f.node}>
                  <Td mono>{f.node}</Td>
                  <Td muted>{f.day}</Td>
                  <Td className="whitespace-nowrap">{f.channel}</Td>
                  <Td>{f.purpose}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          <Section title="Terminal states" hint="Every contact ends in exactly one. There is no other exit.">
            <Table head={['State', 'Entered when', 'Suppression', 'Next action']}>
              {result.terminal_states.map((s) => (
                <tr key={s.state}>
                  <Td><Code>{s.state}</Code></Td>
                  <Td>{s.entered}</Td>
                  <Td muted>{s.suppression}</Td>
                  <Td muted>{s.next}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          <Section title="CRM build order" hint="Ordered by dependency, not by importance. Do not reorder.">
            <ol className="space-y-3">
              {result.build_order.map((s) => (
                <li key={s.step} className="flex gap-3.5">
                  <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-brand-50 font-mono text-xs font-bold text-brand-700">
                    {s.step}
                  </span>
                  <span>
                    <span className="block font-semibold text-ink">{s.title}</span>
                    <span className="block max-w-[80ch] text-sm leading-relaxed text-ink-muted">{s.detail}</span>
                  </span>
                </li>
              ))}
            </ol>
          </Section>
        </>
      )}
    </>
  )
}

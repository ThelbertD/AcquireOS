'use client'

import { useEffect, useState } from 'react'
import {
  Button, Card, Checkbox, Code, Field, Input, Notice, PageHeader, Pre, Section, Select, Table, Td,
} from '@/components/ui'
import { api, ApiError, DnsRecordSet, EspProfile } from '@/lib/api'

export default function DnsRecordsPage() {
  const [esps, setEsps] = useState<EspProfile[]>([])
  const [form, setForm] = useState({
    domain: 'example-hq.com',
    esp: 'google-workspace',
    rua: '{{DMARC_RUA_ADDRESS}}',
    dkim_selector: '',
    include_tracking: true,
  })
  const [explain, setExplain] = useState(true)
  const [result, setResult] = useState<DnsRecordSet | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // The ESP list comes from dns_records.py rather than being hardcoded here, so adding a
  // provider there makes it appear in this select with no frontend change.
  useEffect(() => {
    api
      .get<{ esps: EspProfile[] }>('/api/dns-records')
      .then((d) => setEsps(d.esps))
      .catch(() => setEsps([{ value: 'generic', label: 'Generic / other provider', spf_include: '', dkim_selector: '' }]))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      setResult(await api.post<DnsRecordSet>('/api/dns-records', form))
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
        eyebrow="02 · Infrastructure"
        title="DNS records"
        lede="The full record set for one sending domain. Values in double braces are placeholders you replace before publishing."
      />

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Sending domain" htmlFor="domain">
              <Input id="domain" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} required />
            </Field>
            <Field label="Email service provider" htmlFor="esp">
              <Select id="esp" value={form.esp} onChange={(e) => setForm({ ...form, esp: e.target.value })}>
                {esps.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="DMARC report address" htmlFor="rua" hint="Must be a real mailbox that someone reads weekly.">
              <Input id="rua" value={form.rua} onChange={(e) => setForm({ ...form, rua: e.target.value })} />
            </Field>
            <Field label="DKIM selector" htmlFor="dkim_selector" hint="Leave blank for the provider default.">
              <Input id="dkim_selector" value={form.dkim_selector} onChange={(e) => setForm({ ...form, dkim_selector: e.target.value })} placeholder="provider default" />
            </Field>
          </div>

          <div className="flex flex-wrap gap-x-8 gap-y-3">
            <Checkbox
              label="Include tracking CNAME"
              hint="Only if tracking is actually in use."
              checked={form.include_tracking}
              onChange={(e) => setForm({ ...form, include_tracking: e.target.checked })}
            />
            <Checkbox
              label="Include the plain-English explanation"
              hint="Suitable to send to a client as-is."
              checked={explain}
              onChange={(e) => setExplain(e.target.checked)}
            />
          </div>

          <Button type="submit" busy={busy}>{busy ? 'Generating…' : 'Generate records'}</Button>
        </form>
      </Card>

      {error && (
        <div className="mt-6"><Notice tone="bad" title="Cannot generate records">{error}</Notice></div>
      )}

      {result && (
        <>
          <Section title="Records" hint={`${result.domain} · ${result.esp_label}`}>
            <Table head={['Type', 'Host', 'TTL', 'Value', 'Purpose']}>
              {result.records.map((r, i) => (
                <tr key={i}>
                  <Td mono>{r.type}</Td>
                  <Td mono>{r.host}</Td>
                  <Td muted>{r.ttl}</Td>
                  <Td mono className="min-w-[280px] break-all">{r.value}</Td>
                  <Td muted className="whitespace-nowrap">{r.purpose}</Td>
                </tr>
              ))}
            </Table>
          </Section>

          <div className="mt-5">
            <Notice tone="warn" title="DKIM key">
              {result.dkim_note} Publish every other record first, then generate the key and
              publish it last — activating signing before the record resolves fails DKIM on every
              message sent in the gap.
            </Notice>
          </div>

          <Section title="Order of operations">
            <ol className="max-w-[80ch] list-decimal space-y-2 pl-6 text-base leading-relaxed text-ink-soft marker:text-ink-faint">
              <li>Publish MX, SPF and DMARC.</li>
              <li>Wait for propagation and confirm with the checks below.</li>
              <li>Generate the DKIM key, publish it, <em>then</em> activate signing.</li>
              <li>Publish the tracking CNAME only if tracking will be used.</li>
              <li>
                Send one message to a seed address and read the raw headers. All three of{' '}
                <Code>spf=pass</Code>, <Code>dkim=pass</Code> and <Code>dmarc=pass</Code> must
                appear before any warmup traffic starts.
              </li>
            </ol>
          </Section>

          <Section title="Verification">
            <Pre>{result.records.map((r) => `# ${r.purpose}\n${r.check}`).join('\n\n')}</Pre>
          </Section>

          {explain && (
            <Section title="What these records do" hint="Suitable to send to a client as-is.">
              <div className="space-y-5">
                {result.records.map((r, i) => (
                  <Card key={i} className="p-5">
                    <div className="text-sm font-semibold text-ink">
                      {i + 1}. {r.purpose}{' '}
                      <span className="font-normal text-ink-muted">
                        — {r.type} on <Code>{r.fqdn}</Code>
                      </span>
                    </div>
                    <p className="mt-2 max-w-[80ch] text-base leading-relaxed text-ink-soft">
                      {r.explanation}
                    </p>
                  </Card>
                ))}
                <Card className="p-5">
                  <div className="text-sm font-semibold text-ink">Why DMARC starts at p=none</div>
                  <p className="mt-2 max-w-[80ch] text-base leading-relaxed text-ink-soft">
                    A policy of reject tells the world to throw away any mail from this domain
                    that fails authentication. That is the destination, not the starting point.
                    Published on day one it silently discards legitimate mail from any system
                    nobody remembered to authorise, with no bounce. Publish p=none, read the
                    aggregate reports for two to four weeks until every legitimate source is
                    accounted for, move to quarantine, watch for two more weeks, then reject.
                  </p>
                </Card>
              </div>
            </Section>
          )}

          <div className="mt-8">
            <Notice tone="info" title="Not included">{result.optional_note}</Notice>
          </div>
        </>
      )}
    </>
  )
}

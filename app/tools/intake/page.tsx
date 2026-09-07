'use client'

import { useEffect, useState } from 'react'
import Markdown from '@/components/Markdown'
import { Button, Card, Field, Notice, PageHeader, Section, Table, Td, Textarea, Code } from '@/components/ui'
import { api, ApiError, IntakeResult } from '@/lib/api'

export default function IntakePage() {
  const [payload, setPayload] = useState('')
  const [loadingSample, setLoadingSample] = useState(true)
  const [result, setResult] = useState<IntakeResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .get<{ sample: string }>('/api/intake')
      .then((d) => setPayload(d.sample))
      .catch(() => setPayload('{\n  \n}'))
      .finally(() => setLoadingSample(false))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    let parsed: unknown
    try {
      parsed = JSON.parse(payload)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Not valid JSON.')
      setBusy(false)
      return
    }
    try {
      setResult(await api.post<IntakeResult>('/api/intake', parsed))
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
        eyebrow="06 · Onboarding"
        title="Intake to spec"
        lede="Turn a completed client intake into a build specification: the domain plan, the cadence node map, the CRM build order, and everything missing or ambiguous that blocks the build."
      />

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-5">
          <Field
            label="Intake JSON"
            htmlFor="payload"
            hint="Prefilled with 06-onboarding/sample-intake.json. Mirrors the sections of intake-form.md."
          >
            <Textarea
              id="payload"
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              rows={18}
              disabled={loadingSample}
              placeholder={loadingSample ? 'Loading the sample…' : ''}
            />
          </Field>
          <Button type="submit" busy={busy} disabled={loadingSample}>
            {busy ? 'Building…' : 'Build the specification'}
          </Button>
        </form>
      </Card>

      {error && (
        <div className="mt-6"><Notice tone="bad" title="Cannot build from this input">{error}</Notice></div>
      )}

      {result && (
        <>
          <div className="mt-6 space-y-3">
            {result.blockers.length > 0 ? (
              <Notice tone="bad" title={`${result.blockers.length} blocker(s)`}>
                The build does not start until these are resolved. Each needs an answer only the
                client can give.
              </Notice>
            ) : (
              <Notice tone="good" title="No blockers">
                Every required input is present and no compliance gate is unsatisfied.
              </Notice>
            )}
            {result.warnings.length > 0 && (
              <Notice tone="warn" title={`${result.warnings.length} warning(s)`}>
                These do not stop the build, but they change it.
              </Notice>
            )}
          </div>

          {result.blockers.length > 0 && (
            <Section title="Blockers">
              <Table head={['#', 'Section', 'Issue', 'Why it blocks']}>
                {result.blockers.map((b, i) => (
                  <tr key={i}>
                    <Td muted>{i + 1}</Td>
                    <Td className="whitespace-nowrap font-medium">{b.section}</Td>
                    <Td>{b.issue}</Td>
                    <Td muted>{b.why}</Td>
                  </tr>
                ))}
              </Table>
            </Section>
          )}

          {result.warnings.length > 0 && (
            <Section title="Warnings">
              <Table head={['#', 'Section', 'Issue', 'What it means']}>
                {result.warnings.map((w, i) => (
                  <tr key={i}>
                    <Td muted>{i + 1}</Td>
                    <Td className="whitespace-nowrap font-medium">{w.section}</Td>
                    <Td>{w.issue}</Td>
                    <Td muted>{w.why}</Td>
                  </tr>
                ))}
              </Table>
            </Section>
          )}

          {Object.keys(result.resolved_variables).length > 0 && (
            <Section
              title="Resolved variables"
              hint="Values from this intake mapped onto the placeholders in VARIABLES.md. Anything not listed is still unresolved and must be filled by hand."
            >
              <Table head={['Variable', 'Value']}>
                {Object.entries(result.resolved_variables)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([k, v]) => (
                    <tr key={k}>
                      <Td className="whitespace-nowrap"><Code>{`{{${k}}}`}</Code></Td>
                      <Td>{v}</Td>
                    </tr>
                  ))}
              </Table>
            </Section>
          )}

          <Section title="Full specification">
            <Card className="p-6 sm:p-8">
              <Markdown source={result.markdown} />
            </Card>
          </Section>
        </>
      )}
    </>
  )
}

'use client'

import { useEffect, useState } from 'react'
import Markdown from '@/components/Markdown'
import { Button, Card, Field, Notice, PageHeader, Textarea } from '@/components/ui'
import { api, ApiError, AuditResult } from '@/lib/api'

export default function AuditPage() {
  const [payload, setPayload] = useState('')
  const [loadingSample, setLoadingSample] = useState(true)
  const [result, setResult] = useState<AuditResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Prefill from the repo's own fixture rather than shipping a second copy in the bundle.
  useEffect(() => {
    api
      .get<{ sample: string }>('/api/audit')
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
      setResult(await api.post<AuditResult>('/api/audit', parsed))
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
        eyebrow="03 · Audit"
        title="Audit report"
        lede="Render a deliverability audit from a findings file. Missing sections render as not assessed rather than being silently dropped, and the remediation list is built from the findings so the plan cannot drift out of step with them."
      />

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-5">
          <Field
            label="Findings JSON"
            htmlFor="payload"
            hint="Prefilled with 03-audit/sample-input.json. Replace it with your own."
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
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" busy={busy} disabled={loadingSample}>
              {busy ? 'Rendering…' : 'Render the report'}
            </Button>
            <span className="text-xs text-ink-muted">
              {payload ? `${payload.length.toLocaleString()} characters` : ''}
            </span>
          </div>
        </form>
      </Card>

      {error && (
        <div className="mt-6"><Notice tone="bad" title="Cannot render this input">{error}</Notice></div>
      )}

      {result && result.warnings.length > 0 && (
        <div className="mt-6">
          <Notice tone="warn" title={`${result.warnings.length} issue(s) in the input`}>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </Notice>
        </div>
      )}

      {result && (
        <Card className="mt-6 p-6 sm:p-8">
          <Markdown source={result.markdown} />
        </Card>
      )}
    </>
  )
}

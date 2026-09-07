'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { Notice, PageHeader } from '@/components/ui'
import { api, ApiError, DocIndex } from '@/lib/api'

export default function DocsIndexPage() {
  const [index, setIndex] = useState<DocIndex | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get<DocIndex>('/api/docs')
      .then(setIndex)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not load the index.'))
  }, [])

  return (
    <>
      <PageHeader
        title="Documents"
        lede="The fifteen fillable templates and specifications. Every client-specific value is a placeholder registered in VARIABLES.md — a template is ready to deliver when no double braces remain in it."
      />

      {error && <Notice tone="bad" title="Could not load the documents">{error}</Notice>}

      {!index && !error && (
        <div className="space-y-6">
          {[0, 1, 2].map((i) => (
            <div key={i}>
              <div className="h-5 w-40 animate-pulse rounded bg-edge-soft" />
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="h-20 animate-pulse rounded-xl bg-edge-soft" />
                <div className="h-20 animate-pulse rounded-xl bg-edge-soft" />
              </div>
            </div>
          ))}
        </div>
      )}

      {index && (
        <div className="space-y-9">
          {index.groups.map((g) => (
            <section key={g.group}>
              <h2 className="text-sm font-bold uppercase tracking-[0.1em] text-ink-faint">
                {g.group}
              </h2>
              <ul className="mt-3 grid gap-3 sm:grid-cols-2">
                {g.documents.map((d) => (
                  <li key={d.path}>
                    {d.available ? (
                      <Link
                        href={`/docs/${d.path}`}
                        className="group flex h-full flex-col rounded-xl border border-edge bg-paper p-4 shadow-card transition-all hover:-translate-y-px hover:border-brand-400 hover:shadow-lift"
                      >
                        <span className="font-semibold text-ink group-hover:text-brand-700">
                          {d.title}
                        </span>
                        <span className="mt-1 font-mono text-xs text-ink-faint">{d.path}</span>
                      </Link>
                    ) : (
                      <div className="flex h-full flex-col rounded-xl border border-dashed border-edge bg-paper/60 p-4">
                        <span className="font-semibold text-ink-faint">{d.title}</span>
                        <span className="mt-1 font-mono text-xs text-ink-faint">{d.path}</span>
                        <span className="mt-1 text-xs text-bad-text">not bundled</span>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </>
  )
}

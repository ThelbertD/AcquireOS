'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import Markdown from '@/components/Markdown'
import { Card, Notice } from '@/components/ui'
import { api, ApiError, Doc } from '@/lib/api'

export default function DocPage() {
  const params = useParams<{ slug: string[] }>()
  const path = Array.isArray(params.slug) ? params.slug.join('/') : ''

  const [doc, setDoc] = useState<Doc | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!path) return
    setDoc(null)
    setError('')
    api
      .get<Doc>(`/api/docs?path=${encodeURIComponent(path)}`)
      .then(setDoc)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : 'Could not load this document.'),
      )
  }, [path])

  return (
    <>
      <nav className="mb-5 text-sm">
        <Link href="/docs" className="font-medium text-brand-600 hover:underline">
          ← All documents
        </Link>
        <span className="mx-2 text-ink-faint">·</span>
        <span className="font-mono text-xs text-ink-muted">{path}</span>
      </nav>

      {error && (
        <Notice tone="bad" title="Could not load this document">
          {error}
        </Notice>
      )}

      {!doc && !error && (
        <div className="space-y-3">
          <div className="h-9 w-2/5 animate-pulse rounded bg-edge-soft" />
          <div className="h-4 w-full animate-pulse rounded bg-edge-soft" />
          <div className="h-4 w-11/12 animate-pulse rounded bg-edge-soft" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-edge-soft" />
        </div>
      )}

      {doc && (
        <Card className="p-6 sm:p-9">
          <Markdown source={doc.markdown} />
        </Card>
      )}
    </>
  )
}

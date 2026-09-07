'use client'

import { useEffect, useState } from 'react'

/**
 * Renders markdown coming back from the API.
 *
 * Sanitized, and not optionally. The audit and intake documents are built from user-supplied
 * JSON — a client_name of "<script>…</script>" reaches this component — so the HTML is passed
 * through DOMPurify before it goes anywhere near dangerouslySetInnerHTML.
 *
 * Both libraries are imported dynamically: they are only needed once a result exists, and
 * DOMPurify expects a DOM, which does not exist during prerender.
 */
export default function Markdown({ source }: { source: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function render() {
      try {
        const [{ marked }, purifyModule] = await Promise.all([
          import('marked'),
          import('dompurify'),
        ])
        const DOMPurify = purifyModule.default
        const parsed = await marked.parse(source, { gfm: true, breaks: false })
        const clean = DOMPurify.sanitize(parsed, {
          ADD_ATTR: ['target', 'rel'],
          FORBID_TAGS: ['style', 'form', 'input', 'button'],
          FORBID_ATTR: ['style', 'onerror', 'onload'],
        })
        if (!cancelled) setHtml(clean)
      } catch {
        if (!cancelled) setFailed(true)
      }
    }

    render()
    return () => {
      cancelled = true
    }
  }, [source])

  if (failed) {
    // Never lose the content because the renderer failed — show it as text.
    return (
      <pre className="overflow-x-auto rounded-xl border border-edge bg-[#fbfbfd] p-4 font-mono text-sm leading-relaxed text-ink-soft">
        {source}
      </pre>
    )
  }

  if (html === null) {
    return (
      <div className="space-y-2.5" aria-busy>
        <div className="h-6 w-1/3 animate-pulse rounded bg-edge-soft" />
        <div className="h-4 w-full animate-pulse rounded bg-edge-soft" />
        <div className="h-4 w-11/12 animate-pulse rounded bg-edge-soft" />
        <div className="h-4 w-4/5 animate-pulse rounded bg-edge-soft" />
      </div>
    )
  }

  return <div className="md-body" dangerouslySetInnerHTML={{ __html: html }} />
}

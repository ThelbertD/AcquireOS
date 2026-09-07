'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'

const NAV: { group: string; links: { href: string; label: string }[] }[] = [
  {
    group: 'Planners',
    links: [
      { href: '/', label: 'Overview' },
      { href: '/tools/domain-plan', label: 'Domain plan' },
      { href: '/tools/dns-records', label: 'DNS records' },
      { href: '/tools/cadence', label: 'Cadence builder' },
      { href: '/tools/audit', label: 'Audit report' },
      { href: '/tools/intake', label: 'Intake to spec' },
    ],
  },
  {
    group: 'Reference',
    links: [
      { href: '/docs', label: 'All documents' },
      { href: '/docs/VARIABLES.md', label: 'Variables' },
      { href: '/docs/04-cadence/cadence-spec.md', label: 'Cadence spec' },
      { href: '/docs/05-copy/copy-rules.md', label: 'Copy rules' },
      { href: '/docs/01-sales/pricing-model.md', label: 'Pricing model' },
    ],
  },
]

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3 px-2 py-1">
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[11px] bg-brand-500 text-xl font-bold text-white shadow-[0_2px_10px_rgba(91,110,245,0.35)]">
        A
      </span>
      <span className="min-w-0">
        <span className="block truncate text-xl font-bold leading-tight tracking-tight text-ink">
          AcquireOS
        </span>
        <span className="mt-0.5 block truncate text-[11.5px] font-bold uppercase tracking-[0.11em] text-brand-600">
          Outbound Pipeline OS
        </span>
      </span>
    </Link>
  )
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  return (
    <nav className="mt-6 space-y-6">
      {NAV.map(({ group, links }) => (
        <div key={group}>
          <div className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-[0.11em] text-ink-faint">
            {group}
          </div>
          <div className="space-y-0.5">
            {links.map(({ href, label }) => {
              const active = pathname === href
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={onNavigate}
                  aria-current={active ? 'page' : undefined}
                  className={`block rounded-lg px-3 py-2 text-[15px] transition-colors ${
                    active
                      ? 'bg-brand-50 font-semibold text-brand-700'
                      : 'font-medium text-ink-soft hover:bg-paper-sunk hover:text-ink'
                  }`}
                >
                  {label}
                </Link>
              )
            })}
          </div>
        </div>
      ))}
    </nav>
  )
}

export default function Sidebar() {
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Mobile bar */}
      <div className="flex items-center justify-between border-b border-edge bg-paper px-4 py-3 lg:hidden">
        <Brand />
        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Toggle navigation"
          className="rounded-lg border border-edge px-3 py-2 text-sm font-semibold text-ink-soft hover:bg-paper-sunk"
        >
          {open ? 'Close' : 'Menu'}
        </button>
      </div>
      {open && (
        <div className="border-b border-edge bg-paper px-4 pb-4 lg:hidden">
          <NavLinks onNavigate={() => setOpen(false)} />
        </div>
      )}

      {/* Desktop rail */}
      <aside className="hidden w-[264px] shrink-0 border-r border-edge bg-paper-rail px-3 py-5 lg:block">
        <div className="sticky top-5">
          <Brand />
          <NavLinks />
          <div className="mt-8 border-t border-edge-soft px-3 pt-4 text-xs leading-relaxed text-ink-faint">
            Client-agnostic. Every client-specific value is a placeholder registered in{' '}
            <Link href="/docs/VARIABLES.md" className="text-brand-600 hover:underline">
              VARIABLES.md
            </Link>
            .
          </div>
        </div>
      </aside>
    </>
  )
}

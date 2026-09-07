'use client'

import { ReactNode } from 'react'

/* ---------------------------------------------------------------- page furniture */

export function PageHeader({
  eyebrow,
  title,
  lede,
}: {
  eyebrow?: string
  title: string
  lede?: ReactNode
}) {
  return (
    <header className="mb-8">
      {eyebrow && (
        <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.1em] text-brand-600">
          {eyebrow}
        </div>
      )}
      <h1 className="text-3xl font-semibold tracking-tight text-ink">{title}</h1>
      {lede && <p className="mt-2.5 max-w-[74ch] text-lg text-ink-muted">{lede}</p>}
    </header>
  )
}

export function Section({
  title,
  hint,
  children,
}: {
  title: string
  hint?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold tracking-tight text-ink">{title}</h2>
      {hint && <p className="mt-1 max-w-[80ch] text-sm text-ink-muted">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

export function Card({
  children,
  className = '',
  as = 'div',
}: {
  children: ReactNode
  className?: string
  as?: 'div' | 'li'
}) {
  const Tag = as
  return (
    <Tag
      className={`rounded-xl border border-edge bg-paper shadow-card ${className}`}
    >
      {children}
    </Tag>
  )
}

/* ---------------------------------------------------------------- form controls */

export function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label: string
  hint?: ReactNode
  htmlFor?: string
  children: ReactNode
}) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 block text-sm font-semibold text-ink"
      >
        {label}
      </label>
      {children}
      {hint && <p className="mt-1.5 text-xs leading-snug text-ink-muted">{hint}</p>}
    </div>
  )
}

const controlClass =
  'w-full rounded-lg border border-edge bg-paper px-3 py-2 text-base text-ink ' +
  'placeholder:text-ink-faint transition-colors hover:border-edge-strong ' +
  'focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-400/30 ' +
  'disabled:cursor-not-allowed disabled:bg-paper-sunk disabled:text-ink-faint'

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${controlClass} ${props.className ?? ''}`} />
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${controlClass} ${props.className ?? ''}`} />
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      spellCheck={false}
      {...props}
      className={`${controlClass} font-mono text-sm leading-relaxed ${props.className ?? ''}`}
    />
  )
}

export function Checkbox({
  label,
  hint,
  ...props
}: { label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 select-none">
      <input
        type="checkbox"
        {...props}
        className="mt-1 h-[18px] w-[18px] shrink-0 cursor-pointer rounded border-edge-strong accent-brand-500 disabled:cursor-not-allowed"
      />
      <span>
        <span className="text-sm font-medium text-ink">{label}</span>
        {hint && <span className="block text-xs text-ink-muted">{hint}</span>}
      </span>
    </label>
  )
}

export function Button({
  children,
  variant = 'primary',
  busy = false,
  ...props
}: {
  children: ReactNode
  variant?: 'primary' | 'ghost'
  busy?: boolean
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold ' +
    'transition-colors disabled:cursor-not-allowed disabled:opacity-60'
  const styles =
    variant === 'primary'
      ? 'bg-brand-500 text-white hover:bg-brand-600'
      : 'border border-edge bg-paper text-ink-soft hover:bg-paper-sunk'
  return (
    <button {...props} disabled={props.disabled || busy} className={`${base} ${styles}`}>
      {busy && <Spinner />}
      {children}
    </button>
  )
}

export function Spinner() {
  return (
    <span
      aria-hidden
      className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}

/* ---------------------------------------------------------------- feedback */

type Tone = 'good' | 'warn' | 'bad' | 'info'

const toneClass: Record<Tone, string> = {
  good: 'border-good-line bg-good-bg text-good-text',
  warn: 'border-warn-line bg-warn-bg text-warn-text',
  bad: 'border-bad-line bg-bad-bg text-bad-text',
  info: 'border-brand-200 bg-brand-50 text-brand-700',
}

export function Notice({
  tone = 'info',
  title,
  children,
}: {
  tone?: Tone
  title?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${toneClass[tone]}`}>
      {title && <div className="font-semibold">{title}</div>}
      {children && <div className={title ? 'mt-1' : ''}>{children}</div>}
    </div>
  )
}

export function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: ReactNode
  tone?: 'bad' | 'warn'
}) {
  const valueTone =
    tone === 'bad' ? 'text-bad-text' : tone === 'warn' ? 'text-warn-text' : 'text-ink'
  return (
    <Card className="px-4 py-3.5">
      <div className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
        {label}
      </div>
      <div className={`mt-1 text-2xl font-semibold tracking-tight ${valueTone}`}>{value}</div>
    </Card>
  )
}

/* ---------------------------------------------------------------- tables */

export function Table({
  head,
  children,
}: {
  head: ReactNode[]
  children: ReactNode
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-edge bg-paper shadow-card">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {head.map((h, i) => (
              <th
                key={i}
                className="whitespace-nowrap border-b border-edge bg-paper-sunk px-3.5 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-ink-muted"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

export function Td({
  children,
  mono = false,
  muted = false,
  className = '',
}: {
  children: ReactNode
  mono?: boolean
  muted?: boolean
  className?: string
}) {
  return (
    <td
      className={`border-b border-edge-soft px-3.5 py-2.5 align-top last:border-r-0 ${
        mono ? 'font-mono text-[0.9em]' : ''
      } ${muted ? 'text-ink-muted' : 'text-ink-soft'} ${className}`}
    >
      {children}
    </td>
  )
}

export function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded bg-paper-sunk px-1.5 py-0.5 font-mono text-[0.88em] text-brand-700 ring-1 ring-inset ring-edge-soft">
      {children}
    </code>
  )
}

export function Pre({ children }: { children: ReactNode }) {
  return (
    <pre className="overflow-x-auto rounded-xl border border-edge bg-[#fbfbfd] p-4 font-mono text-sm leading-relaxed text-ink-soft">
      {children}
    </pre>
  )
}

export function EmptyHint({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-edge bg-paper/60 px-5 py-8 text-center text-sm text-ink-muted">
      {children}
    </div>
  )
}

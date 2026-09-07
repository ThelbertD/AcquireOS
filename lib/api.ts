/**
 * Client for the Python functions in /api.
 *
 * Every planner lives in the numbered directories and is called through the same function the
 * CLI calls. Nothing in the frontend reimplements any of it, so the two cannot drift.
 */

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new ApiError(
      'Could not reach the API. In development, start it with `npm run api` in a second terminal.',
      0,
    )
  }

  const text = await res.text()
  let body: unknown
  try {
    body = text ? JSON.parse(text) : {}
  } catch {
    throw new ApiError(
      res.ok ? 'The API returned something that is not JSON.' : text.slice(0, 400),
      res.status,
    )
  }

  if (!res.ok) {
    const message =
      typeof body === 'object' && body !== null && 'error' in body
        ? String((body as { error: unknown }).error)
        : `Request failed with status ${res.status}`
    throw new ApiError(message, res.status)
  }

  return body as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(payload) }),
}

/* ---------- response shapes ---------- */

export interface DomainPlan {
  inputs: Record<string, string | number>
  arithmetic: string[]
  plan: {
    secondary_domains: number
    mailboxes_per_domain: number
    total_mailboxes: number
    daily_ceiling_per_mailbox: number
    estate_daily_capacity: number
    estate_monthly_capacity: number
    utilisation_at_target: number
    survives_losing_one_domain: boolean
    degraded_daily_capacity: number
  }
  suggested_domains: { domain: string; pattern: string; rationale: string }[]
  notes: string[]
}

export interface DnsRecord {
  type: string
  host: string
  fqdn: string
  value: string
  ttl: number
  purpose: string
  explanation: string
  check: string
}

export interface DnsRecordSet {
  domain: string
  esp: string
  esp_label: string
  dkim_selector: string
  dkim_note: string
  records: DnsRecord[]
  optional_note: string
}

export interface EspProfile {
  value: string
  label: string
  spf_include: string
  dkim_selector: string
}

export interface CadenceNode {
  node: string
  key?: string
  day: number
  channel: string
  purpose: string
  entry?: string
  exit?: string
}

export interface Cadence {
  config: {
    segments: string[]
    segment_field: string
    default_lane: string
    channels: string[]
    length_days: number
    sms_consent_confirmed: boolean
  }
  entry_gates: { id: string; name: string; passes: string; on_failure: string }[]
  nodes: CadenceNode[]
  skipped_nodes: { day: number; channel: string; key: string; reason: string }[]
  lanes: { lane: string; slug: string; prefix: string; is_default: boolean; node_ids: string[] }[]
  followthrough: CadenceNode[]
  terminal_states: { state: string; entered: string; suppression: string; next: string }[]
  totals: {
    lanes: number
    nodes_per_lane: number
    main_sequence_node_instances: number
    followthrough_nodes: number
    copy_pieces_required: number
  }
  build_order: { step: number; title: string; detail: string }[]
  warnings: string[]
}

export interface AuditResult {
  markdown: string
  warnings: string[]
}

export interface Finding {
  section: string
  issue: string
  why: string
}

export interface IntakeResult {
  markdown: string
  blockers: Finding[]
  warnings: Finding[]
  resolved_variables: Record<string, string>
}

export interface DocIndex {
  groups: {
    group: string
    documents: { path: string; title: string; available: boolean }[]
  }[]
}

export interface Doc {
  path: string
  title: string
  markdown: string
}

export interface Health {
  ok: boolean
  repo_root: string
  tools: Record<string, string>
  documents_expected: number
  documents_missing: string[]
}

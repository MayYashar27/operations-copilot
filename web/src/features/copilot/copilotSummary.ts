/**
 * Manager view for Ask Copilot: a deterministic presentation layer over the
 * SAVED investigation record. It selects and formats what the backend stored
 * (structured result, pattern themes, captured tool results). It never calls
 * the AI, and it only shows tool evidence that was actually captured.
 */
import type { InvestigationRecord, QuestionResult, TraceStep } from '../../api/types'
import { firstSentences } from '../agents/managerSummary'

export interface Breakdown {
  title: string
  window: string | null
  rows: { label: string; value: number }[]
  /** Hourly buckets read better as a sparkline-style bar strip. */
  kind: 'categories' | 'timeline'
}

export interface KeyNumber {
  label: string
  value: string
  window: string | null
  /** The same measure for another window, shown as "vs …". */
  compare?: { value: string; window: string | null }
}

export interface CopilotView {
  questionType: 'causal' | 'factual'
  directAnswer: {
    /** Shown only when the saved result explicitly confirms a root cause. */
    rootCause: string | null
    isCausal: boolean
    /** "The volume was concentrated in …": derived from captured breakdowns. */
    lead: string | null
    lines: string[]
    /** One short neutral sentence, only when it matters for interpretation. */
    note: string | null
  }
  findings: string[]
  breakdowns: Breakdown[]
  numbers: KeyNumber[]
  themes: { theme: string; requestIds: number[]; confidence: string }[]
  /** Evidence items left out of the Manager view (all remain in Technical details). */
  hiddenEvidence: number
  nextSteps: string[]
  /** Saved documentation for requests, when the trace captured it. */
  requestDocs: Map<number, { subject: string | null; classification: string | null; documentation: string | null; time: string | null }>
}

/** "Why…", "what caused…", "investigate…" ask for an explanation; "how many…" asks for facts. */
export function questionType(question: string): 'causal' | 'factual' {
  const q = question.trim()
  if (/\b(why|cause[sd]?|causing|explain|investigate|what happened|reasons?|root cause)\b/i.test(q)) return 'causal'
  // "Which X drove…" / "How many…" ask for facts; "What drove…" asks for an explanation.
  if (/^(which|how many|how much|what (is|are|was|were))\b/i.test(q)) return 'factual'
  return /\b(drove|driv\w*)\b/i.test(q) ? 'causal' : 'factual'
}

const human = (s: string) => s.replaceAll('_', ' ').replace(/^\w/, (c) => c.toUpperCase())

/** "25 Aug 12:00–13:00" from a tool call's arguments. */
export function windowOf(args: Record<string, unknown>): string | null {
  const start = typeof args.start_time === 'string' ? args.start_time : typeof args.start_date === 'string' ? args.start_date : null
  const end = typeof args.end_time === 'string' ? args.end_time : typeof args.end_date === 'string' ? args.end_date : null
  if (!start) return null
  const day = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  const time = (iso: string) => (iso.length > 10 ? iso.slice(11, 16) : '')
  if (!end) return `${day(start)} ${time(start)}`.trim()
  if (start.slice(0, 10) === end.slice(0, 10)) {
    const s = time(start)
    const e = time(end)
    return s === '08:00' && e === '17:00' ? `${day(start)}, full day` : `${day(start)} ${s}–${e}`.trim()
  }
  return `${day(start)} – ${day(end)}`
}

const asRecord = (v: unknown): Record<string, unknown> | null =>
  v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null

const numericRows = (v: unknown) =>
  Object.entries(asRecord(v) ?? {})
    .filter((e): e is [string, number] => typeof e[1] === 'number')
    .map(([label, value]) => ({ label: human(label), value }))

const BREAKDOWN_FIELDS: Record<string, { field: string; title: string; kind?: Breakdown['kind'] }[]> = {
  get_transfers_by_destination: [{ field: 'transfer_destinations', title: 'Transfers by destination' }],
  get_requests_by_classification: [{ field: 'classifications', title: 'Requests by classification' }],
  get_requests_by_status: [{ field: 'statuses', title: 'Requests by status' }],
  get_requests_by_time_bucket: [{ field: 'request_counts', title: 'Requests over time', kind: 'timeline' }],
  get_classification_status_breakdown: [
    { field: 'statuses', title: 'Status' },
    { field: 'transfer_destinations', title: 'Transferred to' },
  ],
}

function evidenceFromTrace(trace: TraceStep[]): { breakdowns: Breakdown[]; numbers: KeyNumber[] } {
  const breakdowns: Breakdown[] = []
  const numbers: KeyNumber[] = []
  const seen = new Set<string>()

  for (const step of trace) {
    const key = `${step.tool}:${JSON.stringify(step.args)}`
    if (seen.has(key)) continue // the same call twice is the same evidence
    seen.add(key)
    const result = asRecord(step.result)
    if (!result) continue // only evidence that was captured in full
    const window = windowOf(step.args)

    for (const spec of BREAKDOWN_FIELDS[step.tool] ?? []) {
      const rows = numericRows(result[spec.field])
      if (rows.length === 0) continue
      const suffix = typeof result.classification === 'string' ? ` · ${human(result.classification)}` : ''
      breakdowns.push({
        title: spec.title + suffix,
        window,
        rows: spec.kind === 'timeline' ? rows : rows.sort((a, b) => b.value - a.value),
        kind: spec.kind ?? 'categories',
      })
    }

    if (step.tool === 'count_requests' && typeof result.request_count === 'number') {
      numbers.push({ label: 'Requests', value: String(result.request_count), window })
    }
    if (step.tool === 'get_average_wait_time' && typeof result.average_wait_time_minutes === 'number') {
      numbers.push({ label: 'Average wait', value: `${result.average_wait_time_minutes} min`, window })
    }
    if (step.tool === 'get_monitor_metrics' && typeof result.average_available_agents === 'number') {
      numbers.push({ label: 'Available agents (avg)', value: String(result.average_available_agents), window })
      if (typeof result.abandoned_calls_change === 'number') numbers.push({ label: 'Abandoned calls', value: String(result.abandoned_calls_change), window })
    }
  }
  return { breakdowns, numbers }
}

/** The window the agent queried most often: usually the period being investigated. */
function focusWindow(trace: TraceStep[]): string | null {
  const counts = new Map<string, number>()
  for (const step of trace) {
    const w = windowOf(step.args)
    if (w) counts.set(w, (counts.get(w) ?? 0) + 1)
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null
}

/** Same measure in two windows becomes one "A vs B" number; the focus window comes first. */
function pairNumbers(numbers: KeyNumber[], focus: string | null): KeyNumber[] {
  const byLabel = new Map<string, KeyNumber[]>()
  for (const n of numbers) byLabel.set(n.label, [...(byLabel.get(n.label) ?? []), n])
  return [...byLabel.values()].map((group) => {
    const [main, other] = [...group].sort((a, b) => Number(b.window === focus) - Number(a.window === focus))
    return other ? { ...main, compare: { value: other.value, window: other.window } } : main
  })
}

function requestDocsFromTrace(trace: TraceStep[]): CopilotView['requestDocs'] {
  const docs: CopilotView['requestDocs'] = new Map()
  for (const step of trace) {
    const requests = asRecord(step.result)?.requests
    if (!Array.isArray(requests)) continue
    for (const r of requests) {
      const row = asRecord(r)
      if (!row || typeof row.request_id !== 'number') continue
      docs.set(row.request_id, {
        subject: typeof row.subject === 'string' ? row.subject : null,
        classification: typeof row.classification === 'string' ? row.classification : null,
        documentation: typeof row.documentation === 'string' ? row.documentation : null,
        time: typeof row.request_time === 'string' ? row.request_time : null,
      })
    }
  }
  return docs
}

/**
 * "The volume was concentrated in login issue requests: 40 of 45 (89%)."
 * Only when one category holds at least half of a captured breakdown in the
 * investigated window; otherwise no lead is shown and the facts speak alone.
 */
export function concentrationLead(breakdowns: Breakdown[], focus: string | null): string | null {
  const candidates = breakdowns.filter((b) => b.kind === 'categories' && (b.window === focus || focus === null))
  for (const b of candidates) {
    const total = b.rows.reduce((sum, r) => sum + r.value, 0)
    const top = [...b.rows].sort((x, y) => y.value - x.value)[0]
    if (!top || total === 0 || top.value / total < 0.5) continue
    const share = `${top.value} of ${total} (${Math.round((top.value / total) * 100)}%)`
    const where = b.window ? `, ${b.window}` : ''
    if (b.title.startsWith('Requests by classification')) return `The volume was concentrated in ${top.label.toLowerCase()} requests: ${share}${where}.`
    if (b.title.startsWith('Transfers by destination')) return `Most transfers went to ${top.label.toLowerCase()}: ${share}${where}.`
  }
  return null
}

export function buildCopilotView(record: InvestigationRecord): CopilotView {
  const result = record.result as QuestionResult
  const type = questionType(record.question)
  const facts = result.observed_facts.map((f) => firstSentences(f, 1, 220))
  const evidence = evidenceFromTrace(record.trace)
  const focus = focusWindow(record.trace)

  // Explanatory questions lead with where the change came from, when the captured
  // data shows one dominant category. This states a pattern, never a cause.
  const lead = type === 'causal' ? concentrationLead(evidence.breakdowns, focus) : null
  // Skip facts that repeat the lead's own "X of Y" figure.
  const leadFigure = lead?.match(/\d+ of \d+/)?.[0]
  const directLines = facts
    .filter((f) => !leadFigure || !f.includes(leadFigure))
    .slice(0, type === 'causal' ? 2 : 3)

  const findings = result.supported_patterns
    .map((p) => firstSentences(p, 1, 200))
    .filter((p) => !directLines.includes(p))
    .slice(0, type === 'causal' ? 3 : 2)

  // Keep the one-minute read: focus-window evidence first, a few items only.
  const breakdowns = [...evidence.breakdowns]
    .sort((a, b) => Number(b.window === focus) - Number(a.window === focus))
    .slice(0, type === 'causal' ? 2 : 3)
  const numbers = pairNumbers(evidence.numbers, focus).slice(0, 3)
  const hiddenEvidence = evidence.breakdowns.length - breakdowns.length + Math.max(0, pairNumbers(evidence.numbers, focus).length - numbers.length)

  // One neutral sentence (not a banner) so a concentration is not read as a root cause.
  const note = type === 'causal' && !result.confirmed_root_cause
    ? 'These figures show where the change came from; the data does not establish why it happened.'
    : null

  return {
    questionType: type,
    directAnswer: { rootCause: result.confirmed_root_cause, isCausal: type === 'causal', lead, lines: directLines, note },
    findings,
    breakdowns,
    numbers,
    hiddenEvidence,
    themes: record.pattern_themes.slice(0, 2).map((t) => ({ theme: firstSentences(t.theme, 1, 140), requestIds: t.request_ids, confidence: t.confidence })),
    nextSteps: type === 'causal' ? [...new Set(result.recommendations.map((r) => firstSentences(r, 1, 180)))].slice(0, 2) : [],
    requestDocs: requestDocsFromTrace(record.trace),
  }
}

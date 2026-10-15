/**
 * Manager view: a deterministic presentation layer over the SAVED agent
 * investigation. It only selects, groups, shortens and formats structured
 * data already stored by the backend. It never calls the AI and never adds
 * claims: every line shown comes from a saved field (or is a clearly
 * labelled template when no deep investigation exists).
 */
import type { AgentDetail, EvidenceRequest, InvestigationFinding, RuleSignal } from '../../api/types'
import { signalSentence } from '../../lib/signals'

export type Theme = 'transfers' | 'documentation' | 'handling' | 'other'

export const THEME_LABELS: Record<Theme, string> = {
  transfers: 'Transfers and routing',
  documentation: 'Documentation quality',
  handling: 'Handling time',
  other: 'Other observations',
}

/** One key finding: possibly several overlapping source findings combined. */
export interface KeyFinding {
  theme: Theme
  headline: string
  /** Where the headline comes from, so the UI can label it honestly. */
  headlineSource: 'investigation' | 'rule' | 'ai-observation'
  /** Further AI observations on the notes (screening basis only; need validation). */
  aiNotes: string[]
  /** Measured facts (from supporting metrics or rule signals). */
  observed: string[]
  /** A possible explanation, never presented as confirmed. */
  interpretation: { text: string; source: 'investigation' | 'ai-observation' } | null
  requestIds: number[]
  /** How many saved source items this card combines (shown for transparency). */
  sources: { investigationFindings: number; ruleSignals: number; aiObservations: number }
  caveat?: string
}

export interface ManagerView {
  basis: 'investigation' | 'screening'
  findings: KeyFinding[]
  conclusion: { established: string; isTemplate: boolean }
  nextSteps: { items: string[]; isTemplate: boolean; totalAvailable: number }
}

// ---------------------------------------------------------
// Text helpers (pure, deterministic)
// ---------------------------------------------------------

/** Opening quotes minus closing quotes; apostrophes ("A04's") count as neither. */
function openQuotes(text: string): number {
  const opening = (text.match(/(^|[\s(])['"‘“](?=\S)/g) ?? []).length
  const closing = (text.match(/\S['"’”](?=[\s.,;:)!?]|$)/g) ?? []).length
  return opening - closing
}

/** Sentences, never splitting on decimals ("57.58%") or inside a quotation. */
export function sentences(text: string): string[] {
  const raw = text.trim().split(/(?<=[.!?])\s+(?=[A-Z0-9"'(‘“])/)
  const merged: string[] = []
  for (const part of raw) {
    const last = merged[merged.length - 1]
    if (last !== undefined && openQuotes(last) > 0) merged[merged.length - 1] = `${last} ${part}`
    else merged.push(part)
  }
  return merged
}

/** Up to `count` leading sentences, stopping early once `max` characters would be exceeded. */
export function firstSentences(text: string, count = 1, max = 260): string {
  const all = sentences(text)
  let out = all[0] ?? ''
  for (const next of all.slice(1, count)) {
    if (`${out} ${next}`.length > max) break
    out = `${out} ${next}`
  }
  return clip(out, max)
}

export function clip(text: string, max: number): string {
  if (text.length <= max) return text
  const cut = text.slice(0, max)
  return `${cut.slice(0, Math.max(cut.lastIndexOf(' '), max - 20)).replace(/[,;:\s]+$/, '')}…`
}

const THEME_PATTERNS: [Theme, RegExp][] = [
  ['documentation', /\b(documentation|documented|notes?|placeholder)\b/i],
  ['transfers', /\b(transfers?|transferred|routing|routed|destination|escalat\w*)\b/i],
  ['handling', /\b(handling time|handled faster|throughput)\b/i],
]

/** The theme whose keyword appears EARLIEST in the text ("Login requests were transferred ... with no documented steps" -> transfers). */
export function themeOf(text: string): Theme {
  let best: { theme: Theme; index: number } | null = null
  for (const [theme, pattern] of THEME_PATTERNS) {
    const match = pattern.exec(text)
    if (match && (best === null || match.index < best.index)) best = { theme, index: match.index }
  }
  return best?.theme ?? 'other'
}

const SIGNAL_THEME: Record<string, Theme> = {
  HIGH_TRANSFER_RATE_VS_PEERS: 'transfers',
  RISING_TRANSFER_RATE: 'transfers',
  CONCENTRATED_TRANSFERS: 'transfers',
  FASTER_HANDLING_WITH_MORE_TRANSFERS: 'transfers',
  FALLING_HANDLING_TIME: 'handling',
  RISING_HANDLING_TIME: 'handling',
  MANY_SHORT_NOTES: 'documentation',
  MISSING_DOCUMENTATION: 'documentation',
}

const ROUTING_CAVEAT = 'Routing policy was not part of this review.'

/** Interpretations that speculate are kept for the Technical view; plain readings are shown. */
const SPECULATIVE = /\b(may|might|could|possibl\w*|likely|unlikely|suggests?|perhaps|appears?|seems?|potentially)\b/i

const unique = <T>(items: T[]) => [...new Set(items)]

/** Raw field dumps ("Request 100103: classification = technical_issue, ...") are for the audit view, not managers. */
const isRawDump = (metric: string) => /^Request \d+\s*[:,]/.test(metric) || /\b[a-z_]+ = [a-z_']/.test(metric)
const signalIds = (s: RuleSignal) =>
  Object.entries(s.evidence)
    .filter(([k, v]) => k.endsWith('request_ids') && Array.isArray(v))
    .flatMap(([, v]) => (v as unknown[]).filter((x): x is number => typeof x === 'number'))

// ---------------------------------------------------------
// Builders
// ---------------------------------------------------------

function fromInvestigation(detail: AgentDetail): KeyFinding[] {
  const groups = new Map<Theme, InvestigationFinding[]>()
  for (const f of detail.investigation!.findings) {
    const theme = themeOf(f.finding)
    groups.set(theme, [...(groups.get(theme) ?? []), f])
  }
  return [...groups.entries()].map(([theme, items]) => {
    const lead = items[0]
    // One readable fact per underlying finding keeps distinct evidence without repetition.
    const observed = unique(
      items.map((f) => f.supporting_metrics.find((m) => !isRawDump(m))).filter((m): m is string => Boolean(m)),
    ).slice(0, 3)
    return {
      theme,
      headline: firstSentences(lead.finding, 1, 200),
      headlineSource: 'investigation' as const,
      aiNotes: [],
      observed,
      interpretation: (() => {
        const text = lead.interpretation ? firstSentences(lead.interpretation, 1, 220) : ''
        return text && !SPECULATIVE.test(text) ? { text, source: 'investigation' as const } : null
      })(),
      requestIds: unique(items.flatMap((f) => f.supporting_request_ids)),
      sources: { investigationFindings: items.length, ruleSignals: 0, aiObservations: 0 },
      caveat: theme === 'transfers' ? ROUTING_CAVEAT : undefined,
    }
  })
}

function fromScreening(detail: AgentDetail): KeyFinding[] {
  const themes: Theme[] = ['transfers', 'documentation', 'handling', 'other']
  return themes.flatMap((theme): KeyFinding[] => {
    const signals = detail.rule_signals.filter((s) => (SIGNAL_THEME[s.code] ?? 'other') === theme)
    const observations = detail.ai_observations.filter((o) => themeOf(o.finding) === theme)
    if (!signals.length && !observations.length) return []
    // Without a deep investigation there is no saved interpretation: rule signals
    // are the measured facts, AI observations are shown as observations to validate.
    const aiTitles = observations.map((o) => firstSentences(o.finding, 1, 180))
    return [{
      theme,
      headline: signals.length ? signalSentence(signals[0]) : aiTitles[0],
      headlineSource: signals.length ? 'rule' : 'ai-observation',
      aiNotes: (signals.length ? aiTitles : aiTitles.slice(1)).slice(0, 2),
      observed: signals.slice(1, 4).map(signalSentence),
      interpretation: null,
      requestIds: unique([...signals.flatMap(signalIds), ...observations.flatMap((o) => o.request_ids)]),
      sources: { investigationFindings: 0, ruleSignals: signals.length, aiObservations: observations.length },
      caveat: theme === 'transfers' ? ROUTING_CAVEAT : undefined,
    }]
  })
}

const STANDARD_CHECKS: Record<Theme, string> = {
  transfers: 'Spot-check the cited transfers against the routing policy before drawing any conclusion.',
  documentation: 'Review a few of the cited notes with the agent and agree what a complete note should record.',
  handling: 'Compare the agent’s case mix between periods before treating the change as a performance issue.',
  other: 'Review the cited requests to decide whether a deep investigation is warranted.',
}

export function buildManagerView(detail: AgentDetail): ManagerView {
  const inv = detail.investigation
  if (inv) {
    const recs = unique(inv.recommendations.map((r) => firstSentences(r, 1, 200)))
    return {
      basis: 'investigation',
      findings: fromInvestigation(detail).slice(0, 4),
      conclusion: {
        established: firstSentences(inv.summary, 2, 300),
        isTemplate: false,
      },
      nextSteps: { items: recs.slice(0, 3), isTemplate: false, totalAvailable: inv.recommendations.length },
    }
  }

  const findings = fromScreening(detail).slice(0, 4)
  const signals = detail.rule_signals.length
  const observations = detail.ai_observations.length
  return {
    basis: 'screening',
    findings,
    conclusion: {
      established:
        signals + observations === 0
          ? 'Screening found no signals for this agent on this shift.'
          : `Screening found ${signals} metric ${signals === 1 ? 'signal' : 'signals'} and ${observations} ${observations === 1 ? 'observation' : 'observations'} from the AI review of notes on this shift. No deep investigation has been run for this agent.`,
      isTemplate: true,
    },
    nextSteps: { items: findings.map((f) => STANDARD_CHECKS[f.theme]), isTemplate: true, totalAvailable: 0 },
  }
}

// ---------------------------------------------------------
// Why a request supports a finding (facts about the request only)
// ---------------------------------------------------------

export function requestFacts(request: EvidenceRequest, all: EvidenceRequest[]): string[] {
  const facts: string[] = []
  const human = (s: string | null) => (s ?? '').replaceAll('_', ' ')
  facts.push(request.status === 'transferred'
    ? `Transferred to ${human(request.transferred_to) || 'another team'}`
    : `${human(request.status) || 'Unknown status'} at first line`)
  if (request.classification) facts.push(`Classified as ${human(request.classification)}`)
  const words = request.documentation ? request.documentation.trim().split(/\s+/).length : 0
  facts.push(words ? `Note is ${words} ${words === 1 ? 'word' : 'words'} long` : 'No documentation')
  const norm = (request.documentation ?? '').trim().toLowerCase()
  const twins = norm ? all.filter((r) => r.request_id !== request.request_id && (r.documentation ?? '').trim().toLowerCase() === norm) : []
  if (twins.length) facts.push(`Same note text as ${twins.map((r) => `#${r.request_id}`).join(', ')}`)
  return facts
}

/** Saved items (investigation findings / AI observations / signals) that cite a request. */
export function citedBy(detail: AgentDetail, id: number): string[] {
  return [
    ...(detail.investigation?.findings.filter((f) => f.supporting_request_ids.includes(id)).map((f) => firstSentences(f.finding, 1, 140)) ?? []),
    ...detail.ai_observations.filter((o) => o.request_ids.includes(id)).map((o) => firstSentences(o.finding, 1, 140)),
    ...detail.rule_signals.filter((s) => signalIds(s).includes(id)).map(signalSentence),
  ]
}

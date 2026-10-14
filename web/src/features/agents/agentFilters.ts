import type { AgentRow } from '../../api/types'
import { compareByAttention, hasMetricSignals } from '../../lib/attention'
import { signalLabel, signalSentence } from '../../lib/signals'

export type StatusFilter = 'all' | 'investigation' | 'findings' | 'screened'
export type EvidenceFilter = 'all' | 'metric' | 'ai-only'
export type SortKey = 'attention' | 'transfer' | 'handling' | 'requests'

export const SORT_LABELS: Record<SortKey, string> = {
  attention: 'Attention',
  transfer: 'Transfer rate',
  handling: 'Handling time',
  requests: 'Requests',
}

const byMetric = (pick: (r: AgentRow) => number | null | undefined) => (a: AgentRow, b: AgentRow) =>
  (pick(b) ?? -1) - (pick(a) ?? -1) || a.agent_id.localeCompare(b.agent_id)

const SORTERS: Record<SortKey, (a: AgentRow, b: AgentRow) => number> = {
  attention: compareByAttention,
  transfer: byMetric((r) => r.metrics?.transfer_rate_percent),
  handling: byMetric((r) => r.metrics?.average_handling_time_minutes),
  requests: byMetric((r) => r.metrics?.handled_requests),
}

/** Text the search box matches: ID, signal names, AI finding titles. */
function searchable(row: AgentRow): string {
  return [
    row.agent_id,
    ...(row.rule_signals ?? []).flatMap((s) => [signalLabel(s.code), signalSentence(s)]),
    ...row.ai_finding_titles,
  ].join(' ').toLowerCase()
}

export function filterAgents(
  rows: AgentRow[],
  { query, status, evidence, sort }: { query: string; status: StatusFilter; evidence: EvidenceFilter; sort: SortKey },
): AgentRow[] {
  const needle = query.trim().toLowerCase()
  return rows
    .filter((r) => status === 'all' || r.status === status)
    .filter((r) => evidence === 'all' || (evidence === 'metric' ? hasMetricSignals(r) : !hasMetricSignals(r) && r.ai_observation_count > 0))
    .filter((r) => !needle || searchable(r).includes(needle))
    .sort(SORTERS[sort])
}

/** The single most specific reason to show under an agent's name. */
export function keyFinding(row: AgentRow): { source: 'rule' | 'ai'; text: string } | null {
  if (row.rule_signals?.length) return { source: 'rule', text: signalSentence(row.rule_signals[0]) }
  if (row.ai_finding_titles.length) return { source: 'ai', text: row.ai_finding_titles[0] }
  return null
}

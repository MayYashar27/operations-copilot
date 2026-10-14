import type { AgentRow } from '../api/types'
import { STATUS_ORDER } from './status'

export const hasMetricSignals = (row: AgentRow) => row.rule_signal_codes.length > 0

/**
 * Attention order: screening status first, then hard metric signals,
 * then the number of AI observations. Used by Overview and Agents alike,
 * so both screens always agree on "who comes first".
 */
export function compareByAttention(a: AgentRow, b: AgentRow): number {
  return (
    STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) ||
    b.rule_signal_codes.length - a.rule_signal_codes.length ||
    b.ai_observation_count - a.ai_observation_count ||
    a.agent_id.localeCompare(b.agent_id)
  )
}

/**
 * The short list for the Overview: agents recommended for deep review, plus
 * agents with deterministic metric signals. AI-only observations alone do not
 * put an agent on the Overview; they stay visible on the Agents screen.
 */
export function attentionShortlist(rows: AgentRow[], limit = 4): AgentRow[] {
  return rows
    .filter((row) => row.status === 'investigation' || hasMetricSignals(row))
    .sort(compareByAttention)
    .slice(0, limit)
}

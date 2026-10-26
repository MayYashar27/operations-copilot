import type { RuleSignal } from '../api/types'

/**
 * Plain-language names for the deterministic signal codes produced by
 * tools.py / langgraph_agent.py. Unknown codes fall back to a readable form.
 */
const SIGNAL_LABELS: Record<string, string> = {
  HIGH_TRANSFER_RATE_VS_PEERS: 'Transfer rate above peers',
  RISING_TRANSFER_RATE: 'Rising transfer rate',
  FALLING_HANDLING_TIME: 'Falling handling time',
  RISING_HANDLING_TIME: 'Rising handling time',
  FASTER_HANDLING_WITH_MORE_TRANSFERS: 'Faster handling with more transfers',
  MANY_SHORT_NOTES: 'Many short notes',
  MISSING_DOCUMENTATION: 'Missing documentation',
  CONCENTRATED_TRANSFERS: 'Transfers concentrated in one destination',
}

export function signalLabel(code: string): string {
  if (code in SIGNAL_LABELS) return SIGNAL_LABELS[code]
  const words = code.toLowerCase().replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

const num = (v: unknown, digits = 0) =>
  typeof v === 'number' ? v.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }) : '?'
const pct = (v: unknown) => `${num(v, 1)}%`
const humanize = (v: unknown) => String(v ?? '').replaceAll('_', ' ')

/**
 * The specific, evidence-based reason behind a signal, using the numbers the
 * rule itself recorded. Falls back to the label if the evidence is unexpected.
 */
export function signalSentence(signal: RuleSignal): string {
  const e = signal.evidence
  switch (signal.code) {
    case 'HIGH_TRANSFER_RATE_VS_PEERS':
      return `Transferred ${pct(e.agent_transfer_rate_percent)} of requests vs ${pct(e.peer_transfer_rate_percent)} for peers in the recent period`
    case 'RISING_TRANSFER_RATE':
      return `Transfer rate rose from ${pct(e.earlier_transfer_rate_percent)} to ${pct(e.later_transfer_rate_percent)} between periods`
    case 'FALLING_HANDLING_TIME':
      return `Average handling time fell from ${num(e.earlier_average_minutes, 1)} to ${num(e.later_average_minutes, 1)} min`
    case 'RISING_HANDLING_TIME':
      return `Average handling time rose from ${num(e.earlier_average_minutes, 1)} to ${num(e.later_average_minutes, 1)} min`
    case 'FASTER_HANDLING_WITH_MORE_TRANSFERS':
      return `Handling time changed ${num(e.handling_time_change_percent, 1)}% while transfer rate rose ${num(e.transfer_rate_change_percentage_points, 1)} pts`
    case 'MANY_SHORT_NOTES':
      return `${num(e.short_count)} of ${num(e.total_requests)} notes are under ${num(e.threshold_words)} words`
    case 'MISSING_DOCUMENTATION':
      return `${Array.isArray(e.request_ids) ? e.request_ids.length : '?'} requests have no documentation`
    case 'CONCENTRATED_TRANSFERS':
      return `${num(e.transfer_count)} of ${num(e.total_transfers)} transfers went to ${humanize(e.destination)}`
    default:
      return signalLabel(signal.code)
  }
}

/** Request IDs a signal cites, if any. */
export function signalRequestIds(signal: RuleSignal): number[] {
  return Object.entries(signal.evidence)
    .filter(([key, value]) => key.endsWith('request_ids') && Array.isArray(value))
    .flatMap(([, value]) => (value as unknown[]).filter((v): v is number => typeof v === 'number'))
}

/** Human names for the Copilot's tools, for the investigation trace. */
const TOOL_LABELS: Record<string, string> = {
  count_requests: 'Counted requests',
  get_requests_by_classification: 'Broke down requests by classification',
  get_classification_count: 'Counted one classification',
  compare_values: 'Compared with a baseline',
  get_average_wait_time: 'Measured average wait time',
  get_monitor_metrics: 'Read operational monitor',
  get_requests_by_status: 'Broke down requests by status',
  get_transfers_by_destination: 'Broke down transfers by destination',
  get_requests_by_time_bucket: 'Grouped requests into time buckets',
  get_request_details: 'Read request details',
  get_classification_status_breakdown: 'Checked status for one classification',
  get_agent_performance: 'Read agent performance',
  get_agent_daily_trends: 'Read agent daily trends',
  detect_agent_performance_signals: 'Detected agent signals',
  get_agent_request_evidence: 'Read agent request evidence',
  get_agent_comparison: 'Compared all agents',
  get_daily_series: 'Read day-by-day figures',
  detect_volume_anomalies: 'Searched for unusual hours',
  get_capacity_context: 'Compared demand and staffing with typical',
}

export function toolLabel(name: string): string {
  return TOOL_LABELS[name] ?? signalLabel(name.toUpperCase())
}

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

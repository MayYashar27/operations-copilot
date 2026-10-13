import type { ScreeningStatus } from '../api/types'

/**
 * How each screening status is presented. Wording is deliberately neutral:
 * these are review categories for a manager, not ratings of an employee.
 */
export const STATUS_META: Record<
  ScreeningStatus,
  { label: string; short: string; description: string; tone: StatusTone }
> = {
  investigation: {
    label: 'Deep review recommended',
    short: 'Deep review',
    description: 'Several signals combine into a pattern worth a closer look.',
    tone: 'review',
  },
  findings: {
    label: 'Findings to review',
    short: 'Findings',
    description: 'At least one signal or observation, not enough on its own to escalate.',
    tone: 'findings',
  },
  screened: {
    label: 'No actionable findings',
    short: 'Clear',
    description: 'Screened with no signals above the current thresholds.',
    tone: 'clear',
  },
  insufficient_data: {
    label: 'Insufficient data',
    short: 'No data',
    description: 'Too few requests on this day to screen.',
    tone: 'nodata',
  },
}

export type StatusTone = 'review' | 'findings' | 'clear' | 'nodata'

/** Display order, most in need of attention first. */
export const STATUS_ORDER: ScreeningStatus[] = ['investigation', 'findings', 'screened', 'insufficient_data']

// Full class names (not built dynamically) so Tailwind can find them.
export const TONE_CLASSES: Record<StatusTone, { dot: string; badge: string; fill: string }> = {
  review: {
    dot: 'bg-status-review',
    badge: 'bg-status-review-bg text-status-review-ink',
    fill: 'bg-status-review',
  },
  findings: {
    dot: 'bg-status-findings',
    badge: 'bg-status-findings-bg text-status-findings-ink',
    fill: 'bg-status-findings',
  },
  clear: {
    dot: 'bg-status-clear',
    badge: 'bg-status-clear-bg text-status-clear-ink',
    fill: 'bg-status-clear',
  },
  nodata: {
    dot: 'bg-status-nodata',
    badge: 'bg-status-nodata-bg text-status-nodata-ink',
    fill: 'bg-status-nodata',
  },
}

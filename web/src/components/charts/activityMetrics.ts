import type { HourlyActivity } from '../../api/types'

export type ActivityMetric = 'requests' | 'wait' | 'available'

export const ACTIVITY_METRICS: Record<
  ActivityMetric,
  {
    label: string
    unit: string
    digits: number
    form: 'bar' | 'line'
    today: (h: HourlyActivity) => number | null
    typical: (h: HourlyActivity) => number | null
  }
> = {
  requests: {
    label: 'Requests', unit: 'requests', digits: 0, form: 'bar',
    today: (h) => h.requests, typical: (h) => h.typical_requests,
  },
  wait: {
    label: 'Wait time', unit: 'min', digits: 1, form: 'line',
    today: (h) => h.average_wait_minutes, typical: (h) => h.typical_wait_minutes,
  },
  available: {
    label: 'Availability', unit: 'agents', digits: 1, form: 'line',
    today: (h) => h.average_available_agents, typical: (h) => h.typical_available_agents,
  },
}

// Mirrors api/schemas.py. If a backend schema changes, update it here too.

export type ScreeningStatus = 'screened' | 'findings' | 'investigation' | 'insufficient_data'

export interface AppConfig {
  mode: 'demo' | 'live'
  live_investigations_enabled: boolean
  disclaimer: string
}

export interface ReportListItem {
  date: string
  total_agents: number
}

export type StatusCounts = Record<ScreeningStatus, number>

export interface DayMetrics {
  total_requests: number
  average_wait_time_minutes: number | null
  abandoned_calls: number | null
  average_available_agents: number | null
}

export interface HourlyVolume {
  hour: string
  requests: number
  above_threshold: boolean
}

export interface VolumeProfile {
  average_hourly_requests: number
  threshold: number
  threshold_multiplier: number
  hours: HourlyVolume[]
}

export interface PriorityItem {
  agent_id: string
  reasons: string[]
  investigation_summary: string | null
}

export interface ReportOverview {
  date: string
  lookback_start: string | null
  total_agents: number
  status_counts: StatusCounts
  day_metrics: DayMetrics | null
  volume_profile: VolumeProfile | null
  priority_items: PriorityItem[]
}

export interface AgentMetrics {
  handled_requests: number
  scheduled_hours: number | null
  requests_per_scheduled_hour: number | null
  transferred_requests: number
  transfer_rate_percent: number | null
  first_line_resolution_rate_percent: number | null
  average_handling_time_minutes: number | null
  transfer_destinations: Record<string, number>
}

export interface AgentRow {
  agent_id: string
  status: ScreeningStatus
  investigation_reasons: string[]
  rule_signal_codes: string[]
  ai_observation_count: number
  has_investigation: boolean
  metrics: AgentMetrics | null
}

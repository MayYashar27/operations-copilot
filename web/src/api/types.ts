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

export interface HourlyActivity {
  hour: string
  requests: number
  above_threshold: boolean
  typical_requests: number | null
  average_wait_minutes: number | null
  typical_wait_minutes: number | null
  average_available_agents: number | null
  typical_available_agents: number | null
}

export interface UnusualHour {
  hour: string
  requests: number
  ratio_to_average: number
}

export interface DailyTrendItem {
  date: string
  total_requests: number
  average_wait_time_minutes: number | null
  abandoned_calls: number | null
  average_available_agents: number | null
  unusual_hours: UnusualHour[]
  hourly_requests: number[]
  has_report: boolean
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
  hourly_activity: HourlyActivity[]
  daily_trend: DailyTrendItem[]
  team_day_metrics: AgentMetrics | null
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
  rule_signals: RuleSignal[]
  ai_observation_count: number
  ai_finding_titles: string[]
  has_investigation: boolean
  metrics: AgentMetrics | null
}

// ---------------------------------------------------------
// Agent detail (GET /reports/{date}/agents/{id})
// ---------------------------------------------------------

export interface RuleSignal {
  source: 'rule'
  code: string
  category: string
  evidence: Record<string, unknown>
}

export interface AIObservation {
  source: 'ai'
  finding: string
  request_ids: number[]
  explanation: string
}

export interface DailyTrendPoint {
  date: string
  handled_requests: number
  transfer_rate_percent: number | null
  first_line_resolution_rate_percent: number | null
  average_handling_time_minutes: number | null
  requests_per_scheduled_hour: number | null
}

export interface PeriodMetrics {
  dates: string[] | null
  requests: number
  transfers: number
  transfer_rate_percent: number | null
  average_handling_time_minutes: number | null
}

export interface DocumentationScreening {
  total_requests: number
  documented_requests: number
  missing_documentation_count: number
  short_documentation_count: number
  short_documentation_percent: number | null
  short_word_threshold: number
  average_documentation_words: number | null
  repeated_text_group_count: number
}

export interface InvestigationFinding {
  finding: string
  supporting_request_ids: number[]
  supporting_metrics: string[]
  interpretation: string
}

export interface AgentInvestigation {
  summary: string
  observed_facts: string[]
  findings: InvestigationFinding[]
  hypotheses: string[]
  missing_evidence: string[]
  recommendations: string[]
}

export interface EvidenceRequest {
  request_id: number
  request_time: string
  classification: string | null
  subject: string | null
  status: string | null
  transferred_to: string | null
  handling_time_minutes: number | null
  documentation: string | null
}

export interface AgentDetail {
  agent_id: string
  date: string
  lookback_start: string | null
  status: ScreeningStatus
  investigation_reasons: string[]
  day_metrics: AgentMetrics | null
  lookback_metrics: AgentMetrics | null
  team_baseline: AgentMetrics | null
  daily_trends: DailyTrendPoint[]
  period_comparison: { earlier: PeriodMetrics; later: PeriodMetrics; peers_later: PeriodMetrics } | null
  rule_signals: RuleSignal[]
  ai_observations: AIObservation[]
  ai_observation_summary: string | null
  documentation_screening: DocumentationScreening | null
  investigation: AgentInvestigation | null
  evidence_requests: EvidenceRequest[]
  methodology: string | null
}

// ---------------------------------------------------------
// Ask Copilot
// ---------------------------------------------------------

export type InvestigationStatus = 'running' | 'completed' | 'failed'

export interface InvestigationSummary {
  id: string
  kind: 'question' | 'agent'
  origin: 'example' | 'local'
  question: string
  agent_id: string | null
  report_date: string | null
  status: InvestigationStatus
  created_at: string
}

/** InvestigationResult from langgraph_agent.py (question investigations). */
export interface QuestionResult {
  observed_facts: string[]
  supported_patterns: string[]
  hypotheses: string[]
  confirmed_root_cause: string | null
  missing_evidence: string[]
  recommendations: string[]
}

export interface TraceStep {
  tool: string
  args: Record<string, unknown>
  result: unknown
  result_preview: string | null
  result_truncated: boolean
}

export interface PatternTheme {
  theme: string
  request_ids: number[]
  evidence_count: number
  confidence: string
}

export interface InvestigationRecord extends InvestigationSummary {
  date_range: { start: string; end: string } | null
  completed_at: string | null
  model: string | null
  result: (QuestionResult | (AgentInvestigation & { agent_id: string; date: string })) | null
  pattern_themes: PatternTheme[]
  narrative: string | null
  /** Date context appended to the question before it was sent (null on older records). */
  prompt_context: string | null
  trace: TraceStep[]
  error: { type: string; message: string } | null
  /** Evidence the workflow collected before Claude started (null on older records). */
  evidence_plan?: EvidencePlan | null
  /** Non-blocking warnings about the finished answer (null on older records). */
  answer_checks?: AnswerCheck[] | null
}

export interface EvidencePlan {
  scope: Record<string, unknown>
  intents: string[]
  reasons: string[]
  executed: { tool: string; args: Record<string, unknown> }[]
}

export interface AnswerCheck {
  kind: 'unverified_number' | 'unknown_identifier' | 'scope_wording' | 'unequal_periods' | 'confirmed_root_cause' | string
  message: string
  excerpt: string
}

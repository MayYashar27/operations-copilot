"""Shapes of every API response.

These are deliberately separate from the internal report format: the API
returns only what the UI needs, and the frontend can rely on these types.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ScreeningStatus = Literal["screened", "findings", "investigation", "insufficient_data"]


class AppConfig(BaseModel):
    mode: Literal["demo", "live"]
    live_investigations_enabled: bool
    disclaimer: str


class ReportListItem(BaseModel):
    date: str
    total_agents: int


class StatusCounts(BaseModel):
    screened: int = 0
    findings: int = 0
    investigation: int = 0
    insufficient_data: int = 0


class DayMetrics(BaseModel):
    """Service-center-wide metrics for one day (deterministic, from tools.py)."""
    total_requests: int
    average_wait_time_minutes: Optional[float]
    abandoned_calls: Optional[int]
    average_available_agents: Optional[float]


class HourlyVolume(BaseModel):
    hour: str                  # "08:00-09:00"
    requests: int
    above_threshold: bool


class VolumeProfile(BaseModel):
    """Requests per working hour, from tools.detect_hourly_volume_anomalies."""
    average_hourly_requests: float
    threshold: float           # an hour at or above this counts as unusual
    threshold_multiplier: float
    hours: List[HourlyVolume]


class HourlyActivity(BaseModel):
    """One working hour of the selected day, next to its typical value."""
    hour: str
    requests: int
    above_threshold: bool
    typical_requests: Optional[float]
    average_wait_minutes: Optional[float]
    typical_wait_minutes: Optional[float]
    average_available_agents: Optional[float]
    typical_available_agents: Optional[float]


class UnusualHour(BaseModel):
    hour: str
    requests: int
    ratio_to_average: float


class DailyTrendItem(BaseModel):
    date: str
    total_requests: int
    average_wait_time_minutes: Optional[float]
    abandoned_calls: Optional[int]
    average_available_agents: Optional[float]
    unusual_hours: List[UnusualHour]
    hourly_requests: List[int] = []             # 08:00-17:00, one per hour
    has_report: bool


class PriorityItem(BaseModel):
    agent_id: str
    reasons: List[str]
    investigation_summary: Optional[str]


class ReportOverview(BaseModel):
    date: str
    lookback_start: Optional[str]
    total_agents: int
    status_counts: StatusCounts
    day_metrics: Optional[DayMetrics]
    volume_profile: Optional[VolumeProfile]
    priority_items: List[PriorityItem]
    # Added for the redesigned Overview (all deterministic):
    hourly_activity: List[HourlyActivity] = []
    daily_trend: List[DailyTrendItem] = []      # working days in the lookback window
    team_day_metrics: Optional["AgentMetrics"] = None


# ---------------------------------------------------------
# Signals: two sources, kept apart on purpose
# ---------------------------------------------------------

class RuleSignal(BaseModel):
    """Produced by deterministic threshold rules (no AI)."""
    source: Literal["rule"] = "rule"
    code: str
    category: str
    evidence: Dict[str, Any]


class AIObservation(BaseModel):
    """Produced by Claude reading the agent's documentation."""
    source: Literal["ai"] = "ai"
    finding: str
    request_ids: List[int]
    explanation: str


# ---------------------------------------------------------
# Agents
# ---------------------------------------------------------

class AgentMetrics(BaseModel):
    handled_requests: int
    scheduled_hours: Optional[float] = None
    requests_per_scheduled_hour: Optional[float] = None
    transferred_requests: int
    transfer_rate_percent: Optional[float] = None
    first_line_resolution_rate_percent: Optional[float] = None
    average_handling_time_minutes: Optional[float] = None
    transfer_destinations: Dict[str, int] = {}


class AgentRow(BaseModel):
    agent_id: str
    status: ScreeningStatus
    investigation_reasons: List[str]
    rule_signal_codes: List[str]
    rule_signals: List[RuleSignal] = []        # same signals, with their evidence numbers
    ai_observation_count: int
    ai_finding_titles: List[str] = []
    has_investigation: bool
    metrics: Optional[AgentMetrics]


class DailyTrendPoint(BaseModel):
    date: str
    handled_requests: int
    transfer_rate_percent: Optional[float]
    first_line_resolution_rate_percent: Optional[float]
    average_handling_time_minutes: Optional[float]
    requests_per_scheduled_hour: Optional[float]


class PeriodMetrics(BaseModel):
    dates: Optional[List[str]] = None
    requests: int
    transfers: int
    transfer_rate_percent: Optional[float]
    average_handling_time_minutes: Optional[float]


class PeriodComparison(BaseModel):
    """Earlier vs later half of the lookback window, used by the signal rules."""
    earlier: PeriodMetrics
    later: PeriodMetrics
    peers_later: PeriodMetrics


class DocumentationScreening(BaseModel):
    total_requests: int
    documented_requests: int
    missing_documentation_count: int
    short_documentation_count: int
    short_documentation_percent: Optional[float]
    short_word_threshold: int
    average_documentation_words: Optional[float]
    repeated_text_group_count: int


class InvestigationFinding(BaseModel):
    finding: str
    supporting_request_ids: List[int]
    supporting_metrics: List[str]
    interpretation: str


class Investigation(BaseModel):
    summary: str
    observed_facts: List[str]
    findings: List[InvestigationFinding]
    hypotheses: List[str]
    missing_evidence: List[str]
    recommendations: List[str]


class EvidenceRequest(BaseModel):
    request_id: int
    request_time: str
    classification: Optional[str]
    subject: Optional[str]
    status: Optional[str]
    transferred_to: Optional[str]
    handling_time_minutes: Optional[float]
    documentation: Optional[str]


class AgentDetail(BaseModel):
    agent_id: str
    date: str
    lookback_start: Optional[str]
    status: ScreeningStatus
    investigation_reasons: List[str]

    day_metrics: Optional[AgentMetrics]
    lookback_metrics: Optional[AgentMetrics]
    team_baseline: Optional[AgentMetrics]
    daily_trends: List[DailyTrendPoint]
    period_comparison: Optional[PeriodComparison]

    rule_signals: List[RuleSignal]
    ai_observations: List[AIObservation]
    ai_observation_summary: Optional[str]
    documentation_screening: Optional[DocumentationScreening]

    investigation: Optional[Investigation]
    # Only the requests cited somewhere above, so the UI can show evidence
    # without exposing the agent's full request history.
    evidence_requests: List[EvidenceRequest]

    methodology: Optional[str]


ReportOverview.model_rebuild()


# ---------------------------------------------------------
# Ask Copilot: persisted investigations
# ---------------------------------------------------------

InvestigationStatus = Literal["running", "completed", "failed"]
InvestigationOrigin = Literal["example", "local"]
InvestigationKind = Literal["question", "agent"]


class DateRange(BaseModel):
    start: str
    end: str


class TraceStep(BaseModel):
    """One tool call made by the agent, as safely recorded for review."""
    tool: str
    args: Dict[str, Any]
    result: Any = None              # parsed JSON when small enough
    result_preview: Optional[str] = None  # truncated text otherwise
    result_truncated: bool = False


class PatternTheme(BaseModel):
    theme: str
    request_ids: List[int]
    evidence_count: int
    confidence: str


class InvestigationError(BaseModel):
    type: str
    message: str


class InvestigationRecord(BaseModel):
    id: str
    kind: InvestigationKind = "question"
    origin: InvestigationOrigin
    question: str
    agent_id: Optional[str] = None
    report_date: Optional[str] = None     # the shift selected when it was asked
    date_range: Optional[DateRange] = None  # dates the agent actually examined
    status: InvestigationStatus
    created_at: str
    completed_at: Optional[str] = None
    model: Optional[str] = None
    # kind == "question": InvestigationResult from langgraph_agent.py
    # kind == "agent":    AgentInvestigationResult from langgraph_agent.py
    result: Optional[Dict[str, Any]] = None
    pattern_themes: List[PatternTheme] = []
    narrative: Optional[str] = None       # the agent's final prose answer, if any
    # Exact date context appended to the question before it was sent (audit).
    prompt_context: Optional[str] = None
    trace: List[TraceStep] = []
    error: Optional[InvestigationError] = None


class InvestigationSummary(BaseModel):
    id: str
    kind: InvestigationKind
    origin: InvestigationOrigin
    question: str
    agent_id: Optional[str]
    report_date: Optional[str]
    status: InvestigationStatus
    created_at: str


class NewInvestigation(BaseModel):
    question: str = Field(min_length=5, max_length=600)
    report_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

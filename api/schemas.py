"""Shapes of every API response.

These are deliberately separate from the internal report format: the API
returns only what the UI needs, and the frontend can rely on these types.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


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
    priority_items: List[PriorityItem]


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
    ai_observation_count: int
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

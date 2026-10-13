"""Builds API responses from saved reports plus deterministic metrics.

Nothing in this module calls Claude. AI output is only ever READ from saved
reports; numbers are recomputed from the synthetic dataset via tools.py.
"""

from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import ValidationError

import tools
from api import storage
from api.config import Settings
from api.schemas import (
    AgentDetail, AgentMetrics, AgentRow, AIObservation, DailyTrendPoint,
    DayMetrics, DocumentationScreening, EvidenceRequest, Investigation,
    HourlyVolume, PeriodComparison, PriorityItem, ReportListItem,
    ReportOverview, RuleSignal, StatusCounts, VolumeProfile,
)


# The one screening trigger produced by Claude rather than by a rule.
AI_TRIGGER_CODE = "SEMANTIC_DOCUMENTATION_FINDINGS"


class AgentNotFoundError(Exception):
    pass


class DataUnavailableError(Exception):
    pass


def _call_tool(fn: Callable[..., Any], *args: Any) -> Any:
    """Call a tools.py function, translating its errors for the API.

    ValueError means "no data for this agent/period" -> return None.
    Anything else means a source data file is missing or malformed.
    """
    try:
        return fn(*args)
    except ValueError:
        return None
    except (RuntimeError, KeyError, TypeError) as exc:
        raise DataUnavailableError("Source data is missing or has an unexpected format") from exc


# ---------------------------------------------------------
# Splitting a screening result into its two evidence sources
# ---------------------------------------------------------

def rule_signals(result: storage.SavedAgentResult) -> List[RuleSignal]:
    return [
        RuleSignal(code=t["code"], category=t.get("category", ""), evidence=t.get("evidence", {}))
        for t in result.findings
        if t.get("code") != AI_TRIGGER_CODE
    ]


def ai_observations(result: storage.SavedAgentResult) -> List[AIObservation]:
    findings = (result.semantic_analysis or {}).get("findings", [])
    try:
        return [AIObservation.model_validate(f) for f in findings]
    except ValidationError as exc:
        raise storage.ReportMalformedError(
            f"AI observations for {result.agent_id} have an unexpected format"
        ) from exc


def _find_agent(report: storage.SavedReport, agent_id: str) -> storage.SavedAgentResult:
    for result in report.agent_results:
        if result.agent_id == agent_id:
            return result
    raise AgentNotFoundError(f"Agent {agent_id} is not in the report for {report.date}")


def _investigation(settings: Settings, report: storage.SavedReport, agent_id: str) -> Optional[Investigation]:
    saved = storage.load_investigation(settings.reports_dir, report, agent_id)
    if saved is None:
        return None
    try:
        return Investigation.model_validate(saved)
    except ValidationError as exc:
        raise storage.ReportMalformedError(
            f"Saved investigation for {agent_id} has an unexpected format"
        ) from exc


VOLUME_THRESHOLD_MULTIPLIER = 1.5  # the default used by tools.py


def _volume_profile(date: str) -> Optional[VolumeProfile]:
    result = _call_tool(tools.detect_hourly_volume_anomalies, date, VOLUME_THRESHOLD_MULTIPLIER)
    if not result or not result.get("total_requests"):
        return None
    threshold = result["threshold"]
    return VolumeProfile(
        average_hourly_requests=result["average_hourly_volume"],
        threshold=threshold,
        threshold_multiplier=VOLUME_THRESHOLD_MULTIPLIER,
        hours=[
            HourlyVolume(hour=hour, requests=count, above_threshold=count >= threshold)
            for hour, count in result["hourly_counts"].items()
        ],
    )


def _metrics(agent_id: str, start: str, end: str) -> Optional[Dict[str, Any]]:
    return _call_tool(tools.get_agent_performance, agent_id, start, end)


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

def list_reports(settings: Settings) -> List[ReportListItem]:
    items = []
    for date in storage.list_report_dates(settings.reports_dir):
        try:
            report = storage.load_report(settings.reports_dir, date)
        except storage.ReportMalformedError:
            continue  # a broken file should not hide the others
        items.append(ReportListItem(date=date, total_agents=report.total_agents))
    return items


def get_overview(settings: Settings, date: str) -> ReportOverview:
    report = storage.load_report(settings.reports_dir, date)

    counts = StatusCounts(**Counter(r.investigation_status for r in report.agent_results))

    priority = []
    for result in report.agent_results:
        if result.investigation_status != "investigation":
            continue
        investigation = _investigation(settings, report, result.agent_id)
        priority.append(PriorityItem(
            agent_id=result.agent_id,
            reasons=result.investigation_reasons,
            investigation_summary=investigation.summary if investigation else None,
        ))

    try:
        day = _call_tool(tools.get_daily_metrics, date)
    except DataUnavailableError:
        day = None  # e.g. no monitor snapshots for this date; the rest still renders

    try:
        volume = _volume_profile(date)
    except DataUnavailableError:
        volume = None

    return ReportOverview(
        date=report.date,
        lookback_start=report.agent_results[0].lookback_start if report.agent_results else None,
        total_agents=report.total_agents,
        status_counts=counts,
        day_metrics=DayMetrics.model_validate(day) if day else None,
        volume_profile=volume,
        priority_items=priority,
    )


def list_agents(settings: Settings, date: str) -> List[AgentRow]:
    report = storage.load_report(settings.reports_dir, date)

    rows = []
    for result in report.agent_results:
        performance = _metrics(result.agent_id, date, date)
        rows.append(AgentRow(
            agent_id=result.agent_id,
            status=result.investigation_status,
            investigation_reasons=result.investigation_reasons,
            rule_signal_codes=[s.code for s in rule_signals(result)],
            ai_observation_count=len(ai_observations(result)),
            has_investigation=storage.load_investigation(settings.reports_dir, report, result.agent_id) is not None,
            metrics=AgentMetrics.model_validate(performance["agent"]) if performance else None,
        ))
    return rows


def _cited_request_ids(
    signals: List[RuleSignal],
    observations: List[AIObservation],
    investigation: Optional[Investigation],
) -> Set[int]:
    ids: Set[int] = set()
    for signal in signals:
        for key, value in signal.evidence.items():
            if key.endswith("request_ids") and isinstance(value, list):
                ids.update(v for v in value if isinstance(v, int))
    for observation in observations:
        ids.update(observation.request_ids)
    if investigation:
        for finding in investigation.findings:
            ids.update(finding.supporting_request_ids)
    return ids


def get_agent_detail(settings: Settings, date: str, agent_id: str) -> AgentDetail:
    report = storage.load_report(settings.reports_dir, date)
    result = _find_agent(report, agent_id)
    lookback_start = result.lookback_start or date

    signals = rule_signals(result)
    observations = ai_observations(result)
    investigation = _investigation(settings, report, agent_id)

    day = _metrics(agent_id, date, date)
    lookback = _metrics(agent_id, lookback_start, date)

    trends = _call_tool(tools.get_agent_daily_trends, agent_id, lookback_start, date)
    trend_points = [
        DailyTrendPoint.model_validate(point)
        for point in (trends or {}).get("daily_trends", [])
        if point.get("scheduled_hours", 0) > 0  # skip days the agent did not work
    ]

    periods = (result.performance_signals or {}).get("periods")

    screening = result.documentation_screening
    documentation = None
    if screening and screening.get("status") == "screened":
        documentation = DocumentationScreening(
            **{k: screening.get(k) for k in DocumentationScreening.model_fields if k in screening},
            repeated_text_group_count=len(screening.get("repeated_exact_text_groups", [])),
        )

    cited = _cited_request_ids(signals, observations, investigation)
    evidence = _call_tool(tools.get_agent_request_evidence, agent_id, date, date, None, None, None, 100)
    evidence_requests = [
        EvidenceRequest.model_validate(r)
        for r in (evidence or {}).get("requests", [])
        if r.get("request_id") in cited
    ]

    return AgentDetail(
        agent_id=agent_id,
        date=date,
        lookback_start=result.lookback_start,
        status=result.investigation_status,
        investigation_reasons=result.investigation_reasons,
        day_metrics=AgentMetrics.model_validate(day["agent"]) if day else None,
        lookback_metrics=AgentMetrics.model_validate(lookback["agent"]) if lookback else None,
        team_baseline=AgentMetrics.model_validate(lookback["team_baseline"]) if lookback else None,
        daily_trends=trend_points,
        period_comparison=PeriodComparison.model_validate(periods) if periods else None,
        rule_signals=signals,
        ai_observations=observations,
        ai_observation_summary=(result.semantic_analysis or {}).get("summary"),
        documentation_screening=documentation,
        investigation=investigation,
        evidence_requests=evidence_requests,
        methodology=result.methodology,
    )

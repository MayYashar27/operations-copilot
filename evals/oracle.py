"""Independent recomputation of every tool result from the raw synthetic data.

This module deliberately does NOT import tools.py or langgraph_agent.py. It
re-implements each tool's documented contract from data/*.json so that a
saved tool result can be checked against a second, independent calculation.

Two kinds of functions live here:
- replay functions (same arguments and output shape as a tool), used to
  verify saved traces and to rebuild results that were truncated in a trace;
- "truth" helpers that answer what a manager actually means (for example,
  abandoned calls per day), used where a tool's contract and the plain
  meaning of a number differ.
"""

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CLASSIFICATIONS = ("general_information", "login_issue", "payment_issue", "technical_issue")
LOW_SAMPLE = 20  # rates from fewer requests are flagged low_sample
DESTINATIONS = ("back_office", "billing", "supervisor", "technical_support")


# ---------------------------------------------------------------------------
# Raw data, indexed once
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def requests() -> tuple:
    with (DATA / "requests.json").open(encoding="utf-8") as f:
        rows = json.load(f)
    for row in rows:
        row["_t"] = datetime.fromisoformat(row["request_time"])
        row["_d"] = row["_t"].date()
    return tuple(sorted(rows, key=lambda r: r["_t"]))


@lru_cache(maxsize=None)
def snapshots() -> tuple:
    with (DATA / "monitor_snapshots.json").open(encoding="utf-8") as f:
        rows = json.load(f)
    for row in rows:
        row["_t"] = datetime.fromisoformat(row["timestamp"])
    return tuple(sorted(rows, key=lambda r: r["_t"]))


@lru_cache(maxsize=None)
def shifts() -> tuple:
    with (DATA / "agent_shifts.json").open(encoding="utf-8") as f:
        rows = json.load(f)
    for row in rows:
        row["_d"] = date.fromisoformat(row["date"])
    return tuple(rows)


@lru_cache(maxsize=None)
def request_index() -> Dict[int, dict]:
    return {r["request_id"]: r for r in requests()}


def roster() -> List[str]:
    return sorted({s["agent_id"] for s in shifts()})


def data_dates() -> List[date]:
    return sorted({r["_d"] for r in requests()})


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _d(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _window(start_time: str, end_time: str) -> List[dict]:
    """Requests with start <= request_time < end (the request tools' contract)."""
    start, end = _dt(start_time), _dt(end_time)
    return [r for r in requests() if start <= r["_t"] < end]


def _pct(part: float, whole: float) -> Optional[float]:
    return round(100 * part / whole, 2) if whole else None


def _avg(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 2) if values else None


# ---------------------------------------------------------------------------
# Replay functions: one per tool, same arguments and output shape
# ---------------------------------------------------------------------------

def count_requests(start_time, end_time):
    return {"start_time": start_time, "end_time": end_time,
            "request_count": len(_window(start_time, end_time))}


def get_requests_by_classification(start_time, end_time):
    return {"start_time": start_time, "end_time": end_time,
            "classifications": dict(Counter(r["classification"] for r in _window(start_time, end_time)))}


def get_classification_count(start_time, end_time, classification):
    rows = [r for r in _window(start_time, end_time) if r["classification"] == classification]
    return {"start_time": start_time, "end_time": end_time,
            "classification": classification, "request_count": len(rows)}


def get_average_wait_time(start_time, end_time):
    waits = [r["wait_time_minutes"] for r in _window(start_time, end_time)]
    return {"start_time": start_time, "end_time": end_time,
            "average_wait_time_minutes": _avg(waits), "request_count": len(waits)}


@lru_cache(maxsize=None)
def increments() -> Dict[str, Dict[str, int]]:
    """Calls in each snapshot's own 5-minute interval (counters reset at each day's first snapshot)."""
    out: Dict[str, Dict[str, int]] = {}
    last: Dict[date, dict] = {}
    for s in snapshots():
        prev = last.get(s["_t"].date())
        out[s["timestamp"]] = {
            "answered": s["answered_calls"] - (prev["answered_calls"] if prev else 0),
            "abandoned": s["abandoned_calls"] - (prev["abandoned_calls"] if prev else 0),
        }
        last[s["_t"].date()] = s
    return out


def get_monitor_metrics(start_time, end_time):
    """Half-open window start <= timestamp < end; each snapshot covers [t, t+5 min)."""
    start, end = _dt(start_time), _dt(end_time)
    rows = [s for s in snapshots() if start <= s["_t"] < end]
    if not rows:
        return {"start_time": start_time, "end_time": end_time, "snapshot_count": 0,
                "message": "No monitor data found for this period."}
    inc = increments()
    answered = sum(inc[s["timestamp"]]["answered"] for s in rows)
    abandoned = sum(inc[s["timestamp"]]["abandoned"] for s in rows)
    on_shift = [s["agents_on_shift"] for s in rows]
    return {
        "start_time": start_time, "end_time": end_time,
        "snapshot_count": len(rows),
        "average_monitor_wait_time_minutes": _avg([s["average_wait_time_minutes"] for s in rows]),
        "average_available_agents": _avg([s["available_agents"] for s in rows]),
        "peak_agents_on_calls": max(s["agents_on_calls"] for s in rows),
        "average_agents_on_shift": _avg(on_shift),
        "min_agents_on_shift": min(on_shift),
        "answered_calls": answered, "abandoned_calls": abandoned,
        "answered_calls_change": answered, "abandoned_calls_change": abandoned,
        "working_days": len({s["_t"].date() for s in rows}),
    }


def compare_values(current, baseline):
    current, baseline = float(current), float(baseline)
    change = current - baseline
    return {"current": current, "baseline": baseline, "absolute_change": change,
            "percentage_change": round(change / baseline * 100, 2) if baseline else None}


def get_requests_by_status(start_time, end_time):
    return {"start_time": start_time, "end_time": end_time,
            "statuses": dict(Counter(r["status"] for r in _window(start_time, end_time)))}


def get_transfers_by_destination(start_time, end_time):
    rows = [r for r in _window(start_time, end_time)
            if r["status"] == "transferred" and r["transferred_to"]]
    return {"start_time": start_time, "end_time": end_time,
            "transfer_destinations": dict(Counter(r["transferred_to"] for r in rows))}


def get_requests_by_time_bucket(start_time, end_time, bucket_minutes=5, dated_labels=None):
    """Buckets labelled HH:MM-HH:MM; over several days the label starts with the date.

    dated_labels=False reproduces the contract before the 2026-10-26 fix, when
    multi-day labels repeated each day and merged.
    """
    start, end = _dt(start_time), _dt(end_time)
    step = timedelta(minutes=int(bucket_minutes))
    counts: Dict[str, int] = {}
    if dated_labels is None:
        dated_labels = start.date() != (end - timedelta(microseconds=1)).date()

    def label(t0: datetime) -> str:
        return f"{t0:%Y-%m-%d %H:%M}-{t0 + step:%H:%M}" if dated_labels else f"{t0:%H:%M}-{t0 + step:%H:%M}"

    t = start
    while t < end:
        counts[label(t)] = 0
        t += step
    for r in requests():
        if start <= r["_t"] < end:
            index = int((r["_t"] - start).total_seconds() // 60) // int(bucket_minutes)
            counts[label(start + index * step)] += 1
    return {"start_time": start_time, "end_time": end_time,
            "bucket_minutes": bucket_minutes, "request_counts": counts}


def get_request_details(start_time, end_time, classification=None):
    rows = [r for r in _window(start_time, end_time)
            if classification is None or r["classification"] == classification]
    return {
        "start_time": start_time, "end_time": end_time,
        "classification_filter": classification, "request_count": len(rows),
        "requests": [{k: r[k] for k in ("request_id", "request_time", "subject",
                                        "classification", "documentation")} for r in rows],
    }


def get_classification_status_breakdown(start_time, end_time, classification):
    rows = [r for r in _window(start_time, end_time) if r["classification"] == classification]
    return {
        "start_time": start_time, "end_time": end_time, "classification": classification,
        "request_count": len(rows),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "transfer_destinations": dict(Counter(
            r["transferred_to"] for r in rows if r["status"] == "transferred" and r["transferred_to"])),
    }


def _summary(rows: List[dict], hours: float) -> Dict[str, Any]:
    transferred = [r for r in rows if r["status"] == "transferred"]
    resolved = [r for r in rows if r["status"] == "resolved"]
    destinations = Counter(r["transferred_to"] for r in transferred if r["transferred_to"])
    return {
        "handled_requests": len(rows),
        "low_sample": len(rows) < LOW_SAMPLE,
        "scheduled_hours": round(hours, 2),
        "requests_per_scheduled_hour": round(len(rows) / hours, 2) if hours else None,
        "transferred_requests": len(transferred),
        "transfer_rate_percent": _pct(len(transferred), len(rows)),
        "first_line_resolved_requests": len(resolved),
        "first_line_resolution_rate_percent": _pct(len(resolved), len(rows)),
        "average_handling_time_minutes": _avg([r["handling_time_minutes"] for r in rows]),
        "transfer_destinations": dict(destinations.most_common()),
    }


def get_agent_performance(agent_id, start_date, end_date):
    start, end = _d(start_date), _d(end_date)
    rows = [r for r in requests() if start <= r["_d"] <= end]
    period_shifts = [s for s in shifts() if start <= s["_d"] <= end]
    own = [s for s in period_shifts if s["agent_id"] == agent_id]
    if not own:
        raise ValueError(f"No shifts found for {agent_id} in this date range")
    team = _summary(rows, sum(s["scheduled_hours"] for s in period_shifts))
    agents = {s["agent_id"] for s in period_shifts}
    team["average_requests_per_agent"] = round(len(rows) / len(agents), 2)
    return {
        "agent_id": agent_id, "start_date": start_date, "end_date": end_date,
        "agent": _summary([r for r in rows if r["agent_id"] == agent_id],
                          sum(s["scheduled_hours"] for s in own)),
        "team_baseline": team,
    }


def get_agent_daily_trends(agent_id, start_date, end_date):
    start, end = _d(start_date), _d(end_date)
    out = []
    day = start
    while day <= end:
        rows = [r for r in requests() if r["agent_id"] == agent_id and r["_d"] == day]
        hours = sum(s["scheduled_hours"] for s in shifts() if s["agent_id"] == agent_id and s["_d"] == day)
        transferred = sum(r["status"] == "transferred" for r in rows)
        resolved = sum(r["status"] == "resolved" for r in rows)
        out.append({
            "date": day.isoformat(),
            "handled_requests": len(rows),
            "scheduled_hours": round(float(hours), 2),
            "requests_per_scheduled_hour": round(len(rows) / hours, 2) if hours else None,
            "transferred_requests": transferred,
            "transfer_rate_percent": _pct(transferred, len(rows)),
            "first_line_resolution_rate_percent": _pct(resolved, len(rows)),
            "average_handling_time_minutes": _avg([r["handling_time_minutes"] for r in rows]),
        })
        day += timedelta(days=1)
    return {"agent_id": agent_id, "start_date": start_date, "end_date": end_date, "daily_trends": out}


def _period(rows: List[dict]) -> Dict[str, Any]:
    transfers = sum(r["status"] == "transferred" for r in rows)
    return {"requests": len(rows), "transfers": transfers,
            "transfer_rate_percent": _pct(transfers, len(rows)),
            "average_handling_time_minutes": _avg([r["handling_time_minutes"] for r in rows])}


def detect_agent_performance_signals(agent_id, start_date, end_date, min_period_requests=20):
    """Earlier vs later half of the agent's scheduled working days; peers exclude the agent."""
    start, end = _d(start_date), _d(end_date)
    worked = sorted({s["_d"] for s in shifts()
                     if s["agent_id"] == agent_id and start <= s["_d"] <= end and s["scheduled_hours"] > 0})
    if len(worked) < 4:
        return {"agent_id": agent_id, "start_date": start_date, "end_date": end_date,
                "status": "insufficient_data", "signals": []}
    half = len(worked) // 2
    earlier_days, later_days = set(worked[:half]), set(worked[half:])
    own = [r for r in requests() if r["agent_id"] == agent_id]
    earlier = _period([r for r in own if r["_d"] in earlier_days])
    later = _period([r for r in own if r["_d"] in later_days])
    peers = _period([r for r in requests() if r["agent_id"] != agent_id and r["_d"] in later_days])

    codes = []
    if (later["requests"] >= min_period_requests and peers["requests"] >= min_period_requests
            and later["transfer_rate_percent"] - peers["transfer_rate_percent"] >= 15):
        codes.append("HIGH_TRANSFER_RATE_VS_PEERS")
    enough = earlier["requests"] >= min_period_requests and later["requests"] >= min_period_requests
    if enough:
        rate_change = later["transfer_rate_percent"] - earlier["transfer_rate_percent"]
        if rate_change >= 15:
            codes.append("RISING_TRANSFER_RATE")
        t0, t1 = earlier["average_handling_time_minutes"], later["average_handling_time_minutes"]
        if t0 and t1 is not None:
            time_change = 100 * (t1 - t0) / t0
            if time_change <= -20:
                codes.append("FALLING_HANDLING_TIME")
            if time_change >= 20:
                codes.append("RISING_HANDLING_TIME")
            if time_change <= -20 and rate_change >= 15:
                codes.append("FASTER_HANDLING_WITH_MORE_TRANSFERS")
    return {
        "agent_id": agent_id, "start_date": start_date, "end_date": end_date,
        "status": "analyzed" if enough else "limited_data",
        "periods": {
            "earlier": {"dates": [worked[0].isoformat(), worked[half - 1].isoformat()], **earlier},
            "later": {"dates": [worked[half].isoformat(), worked[-1].isoformat()], **later},
            "peers_later": peers,
        },
        "signal_codes": codes,
    }


def get_agent_request_evidence(agent_id, start_date, end_date, status=None,
                               classification=None, transferred_to=None, limit=30):
    start, end = _d(start_date), _d(end_date)
    rows = [r for r in requests()
            if r["agent_id"] == agent_id and start <= r["_d"] <= end
            and (status is None or r["status"] == status)
            and (classification is None or r["classification"] == classification)
            and (transferred_to is None or r["transferred_to"] == transferred_to)]
    selected = rows[:int(limit)]
    return {
        "agent_id": agent_id, "start_date": start_date, "end_date": end_date,
        "total_matching_requests": len(rows), "returned_requests": len(selected),
        "truncated": len(rows) > int(limit),
        "requests": [{k: r[k] for k in ("request_id", "request_time", "classification", "subject",
                                        "status", "transferred_to", "handling_time_minutes",
                                        "documentation")} for r in selected],
    }


def get_agent_comparison(start_date, end_date):
    start, end = _d(start_date), _d(end_date)
    rows = [r for r in requests() if start <= r["_d"] <= end]
    scheduled = sorted({s["agent_id"] for s in shifts() if start <= s["_d"] <= end})
    agents = []
    for agent_id in scheduled:
        own = [r for r in rows if r["agent_id"] == agent_id]
        by_class: Dict[str, Dict[str, Any]] = {}
        for r in own:
            entry = by_class.setdefault(r["classification"], {"requests": 0, "transferred": 0})
            entry["requests"] += 1
            entry["transferred"] += r["status"] == "transferred"
        for entry in by_class.values():
            entry["transfer_rate_percent"] = _pct(entry["transferred"], entry["requests"])
            entry["low_sample"] = entry["requests"] < LOW_SAMPLE
        transferred = sum(r["status"] == "transferred" for r in own)
        agents.append({
            "agent_id": agent_id,
            "handled_requests": len(own),
            "low_sample": len(own) < LOW_SAMPLE,
            "transferred_requests": transferred,
            "transfer_rate_percent": _pct(transferred, len(own)),
            "first_line_resolution_rate_percent": _pct(sum(r["status"] == "resolved" for r in own), len(own)),
            "average_handling_time_minutes": _avg([r["handling_time_minutes"] for r in own]),
            "by_classification": dict(sorted(by_class.items())),
        })
    agents.sort(key=lambda a: (a["transfer_rate_percent"] is None, -(a["transfer_rate_percent"] or 0), a["agent_id"]))
    return {
        "start_date": start_date, "end_date": end_date, "valid_agent_ids": scheduled,
        "team_requests": len(rows),
        "team_transfer_rate_percent": _pct(sum(r["status"] == "transferred" for r in rows), len(rows)),
        "agents": agents,
    }


def legacy_get_monitor_metrics(start_time, end_time):
    """The monitor contract before the 2026-10-26 fix: inclusive end, last-minus-first counters."""
    start, end = _dt(start_time), _dt(end_time)
    rows = [s for s in snapshots() if start <= s["_t"] <= end]
    if not rows:
        return {"start_time": start_time, "end_time": end_time, "snapshot_count": 0,
                "message": "No monitor data found for this period."}
    return {
        "start_time": start_time, "end_time": end_time,
        "snapshot_count": len(rows),
        "average_monitor_wait_time_minutes": _avg([s["average_wait_time_minutes"] for s in rows]),
        "average_available_agents": _avg([s["available_agents"] for s in rows]),
        "peak_agents_on_calls": max(s["agents_on_calls"] for s in rows),
        "answered_calls_change": rows[-1]["answered_calls"] - rows[0]["answered_calls"],
        "abandoned_calls_change": rows[-1]["abandoned_calls"] - rows[0]["abandoned_calls"],
    }


def legacy_get_requests_by_time_bucket(start_time, end_time, bucket_minutes=5):
    return get_requests_by_time_bucket(start_time, end_time, bucket_minutes, dated_labels=False)


# The date the monitor and time-bucket contracts changed. Saved runs created
# earlier are replayed against the legacy contract they were produced under.
CONTRACT_CHANGE_DATE = "2026-10-26"


REPLAY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "count_requests": count_requests,
    "get_requests_by_classification": get_requests_by_classification,
    "get_classification_count": get_classification_count,
    "get_average_wait_time": get_average_wait_time,
    "get_monitor_metrics": get_monitor_metrics,
    "compare_values": compare_values,
    "get_requests_by_status": get_requests_by_status,
    "get_transfers_by_destination": get_transfers_by_destination,
    "get_requests_by_time_bucket": get_requests_by_time_bucket,
    "get_request_details": get_request_details,
    "get_classification_status_breakdown": get_classification_status_breakdown,
    "get_agent_performance": get_agent_performance,
    "get_agent_daily_trends": get_agent_daily_trends,
    "detect_agent_performance_signals": detect_agent_performance_signals,
    "get_agent_request_evidence": get_agent_request_evidence,
    "get_agent_comparison": get_agent_comparison,
}

REPLAY_LEGACY: Dict[str, Callable[..., Dict[str, Any]]] = {
    **REPLAY,
    "get_monitor_metrics": legacy_get_monitor_metrics,
    "get_requests_by_time_bucket": legacy_get_requests_by_time_bucket,
}


# ---------------------------------------------------------------------------
# "Truth" helpers: what a manager means by a number
# ---------------------------------------------------------------------------

def working_days(start: str, end: str) -> List[date]:
    """Days with at least one request between two datetimes (inclusive dates)."""
    s, e = _dt(start).date(), _dt(end).date()
    return [d for d in data_dates() if s <= d <= e]


def daily_monitor_totals() -> Dict[str, Dict[str, int]]:
    """End-of-day answered/abandoned calls. Monitor counters are cumulative per day."""
    totals: Dict[str, Dict[str, int]] = {}
    for s in snapshots():
        totals[s["_t"].date().isoformat()] = {
            "answered_calls": s["answered_calls"], "abandoned_calls": s["abandoned_calls"]}
    return totals


def abandoned_calls_between(start_time: str, end_time: str) -> int:
    """True abandoned calls in start <= t < end: the sum of each snapshot interval's calls.

    Note the generator's 17:00 snapshot covers 17:00-17:05, after closing, so a
    continuous multi-day window includes it while 08:00-17:00 day windows do not.
    """
    start, end = _dt(start_time), _dt(end_time)
    inc = increments()
    return sum(inc[s["timestamp"]]["abandoned"] for s in snapshots() if start <= s["_t"] < end)


def counters_reset_inside(start_time: str, end_time: str) -> bool:
    """True when a monitor window spans more than one day (cumulative counters reset)."""
    start, end = _dt(start_time), _dt(end_time)
    days = {s["_t"].date() for s in snapshots() if start <= s["_t"] < end}
    return len(days) > 1


def daily_abandoned_in_hours(day: str) -> int:
    """Abandoned calls during working hours (08:00-17:00) of one day."""
    return abandoned_calls_between(f"{day}T08:00:00", f"{day}T17:00:00")


def get_daily_series_total_abandoned(start_date: str, end_date: str) -> int:
    """Sum of working-hours abandoned calls over the working days in a range."""
    return sum(daily_abandoned_in_hours(d.isoformat()) for d in data_dates()
               if _d(start_date) <= d <= _d(end_date))


def agents_on_shift(start_time: str, end_time: str) -> Optional[float]:
    start, end = _dt(start_time), _dt(end_time)
    rows = [s["agents_on_shift"] for s in snapshots() if start <= s["_t"] < end]
    return round(sum(rows) / len(rows), 2) if rows else None

"""Shift-level analytics for the Overview: hourly activity and daily trends.

Everything here is deterministic and built from tools.py functions. "Typical"
means the mean of the same hour across the OTHER working days in the report's
lookback window, so a manager can compare today against a recent baseline.

Results are cached per date because the synthetic dataset does not change
while the server runs. Restart the API after regenerating data.
"""

from functools import lru_cache
from statistics import mean
from typing import Any, Dict, List, Optional

import tools

VOLUME_THRESHOLD_MULTIPLIER = 1.5  # the default used by tools.detect_hourly_volume_anomalies
WORKING_HOURS = range(8, 17)       # 08:00-17:00, matching tools.py


def _hour_label(hour: int) -> str:
    return f"{hour:02d}:00-{hour + 1:02d}:00"


@lru_cache(maxsize=1)
def working_days() -> List[str]:
    """Dates that have any requests, ascending."""
    return sorted({r["request_time"][:10] for r in tools.load_requests()})


@lru_cache(maxsize=64)
def day_profile(date: str) -> Dict[str, Any]:
    """Daily metrics, anomaly detection and per-hour figures for one date."""
    anomalies = tools.detect_hourly_volume_anomalies(date, VOLUME_THRESHOLD_MULTIPLIER)
    counts = anomalies.get("hourly_counts", {})

    hours = []
    for hour in WORKING_HOURS:
        start, end = f"{date}T{hour:02d}:00:00", f"{date}T{hour + 1:02d}:00:00"
        label = _hour_label(hour)
        monitor = tools.get_monitor_metrics(start, end)
        hours.append({
            "hour": label,
            "requests": counts.get(label, 0),
            "average_wait_minutes": tools.get_average_wait_time(start, end)["average_wait_time_minutes"],
            "average_available_agents": monitor.get("average_available_agents"),
        })

    average = anomalies.get("average_hourly_volume") or 0
    return {
        "metrics": tools.get_daily_metrics(date),
        "threshold": anomalies.get("threshold"),
        "average_hourly_requests": average,
        "unusual_hours": [
            {
                "hour": a["start_time"][11:16] + "-" + a["end_time"][11:16],
                "requests": a["request_count"],
                "ratio_to_average": a["ratio_to_daily_hourly_average"],
            }
            for a in anomalies.get("anomalies", [])
        ],
        "hours": hours,
    }


def lookback_days(lookback_start: str, date: str) -> List[str]:
    return [d for d in working_days() if lookback_start <= d <= date]


def _typical(values: List[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return round(mean(present), 2) if present else None


def hourly_activity(date: str, baseline_days: List[str]) -> List[Dict[str, Any]]:
    """Today's hours next to the typical value of the same hour on baseline days."""
    today = day_profile(date)
    baseline = [day_profile(d)["hours"] for d in baseline_days if d != date]
    threshold = today["threshold"] or float("inf")

    rows = []
    for i, hour in enumerate(today["hours"]):
        rows.append({
            **hour,
            "above_threshold": hour["requests"] >= threshold,
            "typical_requests": _typical([b[i]["requests"] for b in baseline]),
            "typical_wait_minutes": _typical([b[i]["average_wait_minutes"] for b in baseline]),
            "typical_available_agents": _typical([b[i]["average_available_agents"] for b in baseline]),
        })
    return rows


def daily_trend(days: List[str], report_dates: set) -> List[Dict[str, Any]]:
    trend = []
    for d in days:
        profile = day_profile(d)
        metrics = profile["metrics"]
        trend.append({
            "date": d,
            "total_requests": metrics["total_requests"],
            "average_wait_time_minutes": metrics["average_wait_time_minutes"],
            "abandoned_calls": metrics["abandoned_calls"],
            "average_available_agents": metrics["average_available_agents"],
            "unusual_hours": profile["unusual_hours"],
            "hourly_requests": [h["requests"] for h in profile["hours"]],
            "has_report": d in report_dates,
        })
    return trend

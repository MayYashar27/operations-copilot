import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


DATA_DIR = Path(__file__).parent / "data"

REQUESTS_FILE = DATA_DIR / "requests.json"
MONITOR_FILE = DATA_DIR / "monitor_snapshots.json"

WORKDAY_START = "08:00:00"
WORKDAY_END = "17:00:00"

# Agent rates from fewer requests than this are flagged as low-sample.
# Same minimum the performance-signal rules use.
LOW_SAMPLE_REQUESTS = 20

# Monitor snapshots are taken every 5 minutes. Each snapshot describes the
# 5 minutes STARTING at its timestamp (the generator applies an incident to
# the snapshots whose hour is the incident hour), so a window counts the
# snapshots with start <= timestamp < end: the same half-open rule as the
# request tools. answered/abandoned counters are cumulative within a day and
# reset each morning, so window totals are summed per day.
MONITOR_INTERVAL_RULE = (
    "Snapshots with start <= timestamp < end; each covers the 5 minutes starting "
    "at its timestamp. Call counts are summed per day (counters reset daily)."
)

# The operating day is 08:00-17:00: all requests fall inside it and every
# shift ends at 17:00. The 17:00 snapshot covers 17:00-17:05, after closing,
# so operational figures exclude it unless after-hours data is asked for.
WORKING_HOURS_WINDOW = f"working hours {WORKDAY_START[:5]}-{WORKDAY_END[:5]} each day"

# Loads data from a JSON file and converts it into Python objects.

def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSON list from a file."""

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Data file was not found: {file_path}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON in file: {file_path}"
        ) from exc

    if not isinstance(data, list):
        raise RuntimeError(
            f"Expected a JSON list in file: {file_path}"
        )

    return data

# Converts a date-time string into a Python datetime object for time comparisons.
def parse_datetime(value: str) -> datetime:
    """Convert an ISO datetime string into a datetime object."""
    return datetime.fromisoformat(value)

# Loads all call center requests from the requests data file.
def load_requests() -> List[Dict[str, Any]]:
    """Load call center requests."""
    return load_json_file(REQUESTS_FILE)

# Loads all operational monitor snapshots from the monitor data file.
def load_monitor_snapshots() -> List[Dict[str, Any]]:
    """Load call center monitor snapshots."""
    return load_json_file(MONITOR_FILE)

# Counts how many requests were received within a specific time range.
def count_requests(
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """Count requests received during a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    matching_requests = [
        request
        for request in requests
        if start <= parse_datetime(request["request_time"]) < end
    ]

    result = {
        "start_time": start_time,
        "end_time": end_time,
        "request_count": len(matching_requests),
    }

    # Periods of different length are only comparable per working day.
    working_days = len({request["request_time"][:10] for request in matching_requests})
    result["working_days"] = working_days
    if working_days > 1:
        result["requests_per_working_day"] = round(len(matching_requests) / working_days, 2)

    return result

# Counts requests by classification within a specific time range.
def get_requests_by_classification(
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """Count requests by classification during a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    counts: Dict[str, int] = {}

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if start <= request_time < end:
            classification = request["classification"]

            counts[classification] = (
                counts.get(classification, 0) + 1
            )

    return {
        "start_time": start_time,
        "end_time": end_time,
        "classifications": counts
    }

# Calculates the average customer wait time for requests within a specific time range.
def get_average_wait_time(
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """Calculate average request wait time for a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    wait_times = [
        request["wait_time_minutes"]
        for request in requests
        if start <= parse_datetime(request["request_time"]) < end
    ]

    if not wait_times:
        return {
            "start_time": start_time,
            "end_time": end_time,
            "average_wait_time_minutes": None,
            "request_count": 0
        }

    average_wait = sum(wait_times) / len(wait_times)

    return {
        "start_time": start_time,
        "end_time": end_time,
        "average_wait_time_minutes": round(average_wait, 2),
        "request_count": len(wait_times)
    }

# Adds per-snapshot call increments to monitor snapshots.
def monitor_snapshots_with_increments() -> List[Dict[str, Any]]:
    """Snapshots in time order, each with the calls answered/abandoned in its own interval.

    Counters are cumulative within a day and start from zero each morning, so a
    snapshot's increment is its counter minus the previous snapshot of the same day.
    """
    snapshots = sorted(load_monitor_snapshots(), key=lambda s: s["timestamp"])
    previous: Dict[str, Dict[str, Any]] = {}
    rows = []
    for snapshot in snapshots:
        day = snapshot["timestamp"][:10]
        before = previous.get(day, {"answered_calls": 0, "abandoned_calls": 0})
        rows.append({
            **snapshot,
            "answered_in_interval": snapshot["answered_calls"] - before["answered_calls"],
            "abandoned_in_interval": snapshot["abandoned_calls"] - before["abandoned_calls"],
        })
        previous[day] = snapshot
    return rows


def _monitor_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    on_shift = [r["agents_on_shift"] for r in rows if isinstance(r.get("agents_on_shift"), (int, float))]
    return {
        "snapshot_count": len(rows),
        "average_monitor_wait_time_minutes": round(
            sum(r["average_wait_time_minutes"] for r in rows) / len(rows), 2
        ),
        "average_available_agents": round(
            sum(r["available_agents"] for r in rows) / len(rows), 2
        ),
        "peak_agents_on_calls": max(r["agents_on_calls"] for r in rows),
        "average_agents_on_shift": round(sum(on_shift) / len(on_shift), 2) if on_shift else None,
        "min_agents_on_shift": min(on_shift) if on_shift else None,
        "answered_calls": sum(r["answered_in_interval"] for r in rows),
        "abandoned_calls": sum(r["abandoned_in_interval"] for r in rows),
    }


def _in_working_hours(timestamp: str) -> bool:
    return WORKDAY_START <= timestamp[11:19] < WORKDAY_END


# Summarizes operational monitor metrics for a specific time range.
def get_monitor_metrics(
    start_time: str,
    end_time: str,
    include_after_hours: bool = False,
) -> Dict[str, Any]:
    """Return operational monitor data for start_time <= t < end_time.

    Works for any window, including several days: calls are summed per day.
    By default only working hours (08:00-17:00) count; snapshots outside them
    are reported as excluded, or included when include_after_hours is True.
    """

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    in_window = [
        snapshot
        for snapshot in monitor_snapshots_with_increments()
        if start <= parse_datetime(snapshot["timestamp"]) < end
    ]
    matching_snapshots = (
        in_window if include_after_hours
        else [s for s in in_window if _in_working_hours(s["timestamp"])]
    )
    excluded = len(in_window) - len(matching_snapshots)
    applied = "all snapshots, including after hours" if include_after_hours else WORKING_HOURS_WINDOW

    if not matching_snapshots:
        result = {
            "start_time": start_time,
            "end_time": end_time,
            "snapshot_count": 0,
            "message": "No monitor data found for this period."
        }
        if excluded:
            result.update({"time_window_applied": applied, "after_hours_snapshots_excluded": excluded})
        return result

    summary = _monitor_summary(matching_snapshots)
    by_day: Dict[str, List[Dict[str, Any]]] = {}
    for snapshot in matching_snapshots:
        by_day.setdefault(snapshot["timestamp"][:10], []).append(snapshot)

    result = {
        "start_time": start_time,
        "end_time": end_time,
        **summary,
        # Earlier names for the same totals, kept for saved records and the UI.
        "answered_calls_change": summary["answered_calls"],
        "abandoned_calls_change": summary["abandoned_calls"],
        "working_days": len(by_day),
        "time_window_applied": applied,
        "after_hours_snapshots_excluded": excluded,
        "interval_rule": MONITOR_INTERVAL_RULE,
    }
    if len(by_day) > 1:
        result["per_day"] = [
            {
                "date": day,
                "answered_calls": sum(r["answered_in_interval"] for r in rows),
                "abandoned_calls": sum(r["abandoned_in_interval"] for r in rows),
                "average_available_agents": round(sum(r["available_agents"] for r in rows) / len(rows), 2),
            }
            for day, rows in by_day.items()
        ]
        result["abandoned_calls_per_working_day"] = round(summary["abandoned_calls"] / len(by_day), 2)
    return result

# Compares a current value to a baseline and calculates the absolute and percentage change.
def compare_values(
    current: float,
    baseline: float,
    current_days: Optional[int] = None,
    baseline_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Compare a current value to a baseline value.

    When both day counts are given, also compares the values per day, which is
    the fair comparison for totals over periods of different length.
    """

    absolute_change = current - baseline

    if baseline == 0:
        percentage_change = None
    else:
        percentage_change = (absolute_change / baseline) * 100

    result = {
        "current": current,
        "baseline": baseline,
        "absolute_change": absolute_change,
        "percentage_change": (
            round(percentage_change, 2)
            if percentage_change is not None
            else None
        )
    }

    if current_days is None and baseline_days is None:
        return result
    if not current_days or not baseline_days or current_days < 0 or baseline_days < 0:
        raise ValueError("Provide both current_days and baseline_days as positive numbers of days.")

    current_per_day = current / current_days
    baseline_per_day = baseline / baseline_days
    per_day_change = current_per_day - baseline_per_day
    result.update({
        "current_days": current_days,
        "baseline_days": baseline_days,
        "current_per_day": round(current_per_day, 2),
        "baseline_per_day": round(baseline_per_day, 2),
        "per_day_absolute_change": round(per_day_change, 2),
        "per_day_percentage_change": (
            round(per_day_change / baseline_per_day * 100, 2) if baseline_per_day else None
        ),
        "note": "Totals cover different numbers of days; use the per-day comparison."
        if current_days != baseline_days else "Equal periods; per-day and total comparisons agree.",
    })
    return result

# Counts requests by status within a specific time range.
def get_requests_by_status(
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """Count requests by status during a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    counts: Dict[str, int] = {}

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if start <= request_time < end:
            status = request["status"]

            counts[status] = (
                counts.get(status, 0) + 1
            )

    return {
        "start_time": start_time,
        "end_time": end_time,
        "statuses": counts
    }

# Counts transferred requests by destination within a specific time range.
def get_transfers_by_destination(
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """Count transferred requests by destination during a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    counts: Dict[str, int] = {}

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if start <= request_time < end:
            if request["status"] == "transferred":
                destination = request["transferred_to"]

                if destination is not None:
                    counts[destination] = (
                        counts.get(destination, 0) + 1
                    )

    return {
        "start_time": start_time,
        "end_time": end_time,
        "transfer_destinations": counts
    }


# Groups requests into time buckets and counts how many requests were received in each interval.
def get_requests_by_time_bucket(
    start_time: str,
    end_time: str,
    bucket_minutes: int = 5
) -> Dict[str, Any]:
    """Count requests in fixed time intervals within a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    # Over several days, HH:MM labels would repeat and merge different days.
    spans_days = start.date() != (end - timedelta(microseconds=1)).date()
    label_format = "%Y-%m-%d %H:%M" if spans_days else "%H:%M"

    buckets: Dict[str, int] = {}

    current_bucket_start = start

    while current_bucket_start < end:
        current_bucket_end = current_bucket_start + timedelta(
            minutes=bucket_minutes
        )

        bucket_label = (
            f"{current_bucket_start.strftime(label_format)}-"
            f"{current_bucket_end.strftime('%H:%M')}"
        )

        buckets[bucket_label] = 0

        current_bucket_start = current_bucket_end

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if start <= request_time < end:
            minutes_from_start = int(
                (request_time - start).total_seconds() // 60
            )

            bucket_index = minutes_from_start // bucket_minutes

            bucket_start = start + timedelta(
                minutes=bucket_index * bucket_minutes
            )

            bucket_end = bucket_start + timedelta(
                minutes=bucket_minutes
            )

            bucket_label = (
                f"{bucket_start.strftime(label_format)}-"
                f"{bucket_end.strftime('%H:%M')}"
            )

            buckets[bucket_label] += 1

    return {
        "start_time": start_time,
        "end_time": end_time,
        "bucket_minutes": bucket_minutes,
        "request_counts": buckets
    }

# Counts requests of a specific classification within a specific time range.
def get_classification_count(
    start_time: str,
    end_time: str,
    classification: str
) -> Dict[str, Any]:
    """Count requests of a specific classification during a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    count = 0

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if (
            start <= request_time < end
            and request["classification"] == classification
        ):
            count += 1

    return {
        "start_time": start_time,
        "end_time": end_time,
        "classification": classification,
        "request_count": count
    }

# Returns request-level details for requests within a specific time range,
# optionally filtered by classification.
def get_request_details(
    start_time: str,
    end_time: str,
    classification: str = None
) -> Dict[str, Any]:
    """Return request details for a given time range, optionally filtered by classification."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    matching_requests = []

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if not (start <= request_time < end):
            continue

        if classification is not None:
            if request["classification"] != classification:
                continue

        matching_requests.append({
            "request_id": request["request_id"],
            "request_time": request["request_time"],
            "subject": request["subject"],
            "classification": request["classification"],
            "documentation": request["documentation"]
        })

    return {
        "start_time": start_time,
        "end_time": end_time,
        "classification_filter": classification,
        "request_count": len(matching_requests),
        "requests": matching_requests
    }

# Returns status and transfer breakdown for a specific classification
# within a given time range.
def get_classification_status_breakdown(
    start_time: str,
    end_time: str,
    classification: str
) -> Dict[str, Any]:
    """Analyze statuses and transfer destinations for one classification."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    requests = load_requests()

    matching_requests = [
        request
        for request in requests
        if (
            start <= parse_datetime(request["request_time"]) < end
            and request["classification"] == classification
        )
    ]

    status_counts: Dict[str, int] = {}
    transfer_destinations: Dict[str, int] = {}

    for request in matching_requests:
        status = request["status"]

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

        if status == "transferred":
            destination = request["transferred_to"]

            if destination is not None:
                transfer_destinations[destination] = (
                    transfer_destinations.get(destination, 0) + 1
                )

    return {
        "start_time": start_time,
        "end_time": end_time,
        "classification": classification,
        "request_count": len(matching_requests),
        "statuses": status_counts,
        "transfer_destinations": transfer_destinations
    }


def detect_hourly_volume_anomalies(
    date: str,
    threshold_multiplier: float = 1.5
) -> Dict[str, Any]:
    """
    Detect hourly request-volume anomalies for a given day.

    An hour is considered anomalous when its request volume is at least
    threshold_multiplier times the average hourly request volume.
    """

    requests = load_requests()

    hourly_counts = {
        hour: 0
        for hour in range(8, 17)
    }

    for request in requests:
        request_time = parse_datetime(request["request_time"])

        if request_time.date().isoformat() != date:
            continue

        if request_time.hour in hourly_counts:
            hourly_counts[request_time.hour] += 1

    total_requests = sum(hourly_counts.values())

    if total_requests == 0:
        return {
            "date": date,
            "total_requests": 0,
            "average_hourly_volume": 0,
            "anomalies": []
        }

    average_hourly_volume = (
        total_requests / len(hourly_counts)
    )

    threshold = (
        average_hourly_volume * threshold_multiplier
    )

    anomalies = []

    for hour, count in hourly_counts.items():
        if count >= threshold:
            anomalies.append({
                "start_time": f"{date}T{hour:02d}:00:00",
                "end_time": f"{date}T{hour + 1:02d}:00:00",
                "request_count": count,
                "ratio_to_daily_hourly_average": round(
                    count / average_hourly_volume,
                    2
                )
            })

    return {
        "date": date,
        "total_requests": total_requests,
        "average_hourly_volume": round(
            average_hourly_volume,
            2
        ),
        "threshold": round(threshold, 2),
        "hourly_counts": {
            f"{hour:02d}:00-{hour + 1:02d}:00": count
            for hour, count in hourly_counts.items()
        },
        "anomalies": anomalies
    }

def get_daily_metrics(date: str) -> Dict[str, Any]:
    """
    Return deterministic operational metrics for a full working day.
    """

    start_time = f"{date}T08:00:00"
    end_time = f"{date}T17:00:00"

    request_count_result = count_requests(
        start_time=start_time,
        end_time=end_time,
    )

    wait_time_result = get_average_wait_time(
        start_time=start_time,
        end_time=end_time,
    )

    monitor_result = get_monitor_metrics(
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "date": date,
        "total_requests": request_count_result["request_count"],
        "average_wait_time_minutes": wait_time_result[
            "average_wait_time_minutes"
        ],
        "abandoned_calls": monitor_result.get("abandoned_calls"),
        "average_available_agents": monitor_result[
            "average_available_agents"
        ],
    }


AGENT_SHIFTS_FILE = DATA_DIR / "agent_shifts.json"


def get_agent_performance(agent_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Compare an agent with the team over an inclusive date range."""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    if start > end:
        raise ValueError("start_date must be on or before end_date")

    requests = [
        r for r in load_requests()
        if start <= parse_datetime(r["request_time"]).date() <= end
    ]
    shifts = [
        s for s in load_json_file(AGENT_SHIFTS_FILE)
        if start <= datetime.fromisoformat(s["date"]).date() <= end
    ]
    agent_shifts = [s for s in shifts if s["agent_id"] == agent_id]
    if not agent_shifts:
        raise ValueError(f"No shifts found for {agent_id} in this date range")

    def summarize(items: List[Dict[str, Any]], hours: float) -> Dict[str, Any]:
        count = len(items)
        transfers = [r for r in items if r.get("status") == "transferred"]
        resolved = sum(r.get("status") == "resolved" for r in items)
        handling = [r["handling_time_minutes"] for r in items
                    if isinstance(r.get("handling_time_minutes"), (int, float))]
        destinations: Dict[str, int] = {}
        for r in transfers:
            dest = r.get("transferred_to")
            if dest:
                destinations[dest] = destinations.get(dest, 0) + 1
        return {
            "handled_requests": count,
            "low_sample": count < LOW_SAMPLE_REQUESTS,
            "scheduled_hours": round(hours, 2),
            "requests_per_scheduled_hour": round(count / hours, 2) if hours else None,
            "transferred_requests": len(transfers),
            "transfer_rate_percent": round(100 * len(transfers) / count, 2) if count else None,
            "first_line_resolved_requests": resolved,
            "first_line_resolution_rate_percent": round(100 * resolved / count, 2) if count else None,
            "average_handling_time_minutes": round(sum(handling) / len(handling), 2) if handling else None,
            "transfer_destinations": dict(sorted(destinations.items(), key=lambda x: -x[1])),
        }

    agent_requests = [r for r in requests if r.get("agent_id") == agent_id]
    agent_hours = sum(float(s["scheduled_hours"]) for s in agent_shifts)
    team_hours = sum(float(s["scheduled_hours"]) for s in shifts)
    team_agents = {s["agent_id"] for s in shifts}
    team = summarize(requests, team_hours)
    team["average_requests_per_agent"] = round(len(requests) / len(team_agents), 2) if team_agents else None

    return {
        "agent_id": agent_id,
        "start_date": start_date,
        "end_date": end_date,
        "period_label": _period_label(start_date, end_date, len({s["date"] for s in agent_shifts})),
        "agent": summarize(agent_requests, agent_hours),
        "team_baseline": team,
        "comparison_note": "Team rates are request-weighted; requests/hour uses scheduled shift hours. These are descriptive signals, not employee performance ratings.",
    }


def _period_label(start_date: str, end_date: str, working_days: int) -> str:
    """States the period a result covers, so one day is never read as a whole period."""
    days = "1 working day" if working_days == 1 else f"{working_days} working days"
    span = start_date if start_date == end_date else f"{start_date} to {end_date}"
    return f"{span} ({days}). Rates describe only this period."


def get_agent_daily_trends(
    agent_id: str,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Calculate daily performance trends for an agent.
    Dates are inclusive.
    """

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    if end < start:
        raise ValueError("end_date must be on or after start_date")

    requests = load_requests()
    shifts = load_json_file(DATA_DIR / "agent_shifts.json")

    daily = {}
    current = start

    while current <= end:
        date_str = current.isoformat()
        daily[date_str] = {
            "handled_requests": 0,
            "transferred_requests": 0,
            "first_line_resolved_requests": 0,
            "handling_time_total": 0.0,
            "handling_time_count": 0,
            "scheduled_hours": 0.0,
        }
        current += timedelta(days=1)

    for request in requests:
        if request.get("agent_id") != agent_id:
            continue

        date_str = request["request_time"][:10]

        if date_str not in daily:
            continue

        record = daily[date_str]
        record["handled_requests"] += 1

        if request.get("status") == "transferred":
            record["transferred_requests"] += 1
        elif request.get("status") == "resolved":
            record["first_line_resolved_requests"] += 1

        handling_time = request.get("handling_time_minutes")
        if isinstance(handling_time, (int, float)):
            record["handling_time_total"] += handling_time
            record["handling_time_count"] += 1

    for shift in shifts:
        if shift.get("agent_id") != agent_id:
            continue

        date_str = shift.get("date")
        if date_str not in daily:
            continue

        # Uses scheduled_hours when present.
        # Otherwise derives hours from shift timestamps.
        hours = shift.get("scheduled_hours")

        if hours is None:
            shift_start = shift.get("start_time")
            shift_end = shift.get("end_time")

            if shift_start and shift_end:
                hours = (
                    parse_datetime(shift_end)
                    - parse_datetime(shift_start)
                ).total_seconds() / 3600

        if isinstance(hours, (int, float)):
            daily[date_str]["scheduled_hours"] += hours

    trends = []

    for date_str, record in daily.items():
        count = record["handled_requests"]
        transferred = record["transferred_requests"]
        resolved = record["first_line_resolved_requests"]
        hours = record["scheduled_hours"]
        handling_count = record["handling_time_count"]

        trends.append({
            "date": date_str,
            "handled_requests": count,
            "scheduled_hours": round(hours, 2),
            "requests_per_scheduled_hour": (
                round(count / hours, 2) if hours > 0 else None
            ),
            "transferred_requests": transferred,
            "transfer_rate_percent": (
                round(transferred / count * 100, 2)
                if count > 0 else None
            ),
            "first_line_resolution_rate_percent": (
                round(resolved / count * 100, 2)
                if count > 0 else None
            ),
            "average_handling_time_minutes": (
                round(
                    record["handling_time_total"] / handling_count,
                    2
                )
                if handling_count > 0 else None
            ),
        })

    return {
        "agent_id": agent_id,
        "start_date": start_date,
        "end_date": end_date,
        "daily_trends": trends,
    }

def _classification_rates(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Requests, transfers and transfer rate per classification, sorted by name."""
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        entry = out.setdefault(r["classification"], {"requests": 0, "transferred": 0})
        entry["requests"] += 1
        entry["transferred"] += r.get("status") == "transferred"
    for entry in out.values():
        entry["transfer_rate_percent"] = round(100 * entry["transferred"] / entry["requests"], 2)
        entry["low_sample"] = entry["requests"] < LOW_SAMPLE_REQUESTS
    return dict(sorted(out.items()))

# Append to the END of tools.py, after get_agent_daily_trends().
# Uses existing load_requests(), get_agent_daily_trends(), and parse_datetime().

def detect_agent_performance_signals(
    agent_id: str,
    start_date: str,
    end_date: str,
    min_period_requests: int = 20,
) -> Dict[str, Any]:
    """Detect descriptive signals; never assign an employee performance rating.

    Inclusive dates; splits observed working days into two chronological halves.
    Team comparison excludes the selected agent.
    """
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    if start > end:
        raise ValueError("end_date must be on or after start_date")
    if min_period_requests < 1:
        raise ValueError("min_period_requests must be positive")

    trends = get_agent_daily_trends(agent_id, start_date, end_date)["daily_trends"]
    working_days = [day["date"] for day in trends if day["scheduled_hours"] > 0]
    if len(working_days) < 4:
        return {
            "agent_id": agent_id, "start_date": start_date, "end_date": end_date,
            "status": "insufficient_data", "signals": [],
            "reason": "At least four scheduled working days are required.",
        }

    midpoint = len(working_days) // 2
    earlier_days = set(working_days[:midpoint])
    later_days = set(working_days[midpoint:])
    observed_days = earlier_days | later_days
    all_requests = [
        r for r in load_requests()
        if r["request_time"][:10] in observed_days
    ]
    agent_requests = [r for r in all_requests if r.get("agent_id") == agent_id]
    peers = [r for r in all_requests if r.get("agent_id") != agent_id]

    def metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        count = len(rows)
        transfers = sum(r.get("status") == "transferred" for r in rows)
        handling = [
            float(r["handling_time_minutes"]) for r in rows
            if isinstance(r.get("handling_time_minutes"), (int, float))
        ]
        return {
            "requests": count,
            "transfers": transfers,
            "transfer_rate_percent": round(100 * transfers / count, 2) if count else None,
            "average_handling_time_minutes": round(sum(handling) / len(handling), 2) if handling else None,
            # Per-category figures for the same period, so category rates are
            # never taken from a different period than the totals beside them.
            "by_classification": _classification_rates(rows),
        }

    earlier = metrics([r for r in agent_requests if r["request_time"][:10] in earlier_days])
    later = metrics([r for r in agent_requests if r["request_time"][:10] in later_days])
    peer_later = metrics([r for r in peers if r["request_time"][:10] in later_days])
    enough = earlier["requests"] >= min_period_requests and later["requests"] >= min_period_requests
    signals: List[Dict[str, Any]] = []

    def add_signal(code: str, evidence: Dict[str, Any], explanation: str) -> None:
        signals.append({"code": code, "evidence": evidence, "interpretation": explanation})

    agent_rate = later["transfer_rate_percent"]
    peer_rate = peer_later["transfer_rate_percent"]
    if (later["requests"] >= min_period_requests
            and peer_later["requests"] >= min_period_requests
            and agent_rate is not None and peer_rate is not None
            and agent_rate - peer_rate >= 15):
        add_signal("HIGH_TRANSFER_RATE_VS_PEERS", {
            "agent_transfer_rate_percent": agent_rate,
            "peer_transfer_rate_percent": peer_rate,
            "difference_percentage_points": round(agent_rate - peer_rate, 2),
            "agent_request_count": later["requests"],
            "peer_request_count": peer_later["requests"],
        }, "Higher transfer rate than peers; review case mix and transfer reasons.")

    if enough:
        rate_change = later["transfer_rate_percent"] - earlier["transfer_rate_percent"]
        if rate_change >= 15:
            add_signal("RISING_TRANSFER_RATE", {
                "earlier_transfer_rate_percent": earlier["transfer_rate_percent"],
                "later_transfer_rate_percent": later["transfer_rate_percent"],
                "change_percentage_points": round(rate_change, 2),
                "earlier_requests": earlier["requests"],
                "later_requests": later["requests"],
            }, "Transfer rate rose between periods; this is not proof of unnecessary transfers.")

        earlier_time = earlier["average_handling_time_minutes"]
        later_time = later["average_handling_time_minutes"]
        if earlier_time is not None and later_time is not None and earlier_time > 0:
            time_change = 100 * (later_time - earlier_time) / earlier_time
            if time_change <= -20:
                add_signal("FALLING_HANDLING_TIME", {
                    "earlier_average_minutes": earlier_time,
                    "later_average_minutes": later_time,
                    "change_percent": round(time_change, 2),
                }, "Handling time fell; investigate context before treating it as positive or negative.")
            if time_change >= 20:
                add_signal("RISING_HANDLING_TIME", {
                    "earlier_average_minutes": earlier_time,
                    "later_average_minutes": later_time,
                    "change_percent": round(time_change, 2),
                }, "Handling time rose; investigate case complexity and workflow changes.")
            if time_change <= -20 and rate_change >= 15:
                add_signal("FASTER_HANDLING_WITH_MORE_TRANSFERS", {
                    "handling_time_change_percent": round(time_change, 2),
                    "transfer_rate_change_percentage_points": round(rate_change, 2),
                }, "Concurrent changes warrant review of individual requests and documentation.")

    return {
        "agent_id": agent_id,
        "start_date": start_date,
        "end_date": end_date,
        "status": "analyzed" if enough else "limited_data",
        "periods": {
            "earlier": {"dates": [working_days[0], working_days[midpoint - 1]], **earlier},
            "later": {"dates": [working_days[midpoint], working_days[-1]], **later},
            "peers_later": peer_later,
        },
        "signals": signals,
        "methodology": "Two halves of scheduled working days; rates are request-weighted. Peer baseline excludes the agent. Thresholds are illustrative heuristics, not validated personnel assessment rules.",
    }



def get_agent_request_evidence(
    agent_id: str,
    start_date: str,
    end_date: str,
    status: str = None,
    classification: str = None,
    transferred_to: str = None,
    limit: int = 30,
) -> Dict[str, Any]:
    """Retrieve request-level evidence for one agent."""

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    if end < start:
        raise ValueError("end_date must be on or after start_date")

    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    matching = []

    for request in load_requests():
        if request.get("agent_id") != agent_id:
            continue

        request_date = parse_datetime(
            request["request_time"]
        ).date()

        if not start <= request_date <= end:
            continue

        if status is not None and request.get("status") != status:
            continue

        if (
            classification is not None
            and request.get("classification") != classification
        ):
            continue

        if (
            transferred_to is not None
            and request.get("transferred_to") != transferred_to
        ):
            continue

        matching.append(request)

    matching.sort(key=lambda r: r["request_time"])

    selected = matching[:limit]

    return {
        "agent_id": agent_id,
        "start_date": start_date,
        "end_date": end_date,
        "filters": {
            "status": status,
            "classification": classification,
            "transferred_to": transferred_to,
        },
        "total_matching_requests": len(matching),
        "returned_requests": len(selected),
        "truncated": len(matching) > limit,
        "requests": [
            {
                "request_id": r.get("request_id"),
                "request_time": r.get("request_time"),
                "classification": r.get("classification"),
                "subject": r.get("subject"),
                "status": r.get("status"),
                "transferred_to": r.get("transferred_to"),
                "handling_time_minutes": r.get(
                    "handling_time_minutes"
                ),
                "documentation": r.get("documentation"),
            }
            for r in selected
        ],
    }



def get_agent_documentation_screening(
    agent_id: str,
    date: str,
    short_word_threshold: int = 6,
) -> Dict[str, Any]:
    """Screen all documentation for one agent on one day.

    Descriptive indicators only; not a judgment of service quality.
    Text is not sent to an LLM by this function.
    """
    target_date = datetime.fromisoformat(date).date()
    if short_word_threshold < 1:
        raise ValueError("short_word_threshold must be positive")

    rows = [
        r for r in load_requests()
        if r.get("agent_id") == agent_id
        and isinstance(r.get("request_time"), str)
        and datetime.fromisoformat(r["request_time"]).date() == target_date
    ]

    records = []
    for r in rows:
        doc = r.get("documentation")
        text = doc.strip() if isinstance(doc, str) else ""
        normalized = " ".join(text.casefold().split())
        records.append({
            "request_id": r.get("request_id"),
            "classification": r.get("classification"),
            "status": r.get("status"),
            "word_count": len(text.split()),
            "normalized": normalized,
        })

    count = len(records)
    missing = [r for r in records if not r["normalized"]]
    short = [r for r in records if r["normalized"] and r["word_count"] < short_word_threshold]

    groups: Dict[str, List[Any]] = {}
    for r in records:
        if r["normalized"]:
            groups.setdefault(r["normalized"], []).append(r["request_id"])
    repeated = [ids for ids in groups.values() if len(ids) >= 2]
    repeated.sort(key=len, reverse=True)
    lengths = [r["word_count"] for r in records if r["normalized"]]

    def pct(n: int) -> float | None:
        return round(n * 100 / count, 2) if count else None

    return {
        "agent_id": agent_id,
        "date": date,
        "status": "screened" if count else "no_requests",
        "total_requests": count,
        "documented_requests": count - len(missing),
        "missing_documentation_count": len(missing),
        "missing_documentation_percent": pct(len(missing)),
        "short_documentation_count": len(short),
        "short_documentation_percent": pct(len(short)),
        "short_word_threshold": short_word_threshold,
        "average_documentation_words": round(sum(lengths) / len(lengths), 2) if lengths else None,
        "missing_request_ids": [r["request_id"] for r in missing],
        "short_request_ids": [r["request_id"] for r in short],
        "repeated_exact_text_groups": [
            {"request_ids": ids, "count": len(ids)} for ids in repeated
        ],
        "methodology": (
            "Word counts use whitespace splitting. Repetition matches normalized exact text "
            "(case and whitespace ignored), not semantic similarity. "
            "Short or repeated notes are screening signals, not proof of poor documentation."
        ),
    }


# ---------------------------------------------------------
# Agent identity and cross-agent comparison
# ---------------------------------------------------------

def known_agent_ids() -> List[str]:
    """Agent IDs that exist in the shift schedule, sorted (e.g. A01..A15)."""
    return sorted({s["agent_id"] for s in load_json_file(AGENT_SHIFTS_FILE) if s.get("agent_id")})


def validate_agent_id(agent_id: str) -> None:
    """Reject identifiers that do not exist, and say which ones do."""
    valid = known_agent_ids()
    if agent_id not in valid:
        raise ValueError(
            f"Unknown agent_id '{agent_id}'. Valid agent IDs: {', '.join(valid)}. "
            "To compare all agents at once, use get_agent_comparison."
        )


def get_agent_comparison(start_date: str, end_date: str) -> Dict[str, Any]:
    """Compare every scheduled agent over an inclusive date range.

    Per agent: requests, transfers, transfer rate, first-line resolution,
    average handling time, and requests/transfers per classification.
    Same formulas as get_agent_performance. Descriptive only: not a rating.
    """
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    if start > end:
        raise ValueError("start_date must be on or before end_date")

    requests = [r for r in load_requests() if start <= parse_datetime(r["request_time"]).date() <= end]
    scheduled = sorted({
        s["agent_id"] for s in load_json_file(AGENT_SHIFTS_FILE)
        if start <= datetime.fromisoformat(s["date"]).date() <= end
    })

    def rate(part: int, whole: int) -> Optional[float]:
        return round(100 * part / whole, 2) if whole else None

    agents = []
    for agent_id in scheduled:
        rows = [r for r in requests if r.get("agent_id") == agent_id]
        transferred = [r for r in rows if r.get("status") == "transferred"]
        resolved = sum(r.get("status") == "resolved" for r in rows)
        handling = [r["handling_time_minutes"] for r in rows
                    if isinstance(r.get("handling_time_minutes"), (int, float))]
        by_classification: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            entry = by_classification.setdefault(r["classification"], {"requests": 0, "transferred": 0})
            entry["requests"] += 1
            entry["transferred"] += r.get("status") == "transferred"
        for entry in by_classification.values():
            entry["transfer_rate_percent"] = rate(entry["transferred"], entry["requests"])
            entry["low_sample"] = entry["requests"] < LOW_SAMPLE_REQUESTS
        agents.append({
            "agent_id": agent_id,
            "handled_requests": len(rows),
            "low_sample": len(rows) < LOW_SAMPLE_REQUESTS,
            "transferred_requests": len(transferred),
            "transfer_rate_percent": rate(len(transferred), len(rows)),
            "first_line_resolution_rate_percent": rate(resolved, len(rows)),
            "average_handling_time_minutes": round(sum(handling) / len(handling), 2) if handling else None,
            "by_classification": dict(sorted(by_classification.items())),
        })

    agents.sort(key=lambda a: (a["transfer_rate_percent"] is None, -(a["transfer_rate_percent"] or 0), a["agent_id"]))
    team_transfers = sum(r.get("status") == "transferred" for r in requests)
    working_days = len({r["request_time"][:10] for r in requests})

    # A change between the earlier and later half of the period can hide behind
    # a normal period average, so each agent also carries its trend signals.
    trend_note = None
    if working_days >= 4:
        for agent in agents:
            signals = detect_agent_performance_signals(agent["agent_id"], start_date, end_date)
            agent["trend_signals"] = [s["code"] for s in signals.get("signals", [])]
        trend_note = ("trend_signals compare each agent's earlier and later half of the period "
                      "(detect_agent_performance_signals); an agent can have a normal period "
                      "average and still a significant trend.")
    result = {
        "start_date": start_date,
        "end_date": end_date,
        "period_label": _period_label(start_date, end_date, working_days),
        "working_days": working_days,
        "low_sample_threshold": LOW_SAMPLE_REQUESTS,
        "valid_agent_ids": scheduled,
        "team_requests": len(requests),
        "team_transfer_rate_percent": rate(team_transfers, len(requests)),
        "agents": agents,
        "note": "Sorted by transfer rate. Descriptive signals, not performance ratings; "
                "rates marked low_sample (fewer than 20 requests) are volatile.",
    }
    if trend_note:
        result["trend_signals_note"] = trend_note
    return result


# ---------------------------------------------------------
# Day-level views: fair comparisons, incident discovery, capacity
# ---------------------------------------------------------

def list_working_days(start_date: str, end_date: str) -> List[str]:
    """Dates between start_date and end_date (inclusive) that have any requests."""
    start = datetime.fromisoformat(start_date).date().isoformat()
    end = datetime.fromisoformat(end_date).date().isoformat()
    return sorted({r["request_time"][:10] for r in load_requests() if start <= r["request_time"][:10] <= end})


def get_daily_series(start_date: str, end_date: str) -> Dict[str, Any]:
    """One row per working day (08:00-17:00), plus totals and per-working-day averages.

    Use for trends and for comparing periods of different length.
    """
    if datetime.fromisoformat(start_date) > datetime.fromisoformat(end_date):
        raise ValueError("start_date must be on or before end_date")
    days = list_working_days(start_date, end_date)
    requests = load_requests()
    rows = []
    for day in days:
        start, end = f"{day}T{WORKDAY_START}", f"{day}T{WORKDAY_END}"
        day_requests = [r for r in requests if start <= r["request_time"] < end]
        transferred = sum(r["status"] == "transferred" for r in day_requests)
        waits = [r["wait_time_minutes"] for r in day_requests]
        monitor = get_monitor_metrics(start, end)
        rows.append({
            "date": day,
            "requests": len(day_requests),
            "transferred": transferred,
            "transfer_rate_percent": round(100 * transferred / len(day_requests), 2) if day_requests else None,
            "average_wait_time_minutes": round(sum(waits) / len(waits), 2) if waits else None,
            "requests_by_classification": dict(sorted(
                {c: sum(r["classification"] == c for r in day_requests)
                 for c in {r["classification"] for r in day_requests}}.items())),
            "abandoned_calls": monitor.get("abandoned_calls"),
            "answered_calls": monitor.get("answered_calls"),
            "average_available_agents": monitor.get("average_available_agents"),
            "average_agents_on_shift": monitor.get("average_agents_on_shift"),
            "min_agents_on_shift": monitor.get("min_agents_on_shift"),
        })

    def per_day(field: str) -> Optional[float]:
        values = [row[field] for row in rows if row[field] is not None]
        return round(sum(values) / len(values), 2) if values else None

    return {
        "start_date": start_date,
        "end_date": end_date,
        "working_days": len(rows),
        "days": rows,
        "totals": {
            "requests": sum(row["requests"] for row in rows),
            "transferred": sum(row["transferred"] for row in rows),
            "abandoned_calls": sum(row["abandoned_calls"] or 0 for row in rows),
        },
        "per_working_day": {
            "requests": per_day("requests"),
            "transferred": per_day("transferred"),
            "abandoned_calls": per_day("abandoned_calls"),
            "average_available_agents": per_day("average_available_agents"),
        },
        "note": "Compare periods using per_working_day values; totals depend on how many days a period has.",
    }


def detect_volume_anomalies(
    start_date: str,
    end_date: str,
    threshold_multiplier: float = 1.5,
) -> Dict[str, Any]:
    """Unusual hours on every working day in a date range (same rule as the Overview).

    Each unusual hour also says what its requests were: the count per
    classification and the most frequent subjects.
    """
    days = list_working_days(start_date, end_date)
    requests = load_requests()
    anomalies = []
    for day in days:
        result = detect_hourly_volume_anomalies(day, threshold_multiplier)
        for anomaly in result["anomalies"]:
            rows = [r for r in requests if anomaly["start_time"] <= r["request_time"] < anomaly["end_time"]]
            subjects: Dict[str, int] = {}
            for r in rows:
                subjects[r["subject"]] = subjects.get(r["subject"], 0) + 1
            anomalies.append({
                "date": day, **anomaly,
                "day_average_hourly_volume": result["average_hourly_volume"],
                "requests_by_classification": dict(sorted(
                    {c: sum(r["classification"] == c for r in rows)
                     for c in {r["classification"] for r in rows}}.items())),
                "top_subjects": [{"subject": s, "requests": n} for s, n in
                                 sorted(subjects.items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
            })
    anomalies.sort(key=lambda a: -a["ratio_to_daily_hourly_average"])
    return {
        "start_date": start_date,
        "end_date": end_date,
        "working_days_checked": len(days),
        "threshold_multiplier": threshold_multiplier,
        "anomalies": anomalies,
        "rule": "An hour is unusual when its requests are at least threshold_multiplier times "
                "that day's average hourly volume (08:00-17:00).",
    }


def get_capacity_context(start_time: str, end_time: str) -> Dict[str, Any]:
    """Demand and capacity in a window, next to the previous window and the typical day.

    Use for spikes and long waits: shows whether demand rose, capacity fell, or both.
    "Typical" is the mean of the same clock window on the other working days.
    """
    start, end = parse_datetime(start_time), parse_datetime(end_time)
    if start >= end:
        raise ValueError("start_time must be before end_time")
    if start.date() != (end - timedelta(microseconds=1)).date():
        raise ValueError("get_capacity_context takes a window within one day; use get_daily_series for several days.")

    def snapshot_of(window_start: datetime, window_end: datetime) -> Dict[str, Any]:
        s, e = window_start.isoformat(), window_end.isoformat()
        monitor = get_monitor_metrics(s, e)
        return {
            "start_time": s,
            "end_time": e,
            "requests": count_requests(s, e)["request_count"],
            "average_wait_time_minutes": get_average_wait_time(s, e)["average_wait_time_minutes"],
            "average_agents_on_shift": monitor.get("average_agents_on_shift"),
            "min_agents_on_shift": monitor.get("min_agents_on_shift"),
            "average_available_agents": monitor.get("average_available_agents"),
            "peak_agents_on_calls": monitor.get("peak_agents_on_calls"),
            "abandoned_calls": monitor.get("abandoned_calls"),
        }

    length = end - start
    window = snapshot_of(start, end)
    day_open = start.replace(hour=int(WORKDAY_START[:2]), minute=0, second=0, microsecond=0)
    previous = snapshot_of(start - length, start) if start - length >= day_open else None

    others = [d for d in list_working_days("0001-01-01", "9999-12-31") if d != start.date().isoformat()]
    typical_rows = []
    for day in others:
        shift = datetime.fromisoformat(day).date() - start.date()
        typical_rows.append(snapshot_of(start + shift, end + shift))

    def mean_of(field: str) -> Optional[float]:
        values = [row[field] for row in typical_rows if row[field] is not None]
        return round(sum(values) / len(values), 2) if values else None

    fields = ("requests", "average_wait_time_minutes", "average_agents_on_shift",
              "average_available_agents", "abandoned_calls")
    typical = {field: mean_of(field) for field in fields}
    versus_typical = {
        field: round(window[field] - typical[field], 2)
        for field in fields if window[field] is not None and typical[field] is not None
    }
    return {
        "window": window,
        "previous_window": previous,
        "typical_same_window": {**typical, "days": len(typical_rows)},
        "difference_from_typical": versus_typical,
        "reading_guide": "Demand side: requests vs typical. Capacity side: agents on shift and "
                         "available agents vs typical. Both can contribute; neither proves a cause.",
    }

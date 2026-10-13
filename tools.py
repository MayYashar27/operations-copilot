import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List


DATA_DIR = Path(__file__).parent / "data"

REQUESTS_FILE = DATA_DIR / "requests.json"
MONITOR_FILE = DATA_DIR / "monitor_snapshots.json"

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

    return {
        "start_time": start_time,
        "end_time": end_time,
        "request_count": len(matching_requests)
    }

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

# Summarizes operational monitor metrics for a specific time range.
def get_monitor_metrics(
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """Return operational monitor data for a given time range."""

    start = parse_datetime(start_time)
    end = parse_datetime(end_time)

    snapshots = load_monitor_snapshots()

    matching_snapshots = [
        snapshot
        for snapshot in snapshots
        if start <= parse_datetime(snapshot["timestamp"]) <= end
    ]

    if not matching_snapshots:
        return {
            "start_time": start_time,
            "end_time": end_time,
            "snapshot_count": 0,
            "message": "No monitor data found for this period."
        }

    average_wait_time = sum(
        snapshot["average_wait_time_minutes"]
        for snapshot in matching_snapshots
    ) / len(matching_snapshots)

    average_available_agents = sum(
        snapshot["available_agents"]
        for snapshot in matching_snapshots
    ) / len(matching_snapshots)

    peak_agents_on_calls = max(
        snapshot["agents_on_calls"]
        for snapshot in matching_snapshots
    )

    first_snapshot = matching_snapshots[0]
    last_snapshot = matching_snapshots[-1]

    answered_calls_change = (
        last_snapshot["answered_calls"]
        - first_snapshot["answered_calls"]
    )

    abandoned_calls_change = (
        last_snapshot["abandoned_calls"]
        - first_snapshot["abandoned_calls"]
    )

    return {
        "start_time": start_time,
        "end_time": end_time,
        "snapshot_count": len(matching_snapshots),
        "average_monitor_wait_time_minutes": round(
            average_wait_time, 2
        ),
        "average_available_agents": round(
            average_available_agents, 2
        ),
        "peak_agents_on_calls": peak_agents_on_calls,
        "answered_calls_change": answered_calls_change,
        "abandoned_calls_change": abandoned_calls_change
    }

# Compares a current value to a baseline and calculates the absolute and percentage change.
def compare_values(
    current: float,
    baseline: float
) -> Dict[str, Any]:
    """Compare a current value to a baseline value."""

    absolute_change = current - baseline

    if baseline == 0:
        percentage_change = None
    else:
        percentage_change = (absolute_change / baseline) * 100

    return {
        "current": current,
        "baseline": baseline,
        "absolute_change": absolute_change,
        "percentage_change": (
            round(percentage_change, 2)
            if percentage_change is not None
            else None
        )
    }

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

    buckets: Dict[str, int] = {}

    current_bucket_start = start

    while current_bucket_start < end:
        current_bucket_end = current_bucket_start + timedelta(
            minutes=bucket_minutes
        )

        bucket_label = (
            f"{current_bucket_start.strftime('%H:%M')}-"
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
                f"{bucket_start.strftime('%H:%M')}-"
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
        "abandoned_calls": monitor_result["abandoned_calls_change"],
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
        "agent": summarize(agent_requests, agent_hours),
        "team_baseline": team,
        "comparison_note": "Team rates are request-weighted; requests/hour uses scheduled shift hours. These are descriptive signals, not employee performance ratings.",
    }


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

"""Monitor windows, period comparisons and the day-level tools.

Regression tests for the Phase 0 audit findings. Expected values are computed
here straight from data/*.json, not through tools.py.

Monitor semantics, verified against generate_demo_data.generate_monitor_day:
snapshots every 5 minutes from 08:00 to 17:00; each covers the 5 minutes
STARTING at its timestamp (an incident is applied to the snapshots whose hour
is the incident hour); answered/abandoned are cumulative within a day and
start from zero each morning. A window therefore counts the snapshots with
start <= timestamp < end.

Operating schedule, verified against the generator (WORK_START_HOUR = 8,
WORK_END_HOUR = 17) and the data: every request falls between 08:00 and
17:00 and every shift ends at 17:00. The 17:00 snapshot covers 17:00-17:05,
after closing, so operational figures use working hours only, unless
after-hours data is explicitly requested.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pytest

import tools

DATA = Path(__file__).resolve().parent.parent / "data"
SNAPSHOTS = sorted(json.loads((DATA / "monitor_snapshots.json").read_text()), key=lambda s: s["timestamp"])
REQUESTS = json.loads((DATA / "requests.json").read_text())
DAYS = sorted({s["timestamp"][:10] for s in SNAPSHOTS})


def _increments():
    out, last = {}, {}
    for s in SNAPSHOTS:
        day = s["timestamp"][:10]
        prev = last.get(day, {"answered_calls": 0, "abandoned_calls": 0})
        out[s["timestamp"]] = (s["answered_calls"] - prev["answered_calls"], s["abandoned_calls"] - prev["abandoned_calls"])
        last[day] = s
    return out


INC = _increments()


def in_hours(timestamp):
    return "08:00:00" <= timestamp[11:19] < "17:00:00"


def raw(start, end, after_hours=False):
    """Expected monitor figures for start <= t < end, from the raw snapshots."""
    s, e = datetime.fromisoformat(start), datetime.fromisoformat(end)
    rows = [x for x in SNAPSHOTS if s <= datetime.fromisoformat(x["timestamp"]) < e
            and (after_hours or in_hours(x["timestamp"]))]
    return {
        "snapshot_count": len(rows),
        "answered_calls": sum(INC[x["timestamp"]][0] for x in rows),
        "abandoned_calls": sum(INC[x["timestamp"]][1] for x in rows),
        "average_available_agents": round(sum(x["available_agents"] for x in rows) / len(rows), 2),
        "average_monitor_wait_time_minutes": round(sum(x["average_wait_time_minutes"] for x in rows) / len(rows), 2),
        "average_agents_on_shift": round(sum(x["agents_on_shift"] for x in rows) / len(rows), 2),
        "peak_agents_on_calls": max(x["agents_on_calls"] for x in rows),
    }


def assert_matches_raw(start, end):
    result, expected = tools.get_monitor_metrics(start, end), raw(start, end)
    for key, value in expected.items():
        assert result[key] == pytest.approx(value, abs=0.006), (start, end, key)
    assert result["abandoned_calls_change"] == result["abandoned_calls"]  # legacy alias
    assert result["answered_calls_change"] == result["answered_calls"]


# --- Monitor windows: hourly, daily, multi-day, midnight-crossing -----------

@pytest.mark.parametrize("day", DAYS)
def test_every_hour_matches_raw_snapshots(day):
    for hour in range(8, 17):
        assert_matches_raw(f"{day}T{hour:02d}:00:00", f"{day}T{hour + 1:02d}:00:00")


@pytest.mark.parametrize("day", DAYS)
def test_every_working_day_matches_raw_snapshots(day):
    assert_matches_raw(f"{day}T08:00:00", f"{day}T17:00:00")
    hours = sum(tools.get_monitor_metrics(f"{day}T{h:02d}:00:00", f"{day}T{h + 1:02d}:00:00")["abandoned_calls"]
                for h in range(8, 17))
    assert hours == tools.get_monitor_metrics(f"{day}T08:00:00", f"{day}T17:00:00")["abandoned_calls"]


def daily_window_sum(field, days):
    return sum(tools.get_monitor_metrics(f"{d}T08:00:00", f"{d}T17:00:00")[field] for d in days)


def test_multi_day_total_is_the_sum_of_days_not_the_last_days_counter():
    """Regression (audit R8-2): the old tool returned 53 for ten days."""
    result = tools.get_monitor_metrics("2026-08-25 08:00", "2026-09-07 17:00")
    assert result["abandoned_calls"] == raw("2026-08-25 08:00", "2026-09-07 17:00")["abandoned_calls"] == 628
    assert result["working_days"] == 10
    assert sum(d["abandoned_calls"] for d in result["per_day"]) == result["abandoned_calls"]
    assert result["abandoned_calls"] != SNAPSHOTS[-1]["abandoned_calls"]


@pytest.mark.parametrize("start, end, days", [
    ("2026-08-25 08:00", "2026-09-07 17:00", DAYS),
    ("2026-08-25 08:00", "2026-09-01 17:00", DAYS[:6]),   # audit R8-3 'week 1' (the old tool said 63)
    ("2026-09-02 08:00", "2026-09-07 17:00", DAYS[6:]),   # audit R8-3 'week 2' (the old tool said 52)
    ("2026-08-24 00:00", "2026-09-08 00:00", DAYS),       # midnight to midnight, weekends included
])
def test_multi_day_totals_equal_the_sum_of_daily_operational_windows(start, end, days):
    result = tools.get_monitor_metrics(start, end)
    for field in ("abandoned_calls", "answered_calls"):
        assert result[field] == daily_window_sum(field, days), field
    assert result["time_window_applied"] == "working hours 08:00-17:00 each day"


def test_daily_series_and_monitor_totals_agree():
    series = tools.get_daily_series("2026-08-25", "2026-09-07")
    assert series["totals"]["abandoned_calls"] == tools.get_monitor_metrics(
        "2026-08-25 08:00", "2026-09-07 17:00")["abandoned_calls"]


def test_after_hours_snapshots_are_excluded_visibly_not_silently():
    result = tools.get_monitor_metrics("2026-08-25 08:00", "2026-09-07 17:00")
    assert result["after_hours_snapshots_excluded"] == 9   # the 17:00 snapshots of the first nine days
    explicit = tools.get_monitor_metrics("2026-08-25 08:00", "2026-09-07 17:00", include_after_hours=True)
    assert explicit["abandoned_calls"] == raw("2026-08-25 08:00", "2026-09-07 17:00", after_hours=True)["abandoned_calls"] == 634
    assert explicit["after_hours_snapshots_excluded"] == 0
    assert explicit["time_window_applied"] == "all snapshots, including after hours"


def test_after_hours_only_window_says_what_was_excluded():
    result = tools.get_monitor_metrics("2026-08-25T17:00:00", "2026-08-25T18:00:00")
    assert result["snapshot_count"] == 0 and result["after_hours_snapshots_excluded"] == 1
    assert tools.get_monitor_metrics("2026-08-25T17:00:00", "2026-08-25T18:00:00",
                                     include_after_hours=True)["snapshot_count"] == 1


def test_working_day_windows_exclude_no_in_hours_activity():
    """The schedule check behind clipping: requests and shifts all fall inside 08:00-17:00."""
    assert all("08:00:00" <= r["request_time"][11:19] < "17:00:00" for r in REQUESTS)
    shifts = json.loads((DATA / "agent_shifts.json").read_text())
    assert all(s["shift_end"].endswith("17:00:00") and s["shift_start"][11:] >= "08:00:00" for s in shifts)
    for day in DAYS:  # a full-day window drops only the 17:00 closing snapshot
        assert tools.get_monitor_metrics(f"{day}T00:00:00", f"{day}T23:59:59")["after_hours_snapshots_excluded"] == 1


def test_midnight_crossing_window():
    assert_matches_raw("2026-08-25T16:00:00", "2026-08-26T09:00:00")
    result = tools.get_monitor_metrics("2026-08-25T16:00:00", "2026-08-26T09:00:00")
    assert [d["date"] for d in result["per_day"]] == ["2026-08-25", "2026-08-26"]
    # 25 Aug 16:00-16:55 plus 26 Aug 08:00-08:55; the 17:00 closing snapshot is excluded and reported
    assert result["snapshot_count"] == 12 + 12
    assert result["after_hours_snapshots_excluded"] == 1


def test_window_end_is_exclusive_and_start_inclusive():
    one = tools.get_monitor_metrics("2026-08-27T15:00:00", "2026-08-27T15:05:00")
    assert one["snapshot_count"] == 1
    assert tools.get_monitor_metrics("2026-08-27T15:00:00", "2026-08-27T15:00:00")["snapshot_count"] == 0


def test_staffing_incident_hour_contains_exactly_the_incident_snapshots():
    """The generator's capacity incident (27 Aug 15:00) is 8 agents on shift for 15:00-15:55."""
    result = tools.get_monitor_metrics("2026-08-27T15:00:00", "2026-08-27T16:00:00")
    assert result["min_agents_on_shift"] == 8 and result["average_agents_on_shift"] == 8.0
    assert result["average_available_agents"] == 0.33
    after = tools.get_monitor_metrics("2026-08-27T16:00:00", "2026-08-27T16:05:00")
    assert after["average_agents_on_shift"] == 12.0


def test_empty_window_message_is_unchanged():
    assert tools.get_monitor_metrics("2026-08-29T08:00:00", "2026-08-29T17:00:00") == {
        "start_time": "2026-08-29T08:00:00", "end_time": "2026-08-29T17:00:00",
        "snapshot_count": 0, "message": "No monitor data found for this period."}


def test_daily_metrics_use_the_same_rule():
    for day in DAYS:
        assert tools.get_daily_metrics(day)["abandoned_calls"] == raw(f"{day}T08:00:00", f"{day}T17:00:00")["abandoned_calls"]


# --- Periods with different numbers of working days --------------------------

def test_count_requests_reports_working_days():
    """Regression (audit R8-1): 1,199 vs 800 is 6 days vs 4, the same per day."""
    week1 = tools.count_requests("2026-08-25 08:00", "2026-09-01 17:00")
    week2 = tools.count_requests("2026-09-02 08:00", "2026-09-07 17:00")
    assert (week1["working_days"], week2["working_days"]) == (6, 4)
    assert week1["requests_per_working_day"] == 199.83 and week2["requests_per_working_day"] == 200.0
    assert "requests_per_working_day" not in tools.count_requests("2026-08-25T12:00:00", "2026-08-25T13:00:00")


def test_compare_values_is_unchanged_without_day_counts():
    assert tools.compare_values(45, 19) == {"current": 45, "baseline": 19, "absolute_change": 26, "percentage_change": 136.84}


def test_compare_values_per_day():
    result = tools.compare_values(800, 1199, current_days=4, baseline_days=6)
    assert result["percentage_change"] == -33.28  # the misleading total comparison is still reported
    assert result["per_day_percentage_change"] == 0.08
    assert "different numbers of days" in result["note"]


@pytest.mark.parametrize("kwargs", [{"current_days": 4}, {"baseline_days": 6}, {"current_days": 0, "baseline_days": 6}])
def test_compare_values_rejects_incomplete_day_counts(kwargs):
    with pytest.raises(ValueError):
        tools.compare_values(800, 1199, **kwargs)


def test_daily_series_totals_and_per_day_values():
    series = tools.get_daily_series("2026-08-25", "2026-09-07")
    assert series["working_days"] == 10 and [d["date"] for d in series["days"]] == DAYS
    assert series["totals"]["requests"] == len(REQUESTS)
    for row in series["days"]:
        assert row["requests"] == sum(r["request_time"][:10] == row["date"] for r in REQUESTS)
        assert row["abandoned_calls"] == raw(f"{row['date']}T08:00:00", f"{row['date']}T17:00:00")["abandoned_calls"]
    assert series["per_working_day"]["requests"] == round(len(REQUESTS) / 10, 2)


def test_daily_series_on_a_weekend_is_empty():
    series = tools.get_daily_series("2026-08-29", "2026-08-30")
    assert series["working_days"] == 0 and series["days"] == []


# --- Multi-day time buckets ----------------------------------------------------

def test_single_day_bucket_labels_are_unchanged():
    counts = tools.get_requests_by_time_bucket("2026-08-25T12:00:00", "2026-08-25T13:00:00", 10)["request_counts"]
    assert list(counts)[:2] == ["12:00-12:10", "12:10-12:20"] and sum(counts.values()) == 45


def test_multi_day_buckets_are_labelled_by_date_and_not_merged():
    """Regression (audit R8-5/R8-6): labels used to repeat each day and add up."""
    counts = tools.get_requests_by_time_bucket("2026-08-25 08:00", "2026-08-26 17:00", 60)["request_counts"]
    assert counts["2026-08-25 12:00-13:00"] == 45 and counts["2026-08-26 14:00-15:00"] == 45
    assert sum(counts.values()) == sum("2026-08-25" <= r["request_time"][:10] <= "2026-08-26" for r in REQUESTS)


# --- Incident discovery and capacity -----------------------------------------

def test_volume_anomalies_find_the_three_planted_incidents():
    result = tools.detect_volume_anomalies("2026-08-25", "2026-09-07")
    found = {(a["date"], a["start_time"][11:16]) for a in result["anomalies"]}
    assert found == {("2026-08-25", "12:00"), ("2026-08-26", "14:00"), ("2026-08-27", "15:00")}
    assert result["working_days_checked"] == 10


def test_capacity_context_shows_the_staffing_incident():
    """Regression (audit R2-1/R2-2): the staffing drop was invisible to the agent."""
    context = tools.get_capacity_context("2026-08-27T15:00:00", "2026-08-27T16:00:00")
    assert context["window"]["average_agents_on_shift"] == 8.0
    assert context["previous_window"]["average_agents_on_shift"] == 12.0
    assert context["typical_same_window"]["average_agents_on_shift"] == 12.0
    assert context["difference_from_typical"]["average_agents_on_shift"] == -4.0
    assert context["difference_from_typical"]["requests"] > 20  # demand rose too


def test_capacity_context_for_a_demand_only_incident():
    context = tools.get_capacity_context("2026-08-25T12:00:00", "2026-08-25T13:00:00")
    assert context["window"]["average_agents_on_shift"] == 12.0
    assert context["difference_from_typical"]["average_agents_on_shift"] == 0.0
    assert context["difference_from_typical"]["requests"] > 20


def test_capacity_context_at_opening_has_no_previous_window():
    assert tools.get_capacity_context("2026-08-25T08:00:00", "2026-08-25T09:00:00")["previous_window"] is None


def test_capacity_context_rejects_multi_day_windows():
    with pytest.raises(ValueError):
        tools.get_capacity_context("2026-08-25T08:00:00", "2026-08-26T09:00:00")


# --- Sample sizes and period labels --------------------------------------------

def test_one_day_agent_rates_are_flagged_as_low_sample():
    """Regression (audit R6-2): A04's 9 requests on one day were read as a period-wide pattern."""
    day = tools.get_agent_comparison("2026-09-07", "2026-09-07")
    a04 = next(a for a in day["agents"] if a["agent_id"] == "A04")
    assert a04["handled_requests"] == 9 and a04["low_sample"] is True
    assert all(entry["low_sample"] for entry in a04["by_classification"].values())
    assert day["period_label"].startswith("2026-09-07 (1 working day)")

    period = tools.get_agent_comparison("2026-08-25", "2026-09-04")
    assert period["working_days"] == 9 and "9 working days" in period["period_label"]
    assert next(a for a in period["agents"] if a["agent_id"] == "A04")["low_sample"] is False


def test_agent_performance_carries_period_and_sample_size():
    result = tools.get_agent_performance("A04", "2026-09-07", "2026-09-07")
    assert result["agent"]["low_sample"] is True and "1 working day" in result["period_label"]

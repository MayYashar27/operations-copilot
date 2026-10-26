"""The tools vs the independent oracle, over a grid of windows.

Agreement here means the tools compute what they claim. Phase 0 pinned two
contract issues (multi-day monitor totals and merged multi-day buckets) as
strict xfail tests; both were fixed on 2026-10-26 and are now normal tests.
The three day-level tools added with the fix are checked against the oracle's
own monitor and request calculations.
"""

import pytest

import tools
from evals import oracle
from evals.trace_checks import _close

DAYS = [d.isoformat() for d in oracle.data_dates()]
HOURLY = [(f"{d}T{h:02d}:00:00", f"{d}T{h + 1:02d}:00:00") for d in DAYS[:3] for h in range(8, 17)]
DAILY = [(f"{d}T08:00:00", f"{d}T17:00:00") for d in DAYS]
MULTI = [(f"{DAYS[0]} 08:00", f"{DAYS[-1]} 17:00"), (f"{DAYS[0]} 08:00", f"{DAYS[5]} 17:00")]
WINDOWS = HOURLY + DAILY + MULTI


def same(tool_result, oracle_result):
    shared = [k for k in oracle_result if k in tool_result]
    return all(_close(tool_result[k], oracle_result[k]) for k in shared)


@pytest.mark.parametrize("name", ["count_requests", "get_requests_by_classification", "get_average_wait_time",
                                  "get_requests_by_status", "get_transfers_by_destination", "get_monitor_metrics"])
def test_window_tools_agree(name):
    for start, end in WINDOWS:
        assert same(getattr(tools, name)(start, end), oracle.REPLAY[name](start, end)), (name, start, end)


@pytest.mark.parametrize("classification", oracle.CLASSIFICATIONS)
def test_classification_tools_agree(classification):
    for start, end in DAILY + HOURLY[:9]:
        for name in ("get_classification_count", "get_classification_status_breakdown", "get_request_details"):
            assert same(getattr(tools, name)(start, end, classification),
                        oracle.REPLAY[name](start, end, classification)), (name, start, end)


@pytest.mark.parametrize("bucket", [5, 15, 60])
def test_time_buckets_agree(bucket):
    for start, end in DAILY[:3] + MULTI:
        assert same(tools.get_requests_by_time_bucket(start, end, bucket),
                    oracle.get_requests_by_time_bucket(start, end, bucket))


@pytest.mark.parametrize("agent_id", oracle.roster())
def test_agent_tools_agree(agent_id):
    for start, end in [(DAYS[0], DAYS[-1]), (DAYS[-1], DAYS[-1]), (DAYS[0], DAYS[4])]:
        assert same(tools.get_agent_performance(agent_id, start, end), oracle.get_agent_performance(agent_id, start, end))
        assert same(tools.get_agent_daily_trends(agent_id, start, end), oracle.get_agent_daily_trends(agent_id, start, end))
        assert same(tools.get_agent_request_evidence(agent_id, start, end, limit=100),
                    oracle.get_agent_request_evidence(agent_id, start, end, limit=100))
    real = tools.detect_agent_performance_signals(agent_id, DAYS[0], DAYS[-1])
    mine = oracle.detect_agent_performance_signals(agent_id, DAYS[0], DAYS[-1])
    assert {s["code"] for s in real["signals"]} == set(mine["signal_codes"])
    assert same(real["periods"], mine["periods"])


def test_daily_series_agrees_with_oracle():
    series = tools.get_daily_series(DAYS[0], DAYS[-1])
    for row in series["days"]:
        start, end = f"{row['date']}T08:00:00", f"{row['date']}T17:00:00"
        assert row["requests"] == oracle.count_requests(start, end)["request_count"]
        assert row["abandoned_calls"] == oracle.daily_abandoned_in_hours(row["date"])
        assert row["average_agents_on_shift"] == oracle.get_monitor_metrics(start, end)["average_agents_on_shift"]


def test_capacity_context_agrees_with_oracle():
    for start, end in HOURLY[:9]:
        context = tools.get_capacity_context(start, end)
        assert same(context["window"] | {"start_time": start, "end_time": end},
                    {k: v for k, v in oracle.get_monitor_metrics(start, end).items()
                     if k in ("average_agents_on_shift", "average_available_agents", "abandoned_calls")})


def test_agent_comparison_agrees():
    for start, end in [(DAYS[0], DAYS[-1]), (DAYS[-1], DAYS[-1]), (DAYS[0], DAYS[8])]:
        assert same(tools.get_agent_comparison(start, end), oracle.get_agent_comparison(start, end))


def test_multi_day_abandoned_calls_is_a_total():
    """Was a pinned known issue in Phase 0 (fixed 2026-10-26)."""
    start, end = MULTI[0]
    assert tools.get_monitor_metrics(start, end)["abandoned_calls"] == oracle.abandoned_calls_between(start, end)
    assert tools.get_monitor_metrics(start, end)["abandoned_calls_change"] == oracle.abandoned_calls_between(start, end)


def test_multi_day_buckets_are_distinguishable_by_day():
    """Was a pinned known issue in Phase 0 (fixed 2026-10-26)."""
    start, end = MULTI[0]
    counts = tools.get_requests_by_time_bucket(start, end, 60)["request_counts"]
    assert len(counts) >= 9 * len(DAYS)  # one bucket per working hour per day


def test_request_and_monitor_windows_use_the_same_end_rule():
    """Both exclude the end time since the 2026-10-26 fix."""
    start, end = HOURLY[0]
    assert tools.get_monitor_metrics(start, end)["snapshot_count"] == 12  # 08:00 .. 08:55


def test_legacy_contract_reproduces_the_phase0_error():
    """The legacy replay used for runs saved before the fix still yields the old 53."""
    assert oracle.legacy_get_monitor_metrics(*MULTI[0])["abandoned_calls_change"] == 53

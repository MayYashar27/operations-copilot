"""The 16 tools vs the independent oracle, over a grid of windows.

Agreement here means the tools compute what they claim. The xfail tests pin
two contract issues found in Phase 0: the tools behave as coded, but a
plain reading of their output for multi-day windows is wrong. They are
strict, so if a tool is changed to fix them, the test turns red as a reminder
to update this audit.
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


def test_agent_comparison_agrees():
    for start, end in [(DAYS[0], DAYS[-1]), (DAYS[-1], DAYS[-1]), (DAYS[0], DAYS[8])]:
        assert same(tools.get_agent_comparison(start, end), oracle.get_agent_comparison(start, end))


@pytest.mark.xfail(strict=True, reason="KNOWN ISSUE: monitor counters are cumulative per day; over a multi-day "
                                       "window abandoned_calls_change is last-day counter minus first, not the total")
def test_multi_day_abandoned_calls_change_is_a_total():
    start, end = MULTI[0]
    assert tools.get_monitor_metrics(start, end)["abandoned_calls_change"] == oracle.abandoned_calls_between(start, end)


@pytest.mark.xfail(strict=True, reason="KNOWN ISSUE: hourly buckets over several days are labelled HH:MM, so "
                                       "each label sums all days; output looks like one day's profile")
def test_multi_day_buckets_are_distinguishable_by_day():
    start, end = MULTI[0]
    counts = tools.get_requests_by_time_bucket(start, end, 60)["request_counts"]
    assert len(counts) >= 9 * len(DAYS)  # one bucket per working hour per day


def test_request_and_monitor_windows_use_different_end_rules():
    """Documented, not a failure: request tools exclude the end time, the monitor tool includes it."""
    start, end = HOURLY[0]
    snapshot_count = tools.get_monitor_metrics(start, end)["snapshot_count"]
    assert snapshot_count == 13  # 08:00 through 09:00 inclusive at 5-minute intervals

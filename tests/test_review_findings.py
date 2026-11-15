"""Regression tests for the defects found in the live S30 review (2026-11-15).

1. A trend-only agent problem (A07) was invisible in the broad-review evidence.
2. Category figures for the whole period were reported as later-half figures.
3. An hour's total (45) was reported as a count of one category (40).
4. Incident hours without a dominant category were not looked at in detail.

The tests check the evidence the agent receives and the answer checks. They
cannot show that Claude uses the evidence well; that is what live runs are for.
"""

import importlib
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")  # import only; never called

from langchain_core.messages import AIMessage  # noqa: E402

import answer_checks  # noqa: E402
import langgraph_agent  # noqa: E402
import tools  # noqa: E402
from api.copilot_runner import langgraph_question_runner  # noqa: E402
from tests.test_agent_tools import FixedResult, ScriptedModel  # noqa: E402

RANGE = ("2026-08-25", "2026-09-07")


# --- 1. Trend-only problems ---------------------------------------------------------

def test_agent_comparison_carries_trend_signals_for_every_agent():
    agents = {a["agent_id"]: a for a in tools.get_agent_comparison(*RANGE)["agents"]}
    assert len(agents) == 15 and all("trend_signals" in a for a in agents.values())
    assert agents["A07"]["trend_signals"] == [
        "RISING_TRANSFER_RATE", "FALLING_HANDLING_TIME", "FASTER_HANDLING_WITH_MORE_TRANSFERS"]
    assert set(agents["A04"]["trend_signals"]) == {"HIGH_TRANSFER_RATE_VS_PEERS", "RISING_TRANSFER_RATE"}
    assert agents["A09"]["trend_signals"] == ["HIGH_TRANSFER_RATE_VS_PEERS"]


def test_a07_is_unremarkable_on_period_averages_alone():
    """Why the signal is needed: A07's 10-day rate is close to the team's."""
    comparison = tools.get_agent_comparison(*RANGE)
    a07 = next(a for a in comparison["agents"] if a["agent_id"] == "A07")
    assert abs(a07["transfer_rate_percent"] - comparison["team_transfer_rate_percent"]) < 2


def test_trend_signals_match_the_per_agent_signal_tool():
    for agent in tools.get_agent_comparison(*RANGE)["agents"]:
        expected = [s["code"] for s in tools.detect_agent_performance_signals(agent["agent_id"], *RANGE)["signals"]]
        assert agent["trend_signals"] == expected


def test_short_ranges_have_no_trend_signals_and_existing_fields_are_unchanged():
    day = tools.get_agent_comparison("2026-09-07", "2026-09-07")
    assert "trend_signals_note" not in day and all("trend_signals" not in a for a in day["agents"])
    a04 = next(a for a in day["agents"] if a["agent_id"] == "A04")
    assert (a04["handled_requests"], a04["transferred_requests"], a04["transfer_rate_percent"]) == (9, 8, 88.89)


def test_broad_review_prefetch_delivers_trend_signals_to_claude(monkeypatch):
    # Patch the module the runner will actually import: another test file drops
    # langgraph_agent from sys.modules, so the copy imported above can be stale.
    agent = importlib.import_module("langgraph_agent")
    model = ScriptedModel([AIMessage(content="Done.")])
    monkeypatch.setattr(agent, "model_with_tools", model)
    monkeypatch.setattr(agent, "final_investigation_model", FixedResult())
    outcome = langgraph_question_runner(
        "What are the warning signs over the last 10 working days?\n\nContext: The manager is viewing the shift "
        "of 2026-09-07; treat 'today' or 'this shift' as that date.")
    comparison = next(s for s in outcome["trace"] if s["tool"] == "get_agent_comparison")
    a07 = next(a for a in comparison["result"]["agents"] if a["agent_id"] == "A07")
    assert "FASTER_HANDLING_WITH_MORE_TRANSFERS" in a07["trend_signals"]


def test_prompt_covers_trend_signals_and_hour_contents():
    prompt = langgraph_agent.SYSTEM_PROMPT
    assert "OR has trend_signals" in prompt
    assert "top_subjects" in prompt and "no single classification dominates" in prompt


# --- 2. Per-category figures by period --------------------------------------------------

def test_signal_periods_include_categories_for_the_same_period():
    periods = tools.detect_agent_performance_signals("A04", *RANGE)["periods"]
    later = periods["later"]["by_classification"]
    assert {c: v["transfer_rate_percent"] for c, v in later.items()} == {
        "general_information": 60.0, "login_issue": 52.63, "payment_issue": 60.0, "technical_issue": 58.33}
    for name in ("earlier", "later", "peers_later"):
        period = periods[name]
        assert sum(v["requests"] for v in period["by_classification"].values()) == period["requests"]
        assert sum(v["transferred"] for v in period["by_classification"].values()) == period["transfers"]


# --- 3. An hour's total attributed to one category ---------------------------------

def test_anomalies_break_down_each_unusual_hour():
    anomalies = {a["date"]: a for a in tools.detect_volume_anomalies(*RANGE)["anomalies"]}
    assert anomalies["2026-08-25"]["request_count"] == 45
    assert anomalies["2026-08-25"]["requests_by_classification"]["login_issue"] == 40
    for a in anomalies.values():
        assert sum(a["requests_by_classification"].values()) == a["request_count"]


def _anomaly_evidence():
    return [{"tool": "detect_volume_anomalies", "args": {}, "result": tools.detect_volume_anomalies(*RANGE)}]


def _result(*facts):
    base = {f: [] for f in answer_checks.RESULT_FIELDS}
    base.update(observed_facts=list(facts), confirmed_root_cause=None)
    return base


def test_answer_check_flags_a_total_stated_as_a_category_count():
    sentence = "On 2026-08-25 at 12:00–13:00, 45 login_issue requests arrived in one hour."
    warnings = answer_checks.check_answer(_result(sentence), None, _anomaly_evidence())
    assert [w["kind"] for w in warnings] == ["category_count"]


def test_answer_check_accepts_correct_category_counts():
    evidence = _anomaly_evidence() + [{
        "tool": "get_classification_status_breakdown", "args": {},
        "result": tools.get_classification_status_breakdown("2026-08-25T12:00:00", "2026-08-25T13:00:00", "login_issue")}]
    facts = ["40 of 45 requests were login_issue: 40 login_issue requests in the hour.",
             "36 of the 40 login requests mention an update.",
             "17 login_issue requests were resolved and 23 were transferred."]
    warnings = [w for w in answer_checks.check_answer(_result(*facts), None, evidence) if w["kind"] == "category_count"]
    assert warnings == []


# --- 4. What each incident hour was about ---------------------------------------------

def test_mixed_category_incident_shows_its_subjects():
    aug26 = next(a for a in tools.detect_volume_anomalies(*RANGE)["anomalies"] if a["date"] == "2026-08-26")
    subjects = [s["subject"] for s in aug26["top_subjects"]]
    assert len(subjects) == 5
    assert any("Mobile app" in s for s in subjects) and "Payment button not responding" in subjects
    counts = [s["requests"] for s in aug26["top_subjects"]]
    assert counts == sorted(counts, reverse=True)

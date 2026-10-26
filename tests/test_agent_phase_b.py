"""Phase B: the agent's tools and prompts for the Phase 0 audit findings.

These tests check what the agent is GIVEN (tools, schemas, instructions) and
that the graph runs with the new tools. They cannot show that Claude now
reasons correctly: that needs live runs (evals/scenarios S03, S12, S16, S29,
S30). Claude is replaced by a scripted fake; no paid calls.
"""

import json
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")  # import only; never called

from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402

import langgraph_agent  # noqa: E402
import tools  # noqa: E402
from api.copilot_runner import langgraph_question_runner  # noqa: E402
from tests.test_agent_tools import FixedResult, ScriptedModel, call  # noqa: E402

NEW_TOOLS = ("get_daily_series", "detect_volume_anomalies", "get_capacity_context")


def test_nineteen_tools_are_bound():
    names = [t.name for t in langgraph_agent.TOOLS]
    assert len(names) == len(set(names)) == 19
    assert set(NEW_TOOLS) <= set(names)


def test_new_tool_wrappers_return_the_deterministic_results():
    tm = langgraph_agent.TOOL_MAP
    assert tm["get_daily_series"].invoke({"start_date": "2026-08-25", "end_date": "2026-09-07"}) == \
        tools.get_daily_series("2026-08-25", "2026-09-07")
    assert tm["detect_volume_anomalies"].invoke({"start_date": "2026-08-25", "end_date": "2026-09-07"}) == \
        tools.detect_volume_anomalies("2026-08-25", "2026-09-07")
    window = {"start_time": "2026-08-27T15:00:00", "end_time": "2026-08-27T16:00:00"}
    assert tm["get_capacity_context"].invoke(window) == tools.get_capacity_context(**window)


def test_existing_tool_calls_behave_as_before():
    tm = langgraph_agent.TOOL_MAP
    assert tm["compare_values"].invoke({"current": 45, "baseline": 19})["percentage_change"] == 136.84
    assert "per_day_percentage_change" not in tm["compare_values"].invoke({"current": 45, "baseline": 19})
    hour = {"start_time": "2026-08-25T12:00:00", "end_time": "2026-08-25T13:00:00"}
    assert tm["get_monitor_metrics"].invoke(hour) == tools.get_monitor_metrics(**hour)


def test_optional_arguments_reach_the_tools():
    tm = langgraph_agent.TOOL_MAP
    fair = tm["compare_values"].invoke({"current": 800, "baseline": 1199, "current_days": 4, "baseline_days": 6})
    assert fair["per_day_percentage_change"] == 0.08
    window = {"start_time": "2026-08-25 08:00", "end_time": "2026-09-07 17:00"}
    assert tm["get_monitor_metrics"].invoke(window)["abandoned_calls"] == 628
    assert tm["get_monitor_metrics"].invoke({**window, "include_after_hours": True})["abandoned_calls"] == 634


def test_tool_descriptions_explain_windows_samples_and_fair_comparison():
    doc = {t.name: t.description for t in langgraph_agent.TOOLS}
    assert "working hours" in doc["get_monitor_metrics"] and "several days" in doc["get_monitor_metrics"]
    assert "current_days" in doc["compare_values"]
    assert "low_sample" in doc["get_agent_comparison"] and "period_label" in doc["get_agent_comparison"]
    assert "staffing" in doc["get_capacity_context"]
    assert "detect_volume_anomalies" in doc["get_requests_by_time_bucket"]


def test_system_prompt_rules_for_each_audit_finding():
    prompt = langgraph_agent.SYSTEM_PROMPT
    assert "compare per working day" in prompt                     # audit R8-1 unequal periods
    assert "a single day is never a pattern" in prompt              # audit R6-2 one day -> period
    assert "low_sample" in prompt                                    # small samples
    assert "every one outside the normal range" in prompt           # audit R8-4 omitted outlier
    assert "Do not add up or regroup numbers yourself" in prompt     # audit R1-1, R6-4
    assert "BOTH sides" in prompt and "get_capacity_context" in prompt  # audit R2-1 staffing
    assert "get_daily_series" in prompt and "detect_volume_anomalies" in prompt  # audit R8-7 broad reviews
    assert "Never guess identifiers" in prompt                       # earlier rules still present


def test_final_answer_prompt_requires_scope_and_sample_size():
    prompt = langgraph_agent.FINAL_INVESTIGATION_PROMPT
    assert "never \"consistently\" or \"across the period\"" in prompt
    assert "per-working-day values" in prompt
    assert "confirmed_root_cause must be null" in prompt


def test_graph_runs_a_multi_day_review_with_the_new_tools(monkeypatch):
    model = ScriptedModel([
        AIMessage(content="", tool_calls=[
            call("get_daily_series", {"start_date": "2026-08-25", "end_date": "2026-09-07"}, 1),
            call("detect_volume_anomalies", {"start_date": "2026-08-25", "end_date": "2026-09-07"}, 2),
        ]),
        AIMessage(content="", tool_calls=[
            call("get_capacity_context", {"start_time": "2026-08-27T15:00:00", "end_time": "2026-08-27T16:00:00"}, 3),
            # a mistake the model might make: a multi-day window for a one-day tool
            call("get_capacity_context", {"start_time": "2026-08-25T08:00:00", "end_time": "2026-08-26T17:00:00"}, 4),
        ]),
        AIMessage(content="Three incident hours; staffing fell on 27 Aug."),
    ])
    monkeypatch.setattr(langgraph_agent, "model_with_tools", model)
    monkeypatch.setattr(langgraph_agent, "final_investigation_model", FixedResult())

    # A question no pre-fetch rule matches, so only the model's own calls appear
    # (pre-fetching is tested in test_agent_phase_c.py).
    outcome = langgraph_question_runner("Summarise what the data shows.")
    assert outcome["evidence_plan"]["executed"] == []

    assert [s["tool"] for s in outcome["trace"]] == [
        "get_daily_series", "detect_volume_anomalies", "get_capacity_context", "get_capacity_context"]
    assert len(outcome["trace"][1]["result"]["anomalies"]) == 3
    assert outcome["trace"][2]["result"]["window"]["average_agents_on_shift"] == 8.0
    assert "one day" in outcome["trace"][3]["result"]["error"]  # recoverable, run continued

    third_turn = model.seen[2]
    errors = [m for m in third_turn if isinstance(m, ToolMessage) and m.status == "error"]
    assert len(errors) == 1 and "get_daily_series" in json.loads(errors[0].content)["error"]

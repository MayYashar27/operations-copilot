"""Regression tests for the 'A001' failure found in live testing.

Question: "Which agents had the highest transfer rates on September 7, 2026,
and what might explain the differences between them? Are the higher transfer
rates related to specific request categories?"

Claude guessed agent IDs A001..A010 (no tool exposed the real IDs), the tool
raised, and the uncaught error aborted the whole graph. No paid calls here:
Claude is replaced by a scripted fake model.
"""

import json
import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")  # import only; never called

from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402

import langgraph_agent  # noqa: E402
import tools  # noqa: E402
from api.copilot_runner import InvestigationRunner, PartialRunError, langgraph_question_runner  # noqa: E402
from api.copilot_store import JsonInvestigationStore  # noqa: E402

DATE = "2026-09-07"
QUESTION = (
    "Which agents had the highest transfer rates on September 7, 2026, and what might explain "
    "the differences between them? Are the higher transfer rates related to specific request categories?"
)


def call(name, args, i):
    return {"name": name, "args": args, "id": f"call_{i}", "type": "tool_call"}


class ScriptedModel:
    """Stands in for Claude: returns pre-written messages and records what it was shown."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.seen = []

    def invoke(self, messages):
        self.seen.append(messages)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FixedResult:
    def invoke(self, messages):
        return langgraph_agent.InvestigationResult(
            observed_facts=["A04 had the highest transfer rate (88.89%)."],
            supported_patterns=[], hypotheses=[], confirmed_root_cause=None,
            missing_evidence=[], recommendations=[],
        )


# ---------------------------------------------------------
# The missing capability: comparing all agents
# ---------------------------------------------------------

def test_comparison_covers_every_agent_sorted_by_transfer_rate():
    result = tools.get_agent_comparison(DATE, DATE)
    ids = [a["agent_id"] for a in result["agents"]]
    assert sorted(ids) == tools.known_agent_ids() == [f"A{i:02d}" for i in range(1, 16)]
    rates = [a["transfer_rate_percent"] for a in result["agents"]]
    assert rates == sorted(rates, reverse=True)
    assert result["team_transfer_rate_percent"] == 30.5


def test_comparison_matches_get_agent_performance_for_every_agent():
    comparison = tools.get_agent_comparison(DATE, DATE)
    for agent in comparison["agents"]:
        single = tools.get_agent_performance(agent["agent_id"], DATE, DATE)["agent"]
        assert agent["transfer_rate_percent"] == single["transfer_rate_percent"]
        assert agent["average_handling_time_minutes"] == single["average_handling_time_minutes"]
        assert agent["handled_requests"] == single["handled_requests"]


def test_comparison_breaks_transfers_down_by_category():
    for agent in tools.get_agent_comparison(DATE, DATE)["agents"]:
        cats = agent["by_classification"].values()
        assert sum(c["requests"] for c in cats) == agent["handled_requests"]
        assert sum(c["transferred"] for c in cats) == agent["transferred_requests"]


# ---------------------------------------------------------
# Invented identifiers
# ---------------------------------------------------------

@pytest.mark.parametrize("bad_id", ["A001", "A16", "agent_4", "", "a04"])
def test_invalid_agent_ids_are_rejected_with_the_valid_list(bad_id):
    with pytest.raises(ValueError) as error:
        tools.validate_agent_id(bad_id)
    assert "Valid agent IDs: A01, A02" in str(error.value)
    assert "get_agent_comparison" in str(error.value)


@pytest.mark.parametrize("tool_name", [
    "get_agent_performance", "get_agent_daily_trends", "detect_agent_performance_signals", "get_agent_request_evidence",
])
def test_every_per_agent_tool_validates_its_id(tool_name):
    with pytest.raises(ValueError, match="Unknown agent_id 'A001'"):
        langgraph_agent.TOOL_MAP[tool_name].invoke({"agent_id": "A001", "start_date": DATE, "end_date": DATE})


# ---------------------------------------------------------
# Recovery: a failing tool call no longer aborts the graph
# ---------------------------------------------------------

def test_execute_tools_returns_errors_and_still_runs_the_other_calls():
    state = {"messages": [AIMessage(content="", tool_calls=[
        call("get_agent_performance", {"agent_id": "A001", "start_date": DATE, "end_date": DATE}, 1),
        call("get_requests_by_status", {"start_time": f"{DATE}T08:00:00", "end_time": f"{DATE}T17:00:00"}, 2),
        call("no_such_tool", {}, 3),
    ])]}
    messages = langgraph_agent.execute_tools(state)["messages"]

    assert [m.status for m in messages] == ["error", "success", "error"]
    assert "Valid agent IDs" in json.loads(messages[0].content)["error"]
    assert json.loads(messages[1].content)["statuses"] == {"transferred": 61, "resolved": 139}


def test_exact_question_recovers_from_invented_ids(monkeypatch):
    model = ScriptedModel([
        # 1. What Claude did in the live run: guess IDs.
        AIMessage(content="", tool_calls=[
            call("get_agent_performance", {"agent_id": f"A00{i}", "start_date": DATE, "end_date": DATE}, i) for i in range(1, 4)
        ]),
        # 2. After reading the errors, use the comparison tool.
        AIMessage(content="", tool_calls=[call("get_agent_comparison", {"start_date": DATE, "end_date": DATE}, 9)]),
        # 3. Answer.
        AIMessage(content="A04 had the highest transfer rate."),
    ])
    monkeypatch.setattr(langgraph_agent, "model_with_tools", model)
    monkeypatch.setattr(langgraph_agent, "final_investigation_model", FixedResult())

    outcome = langgraph_question_runner(QUESTION)

    assert outcome["result"]["observed_facts"] == ["A04 had the highest transfer rate (88.89%)."]
    tools_called = [s["tool"] for s in outcome["trace"]]
    assert tools_called == ["get_agent_performance"] * 3 + ["get_agent_comparison"]
    assert all("Unknown agent_id" in s["result"]["error"] for s in outcome["trace"][:3])
    assert outcome["trace"][3]["result"]["agents"][0]["agent_id"] == "A04"

    # Claude was actually shown the errors (with the valid IDs) before recovering.
    second_turn = model.seen[1]
    errors = [m for m in second_turn if isinstance(m, ToolMessage) and m.status == "error"]
    assert len(errors) == 3 and "A01, A02" in errors[0].content


def test_failed_run_keeps_the_tool_calls_made_before_the_failure(monkeypatch, tmp_path):
    model = ScriptedModel([
        AIMessage(content="", tool_calls=[call("get_agent_comparison", {"start_date": DATE, "end_date": DATE}, 1)]),
        RuntimeError("Simulated Anthropic API outage"),
    ])
    monkeypatch.setattr(langgraph_agent, "model_with_tools", model)

    with pytest.raises(PartialRunError) as error:
        langgraph_question_runner(QUESTION)
    assert [s["tool"] for s in error.value.partial["trace"]] == ["get_agent_comparison"]

    # Through the runner, the failed record keeps the trace and the real cause.
    model.responses = [
        AIMessage(content="", tool_calls=[call("get_agent_comparison", {"start_date": DATE, "end_date": DATE}, 1)]),
        RuntimeError("Simulated Anthropic API outage"),
    ]
    store = JsonInvestigationStore(tmp_path / "examples", tmp_path / "local")
    runner = InvestigationRunner(store, tmp_path, run_question=langgraph_question_runner,
                                 spawn=lambda work: work(), context=lambda d: None)
    record = store.get(runner.start_question(QUESTION, DATE).id)
    assert record.status == "failed"
    assert record.error.type == "RuntimeError"
    assert [s.tool for s in record.trace] == ["get_agent_comparison"]


def test_tool_docs_and_prompt_point_claude_to_real_ids():
    doc = langgraph_agent.TOOL_MAP["get_agent_performance"].description
    assert "A01" in doc and "get_agent_comparison" in doc
    assert "Never guess identifiers" in langgraph_agent.SYSTEM_PROMPT

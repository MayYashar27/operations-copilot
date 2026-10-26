"""Phase C: deterministic evidence pre-fetching and non-blocking answer checks.

Planner and checks are pure Python and tested directly. Graph tests replace
Claude with a scripted fake; no paid calls. These show that the right
evidence reaches Claude and that warnings are recorded. Whether Claude then
reasons correctly can only be shown by live runs (evals/scenarios).
"""

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")  # import only; never called

from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402

import answer_checks  # noqa: E402
import evidence_planner  # noqa: E402
import langgraph_agent  # noqa: E402
import tools  # noqa: E402
from api.copilot_runner import InvestigationRunner, langgraph_question_runner  # noqa: E402
from api.copilot_store import JsonInvestigationStore  # noqa: E402
from api.schemas import InvestigationRecord  # noqa: E402
from tests.test_agent_tools import FixedResult, ScriptedModel, call  # noqa: E402

DAYS = tools.list_working_days("0001-01-01", "9999-12-31")
CONTEXT = ("\n\nContext: The manager is viewing the shift of {d}; treat 'today' or 'this shift' as that date. "
           "Available data covers working days 2026-08-25 to 2026-09-07, 08:00-17:00.")


def plan(question, viewing="2026-09-07"):
    return evidence_planner.plan(question + CONTEXT.format(d=viewing), DAYS)


def tools_of(p):
    return [c["tool"] for c in p["calls"]]


# --- Planner: intent and scope, not one fixed route ------------------------------

def test_spike_hour_gets_capacity_context():
    p = plan("There was an unusually high workload on 2026-08-27 between 15:00 and 16:00. Investigate what happened.")
    assert tools_of(p) == ["get_capacity_context"]
    assert p["calls"][0]["args"] == {"start_time": "2026-08-27T15:00:00", "end_time": "2026-08-27T16:00:00"}


def test_broad_review_gets_day_series_anomalies_agents_and_drill_down():
    """Regression (audit R8-7): the 10-day review missed all three incident hours."""
    p = plan("Looking at the last 10 working days, what are the most important warning signs?")
    assert tools_of(p) == ["get_daily_series", "detect_volume_anomalies", "get_agent_comparison"]
    assert p["calls"][0]["args"] == {"start_date": "2026-08-25", "end_date": "2026-09-07"}
    assert p["drill_into_anomalies"] is True


def test_multi_day_staffing_question_without_review_words_still_gets_evidence():
    p = plan("Were we understaffed at any point between Aug 25 and Aug 28?")
    assert tools_of(p) == ["get_daily_series", "detect_volume_anomalies"] and p["drill_into_anomalies"]
    assert p["scope"]["start_date"] == "2026-08-25" and p["scope"]["end_date"] == "2026-08-28"


def test_single_day_staffing_question_without_an_hour():
    p = plan("Why were customers waiting so long this afternoon?", viewing="2026-08-27")
    assert tools_of(p) == ["get_daily_series", "detect_volume_anomalies"] and p["drill_into_anomalies"]
    assert p["calls"][0]["args"] == {"start_date": "2026-08-27", "end_date": "2026-08-27"}


def test_unequal_period_question_gets_the_day_series():
    """Regression (audit R8-1)."""
    p = plan("Did request volume drop between 2026-08-25 to 2026-09-01 and 2026-09-02 to 2026-09-07?")
    assert tools_of(p)[:2] == ["get_daily_series", "detect_volume_anomalies"]
    assert "get_agent_comparison" not in tools_of(p)


@pytest.mark.parametrize("question", [
    "Did Agent A07's performance change between August 25 and September 7, 2026?",  # agent tools suffice
    "Which agents had the highest transfer rates on September 7, 2026?",            # one day, agent tools
    "How many requests were received on 2026-09-02?",                               # simple count
    "What happened in the service center on 2026-10-01?",                           # no data that day
    "Summarise what the data shows.",                                               # no scope at all
])
def test_no_prefetch_when_no_rule_applies(question):
    p = plan(question)
    assert p["calls"] == [] and p["reasons"]


def test_relative_dates():
    assert plan("How busy was today compared with yesterday?")["scope"]["start_date"] == "2026-09-04"  # previous working day
    assert plan("Has staffing been a problem this week?")["scope"]["start_date"] == "2026-09-01"       # last 5 working days
    assert plan("Any trends over the last two weeks?")["scope"]["start_date"] == "2026-08-25"


def test_the_date_context_line_is_not_read_as_the_question():
    p = plan("How are things?")
    assert p["scope"]["time_window"] is None and p["calls"] == []


def test_agent_staffing_question_still_gets_operational_evidence():
    p = plan("Was A04 short of staffing support over the last two weeks?")
    assert "get_daily_series" in tools_of(p) and "agent_focus" in p["intents"]


# --- Graph: pre-fetch, drill-down, fallback ---------------------------------------

def run(question, responses, monkeypatch):
    model = ScriptedModel(responses)
    monkeypatch.setattr(langgraph_agent, "model_with_tools", model)
    monkeypatch.setattr(langgraph_agent, "final_investigation_model", FixedResult())
    return langgraph_question_runner(question + CONTEXT.format(d="2026-09-07")), model


def test_broad_review_prefetches_and_drills_into_each_incident(monkeypatch):
    outcome, model = run("What are the warning signs over the last 10 working days?", [
        AIMessage(content="", tool_calls=[call("get_agent_request_evidence",
                                               {"agent_id": "A04", "start_date": "2026-09-01", "end_date": "2026-09-07"}, 1)]),
        AIMessage(content="Done."),
    ], monkeypatch)
    used = [s["tool"] for s in outcome["trace"]]
    assert used[:3] == ["get_daily_series", "detect_volume_anomalies", "get_agent_comparison"]
    assert used[3:6] == ["get_capacity_context"] * 3              # one per planted incident hour
    assert used[6] == "get_agent_request_evidence"                 # Claude can still ask for more
    staffing = [s["result"]["window"] for s in outcome["trace"][3:6]]
    assert sorted(w["average_agents_on_shift"] for w in staffing) == [8.0, 12.0, 12.0]

    first_turn = model.seen[0]
    assert sum(isinstance(m, ToolMessage) for m in first_turn) == 6  # Claude saw the evidence first
    assert len(outcome["evidence_plan"]["executed"]) == 6


def test_spike_question_starts_with_staffing_evidence(monkeypatch):
    """Regression (audit R2-1): the staffing drop was never looked at."""
    outcome, _ = run("Investigate the workload spike on 2026-08-27 between 15:00 and 16:00.",
                     [AIMessage(content="Done.")], monkeypatch)
    first = outcome["trace"][0]
    assert first["tool"] == "get_capacity_context"
    assert first["result"]["window"]["average_agents_on_shift"] == 8.0
    assert first["result"]["typical_same_window"]["average_agents_on_shift"] == 12.0


def test_unmatched_question_runs_exactly_as_before(monkeypatch):
    outcome, model = run("How many requests were received on 2026-09-02?", [
        AIMessage(content="", tool_calls=[call("count_requests",
                                               {"start_time": "2026-09-02T08:00:00", "end_time": "2026-09-02T17:00:00"}, 1)]),
        AIMessage(content="200 requests."),
    ], monkeypatch)
    assert [s["tool"] for s in outcome["trace"]] == ["count_requests"]
    assert not any(isinstance(m, ToolMessage) for m in model.seen[0])


def test_a_failing_prefetch_call_does_not_stop_the_run(monkeypatch):
    monkeypatch.setattr(evidence_planner, "plan", lambda text, days: {
        "scope": {}, "intents": ["spike"], "drill_into_anomalies": False, "reasons": ["test"],
        "calls": [{"tool": "get_capacity_context",
                   "args": {"start_time": "2026-08-25T08:00:00", "end_time": "2026-08-26T09:00:00"}}]})
    outcome, model = run("Anything.", [AIMessage(content="Done.")], monkeypatch)
    assert "error" in outcome["trace"][0]["result"]
    assert outcome["result"] is not None


# --- Answer checks -------------------------------------------------------------------

def steps(*pairs):
    return [{"tool": t, "args": a, "result": r} for t, a, r in pairs]


EVIDENCE = steps(("get_requests_by_status", {}, {"statuses": {"transferred": 61, "resolved": 139}}))


def result(**fields):
    base = {f: [] for f in answer_checks.RESULT_FIELDS}
    base["confirmed_root_cause"] = None
    base.update(fields)
    return base


def kinds(warnings):
    return [w["kind"] for w in warnings]


def test_tool_backed_and_derived_numbers_are_not_flagged():
    r = result(observed_facts=["61 of 200 requests were transferred (30.5%)."])
    assert answer_checks.check_answer(r, None, EVIDENCE) == []


def test_unsupported_number_is_flagged():
    """Regression (audit R6-5): an invented '~18%' team share."""
    w = answer_checks.check_answer(result(observed_facts=["The team share is about 18.4%."]), None, EVIDENCE)
    assert kinds(w) == ["unverified_number"] and "18.4" in w[0]["message"]


def test_unknown_identifiers_are_flagged():
    r = result(observed_facts=["A001 transferred request #100015."])
    w = answer_checks.check_answer(r, None, EVIDENCE, known_agents=["A01", "A04"])
    assert sorted(kinds(w)) == ["unknown_identifier", "unknown_identifier"]


def test_period_wide_wording_about_an_agent_is_flagged():
    """Regression (audit R6-2)."""
    r = result(supported_patterns=["A04 consistently transfers payment requests at or near 100% across the analysis period."])
    evidence = EVIDENCE + steps(("get_agent_comparison", {}, {"agents": [{"agent_id": "A04", "transfer_rate_percent": 100}]}))
    assert "scope_wording" in kinds(answer_checks.check_answer(r, None, evidence))


def test_totals_compared_across_unequal_periods_are_flagged():
    """Regression (audit R8-1), using the tools' real outputs."""
    week1 = tools.count_requests("2026-08-25 08:00", "2026-09-01 17:00")
    week2 = tools.count_requests("2026-09-02 08:00", "2026-09-07 17:00")
    trace = steps(("count_requests", {}, week1), ("count_requests", {}, week2),
                  ("compare_values", {"current": 800, "baseline": 1199}, tools.compare_values(800, 1199)))
    r = result(observed_facts=["Volume changed from 1,199 to 800 (-33.28%)."])
    assert "unequal_periods" in kinds(answer_checks.check_answer(r, None, trace))

    fair = steps(("count_requests", {}, week1), ("count_requests", {}, week2),
                 ("compare_values", {"current": 800, "baseline": 1199, "current_days": 4, "baseline_days": 6},
                  tools.compare_values(800, 1199, 4, 6)))
    assert "unequal_periods" not in kinds(answer_checks.check_answer(r, None, fair))


def test_confirmed_root_cause_is_flagged():
    r = result(confirmed_root_cause="A deployment broke login.")
    assert kinds(answer_checks.check_answer(r, None, EVIDENCE)) == ["confirmed_root_cause"]


def test_checks_are_saved_and_never_block_the_answer(monkeypatch, tmp_path):
    model = ScriptedModel([AIMessage(content="The team share is about 18.4%.")])
    monkeypatch.setattr(langgraph_agent, "model_with_tools", model)

    class Answer:
        def invoke(self, messages):
            return langgraph_agent.InvestigationResult(
                observed_facts=["The team share is about 18.4%."], supported_patterns=[], hypotheses=[],
                confirmed_root_cause=None, missing_evidence=[], recommendations=[])
    monkeypatch.setattr(langgraph_agent, "final_investigation_model", Answer())

    store = JsonInvestigationStore(tmp_path / "examples", tmp_path / "local")
    runner = InvestigationRunner(store, tmp_path, run_question=langgraph_question_runner,
                                 spawn=lambda work: work(), context=lambda d: None)
    record = store.get(runner.start_question("Summarise what the data shows.", "2026-09-07").id)
    assert record.status == "completed"
    assert [c.kind for c in record.answer_checks] == ["unverified_number"]
    assert record.evidence_plan is not None and record.evidence_plan.executed == []


def test_records_saved_before_phase_c_still_load():
    examples = Path(__file__).resolve().parents[1] / "investigations" / "examples"
    for path in examples.glob("*.json"):
        record = InvestigationRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
        assert record.evidence_plan is None and record.answer_checks is None

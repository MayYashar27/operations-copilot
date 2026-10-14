"""Ask Copilot tests: persistence, safety gates, failures. No Claude calls:
the LangGraph runners are replaced by small fakes."""

import json
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.config import PROJECT_ROOT, Settings
from api.copilot_runner import InvestigationRunner, _date_range, _trace_from_messages
from api.copilot_store import JsonInvestigationStore
from api.main import create_app

DATE = "2026-09-07"
LOCAL = ("127.0.0.1", 50000)


def fake_question_runner(question: str) -> dict:
    return {
        "result": {
            "observed_facts": ["Fact A"], "supported_patterns": [], "hypotheses": ["Maybe B"],
            "confirmed_root_cause": None, "missing_evidence": ["Logs"], "recommendations": ["Check C"],
        },
        "trace": [{"tool": "count_requests", "args": {"start_time": f"{DATE}T08:00:00", "end_time": f"{DATE}T17:00:00"},
                   "result": {"request_count": 200}}],
        "date_range": {"start": DATE, "end": DATE},
    }


def fake_agent_runner(agent_id, date, lookback_start, screening):
    assert screening["agent_id"] == agent_id  # receives the raw saved screening result
    return {"result": {"agent_id": agent_id, "date": date, "summary": "S", "observed_facts": [], "findings": [],
                       "hypotheses": [], "missing_evidence": [], "recommendations": []}}


def failing_runner(question: str) -> dict:
    raise RuntimeError("model unavailable")


@pytest.fixture
def workspace(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    shutil.copy(PROJECT_ROOT / "reports" / f"agent_performance_{DATE}.json", reports)
    return tmp_path, reports


def make(tmp_path, reports, mode="live", key=True, run_question=fake_question_runner, host=LOCAL):
    settings = Settings(mode, reports, has_api_key=key, investigations_dir=tmp_path / "investigations")
    store = JsonInvestigationStore(tmp_path / "investigations" / "examples", tmp_path / "investigations" / "local")
    runner = InvestigationRunner(store, reports, run_question=run_question, run_agent=fake_agent_runner,
                                 spawn=lambda work: work())  # run inline for deterministic tests
    return TestClient(create_app(settings, store, runner), client=host), store, runner


# ---------------------------------------------------------
# Safety gates
# ---------------------------------------------------------

def test_demo_mode_refuses_new_investigations(workspace):
    client, *_ = make(*workspace, mode="demo")
    response = client.post("/api/copilot/investigations", json={"question": "What happened today?"})
    assert response.status_code == 403


def test_live_mode_without_key_refuses(workspace):
    client, *_ = make(*workspace, key=False)
    assert client.post("/api/copilot/investigations", json={"question": "What happened today?"}).status_code == 403


def test_non_local_clients_are_refused(workspace):
    client, *_ = make(*workspace, host=("203.0.113.9", 4000))
    assert client.post("/api/copilot/investigations", json={"question": "What happened today?"}).status_code == 403


def test_proxied_requests_are_refused(workspace):
    client, *_ = make(*workspace)
    response = client.post("/api/copilot/investigations", json={"question": "What happened today?"},
                           headers={"X-Forwarded-For": "203.0.113.9"})
    assert response.status_code == 403


def test_question_is_validated(workspace):
    client, *_ = make(*workspace)
    assert client.post("/api/copilot/investigations", json={"question": "hi"}).status_code == 422


def test_only_one_investigation_at_a_time(workspace):
    tmp_path, reports = workspace
    client, store, runner = make(tmp_path, reports)
    runner.spawn = lambda work: None  # leave the first one "running"
    assert client.post("/api/copilot/investigations", json={"question": "First question here"}).status_code == 202
    assert client.post("/api/copilot/investigations", json={"question": "Second question here"}).status_code == 409


# ---------------------------------------------------------
# Persistence
# ---------------------------------------------------------

def test_completed_investigation_is_persisted_and_reopened(workspace):
    client, store, _ = make(*workspace)
    created = client.post("/api/copilot/investigations",
                          json={"question": "Why was wait time high?", "report_date": DATE}).json()

    record = client.get(f"/api/copilot/investigations/{created['id']}").json()
    assert record["status"] == "completed"
    assert record["origin"] == "local"
    assert record["result"]["hypotheses"] == ["Maybe B"]
    assert record["trace"][0]["tool"] == "count_requests"
    assert record["date_range"] == {"start": DATE, "end": DATE}

    # Reopening reads from disk: the runner is not involved.
    reopened = TestClient(create_app(Settings("demo", workspace[1], False, workspace[0] / "investigations")))
    assert reopened.get(f"/api/copilot/investigations/{created['id']}").json()["status"] == "completed"


def test_failures_are_persisted_with_error(workspace):
    client, *_ = make(*workspace, run_question=failing_runner)
    created = client.post("/api/copilot/investigations", json={"question": "Will this fail?"}).json()
    record = client.get(f"/api/copilot/investigations/{created['id']}").json()
    assert record["status"] == "failed"
    assert record["error"] == {"type": "RuntimeError", "message": "model unavailable"}


def test_history_lists_examples_and_local_and_filters(workspace):
    tmp_path, reports = workspace
    client, store, _ = make(tmp_path, reports)
    client.post("/api/copilot/investigations", json={"question": "Local question about wait time"})
    example = store.list()[0].model_copy(update={"id": "example-001", "origin": "example",
                                                 "question": "Example about transfers", "created_at": "2026-01-01T00:00:00+00:00"})
    store.save(example)

    history = client.get("/api/copilot/investigations").json()
    assert [h["origin"] for h in history] == ["local", "example"]  # newest first
    assert len(client.get("/api/copilot/investigations", params={"q": "transfers"}).json()) == 1


def test_interrupted_runs_are_marked_failed(workspace):
    tmp_path, reports = workspace
    client, store, runner = make(tmp_path, reports)
    runner.spawn = lambda work: None
    created = client.post("/api/copilot/investigations", json={"question": "Left running on restart"}).json()

    assert store.mark_interrupted() == 1
    assert store.get(created["id"]).error.type == "Interrupted"


def test_unknown_and_malformed_ids(workspace):
    client, *_ = make(*workspace)
    assert client.get("/api/copilot/investigations/zzzzzzzz").status_code == 404
    assert client.get("/api/copilot/investigations/..%2Fsecrets").status_code in (404, 422)


def test_corrupt_history_file_is_skipped(workspace):
    tmp_path, reports = workspace
    client, *_ = make(tmp_path, reports)
    local = tmp_path / "investigations" / "local"
    local.mkdir(parents=True)
    (local / "broken-0001.json").write_text("{", encoding="utf-8")
    assert client.get("/api/copilot/investigations").status_code == 200


# ---------------------------------------------------------
# Agent deep investigation
# ---------------------------------------------------------

def test_agent_investigation_is_saved_where_agent_detail_reads_it(workspace):
    tmp_path, reports = workspace
    client, *_ = make(tmp_path, reports)
    created = client.post(f"/api/reports/{DATE}/agents/A01/investigation").json()
    assert created["kind"] == "agent"

    detail = client.get(f"/api/reports/{DATE}/agents/A01").json()
    assert detail["investigation"]["summary"] == "S"


def test_agent_investigation_unknown_agent(workspace):
    client, *_ = make(*workspace)
    assert client.post(f"/api/reports/{DATE}/agents/Z99/investigation").status_code == 404


# ---------------------------------------------------------
# Trace extraction from LangGraph messages
# ---------------------------------------------------------

class _Msg:
    def __init__(self, tool_calls=None, tool_call_id=None, content=""):
        self.tool_calls, self.tool_call_id, self.content = tool_calls, tool_call_id, content


def test_trace_pairs_calls_with_results_and_truncates():
    big = json.dumps({"rows": "x" * 5000})
    messages = [
        _Msg(tool_calls=[{"id": "1", "name": "count_requests", "args": {"start_time": "2026-08-25T12:00:00"}},
                         {"id": "2", "name": "get_request_details", "args": {"end_time": "2026-08-26T13:00:00"}}]),
        _Msg(tool_call_id="1", content=json.dumps({"request_count": 45})),
        _Msg(tool_call_id="2", content=big),
    ]
    trace = _trace_from_messages(messages)
    assert trace[0]["result"] == {"request_count": 45}
    assert trace[1]["result_truncated"] is True and len(trace[1]["result_preview"]) == 4000
    assert _date_range(trace) == {"start": "2026-08-25", "end": "2026-08-26"}


def test_demo_app_never_imports_langgraph(workspace):
    client, *_ = make(*workspace, mode="demo")
    client.get("/api/copilot/investigations")
    client.post("/api/copilot/investigations", json={"question": "What happened today?"})
    assert "langgraph_agent" not in sys.modules

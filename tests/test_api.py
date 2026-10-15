"""API tests. They use the committed synthetic report and make no Claude calls."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.config import PROJECT_ROOT, Settings, load_settings
from api.main import create_app


DATE = "2026-09-07"
STATUSES = {"screened", "findings", "investigation", "insufficient_data"}


def make_client(reports_dir: Path, mode: str = "demo", has_key: bool = False) -> TestClient:
    settings = Settings(app_mode=mode, reports_dir=reports_dir, has_api_key=has_key)
    return TestClient(create_app(settings))


@pytest.fixture
def client() -> TestClient:
    return make_client(PROJECT_ROOT / "reports")


# ---------------------------------------------------------
# Demo / live mode
# ---------------------------------------------------------

def test_demo_is_the_default_mode(monkeypatch):
    # Test the code's default, not this machine's .env (which may say live).
    monkeypatch.setattr("api.config.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("APP_MODE", raising=False)
    settings = load_settings()
    assert settings.app_mode == "demo"
    assert settings.live_investigations_enabled is False


def test_live_mode_requires_an_api_key():
    assert Settings("live", Path("."), has_api_key=False).live_investigations_enabled is False
    assert Settings("live", Path("."), has_api_key=True).live_investigations_enabled is True
    assert Settings("demo", Path("."), has_api_key=True).live_investigations_enabled is False


def test_invalid_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_MODE", "production")
    with pytest.raises(ValueError):
        load_settings()


def test_config_endpoint_exposes_no_secrets(client):
    body = client.get("/api/config").json()
    assert body["mode"] == "demo"
    assert body["live_investigations_enabled"] is False
    assert "key" not in json.dumps(body).lower()


# ---------------------------------------------------------
# Happy paths against the committed synthetic report
# ---------------------------------------------------------

def test_list_reports(client):
    dates = [item["date"] for item in client.get("/api/reports").json()]
    assert DATE in dates


def test_overview_counts_add_up(client):
    body = client.get(f"/api/reports/{DATE}").json()
    assert sum(body["status_counts"].values()) == body["total_agents"]
    assert body["day_metrics"]["total_requests"] > 0
    for item in body["priority_items"]:
        assert item["reasons"]


def test_overview_volume_profile_matches_day_total(client):
    body = client.get(f"/api/reports/{DATE}").json()
    profile = body["volume_profile"]
    assert len(profile["hours"]) == 9  # 08:00-17:00
    assert sum(h["requests"] for h in profile["hours"]) == body["day_metrics"]["total_requests"]
    for h in profile["hours"]:
        assert h["above_threshold"] == (h["requests"] >= profile["threshold"])


def test_overview_hourly_activity_and_trend(client):
    body = client.get(f"/api/reports/{DATE}").json()

    hours = body["hourly_activity"]
    assert len(hours) == 9
    assert sum(h["requests"] for h in hours) == body["day_metrics"]["total_requests"]
    assert all(h["typical_requests"] is not None for h in hours)

    trend = body["daily_trend"]
    assert trend[-1]["date"] == DATE and trend[-1]["has_report"] is True
    assert [t["date"] for t in trend] == sorted(t["date"] for t in trend)
    assert all(t["date"] >= body["lookback_start"] for t in trend)
    assert all(sum(t["hourly_requests"]) == t["total_requests"] for t in trend)


def test_agent_rows_include_ai_finding_titles(client):
    rows = {r["agent_id"]: r for r in client.get(f"/api/reports/{DATE}/agents").json()}
    assert len(rows["A04"]["ai_finding_titles"]) == rows["A04"]["ai_observation_count"]


def test_agents_list(client):
    rows = client.get(f"/api/reports/{DATE}/agents").json()
    assert len(rows) == 15
    for row in rows:
        assert row["status"] in STATUSES
        assert row["metrics"]["handled_requests"] > 0


def test_agent_detail_keeps_rule_and_ai_sources_separate(client):
    body = client.get(f"/api/reports/{DATE}/agents/A04").json()

    assert body["rule_signals"], "A04 has deterministic signals in the saved report"
    assert all(s["source"] == "rule" for s in body["rule_signals"])
    assert all(s["code"] != "SEMANTIC_DOCUMENTATION_FINDINGS" for s in body["rule_signals"])
    assert all(o["source"] == "ai" for o in body["ai_observations"])


def test_agent_detail_evidence_covers_cited_requests_only(client):
    body = client.get(f"/api/reports/{DATE}/agents/A04").json()

    cited = {i for o in body["ai_observations"] for i in o["request_ids"]}
    cited |= {i for f in body["investigation"]["findings"] for i in f["supporting_request_ids"]}
    returned = {r["request_id"] for r in body["evidence_requests"]}

    assert cited <= returned
    assert "customer_description" not in json.dumps(body)


def test_saved_investigation_is_returned(client):
    body = client.get(f"/api/reports/{DATE}/agents/A04").json()
    assert body["investigation"]["summary"]
    assert body["investigation"]["hypotheses"] is not None


# ---------------------------------------------------------
# Missing and malformed data
# ---------------------------------------------------------

def test_missing_report_returns_404(client):
    response = client.get("/api/reports/2020-01-01")
    assert response.status_code == 404


def test_invalid_date_returns_422(client):
    assert client.get("/api/reports/not-a-date").status_code == 422
    assert client.get("/api/reports/..%2F..%2Fsecrets").status_code in (404, 422)


def test_missing_agent_returns_404(client):
    assert client.get(f"/api/reports/{DATE}/agents/Z99").status_code == 404


def test_invalid_agent_id_returns_422(client):
    assert client.get(f"/api/reports/{DATE}/agents/A0!").status_code == 422


def test_empty_reports_dir(tmp_path):
    assert make_client(tmp_path).get("/api/reports").json() == []


def test_corrupt_json_returns_clean_500(tmp_path):
    (tmp_path / f"agent_performance_{DATE}.json").write_text("{not json", encoding="utf-8")
    response = make_client(tmp_path).get(f"/api/reports/{DATE}")

    assert response.status_code == 500
    assert str(tmp_path) not in response.text  # no file paths leaked


def test_report_with_wrong_shape_returns_500(tmp_path):
    (tmp_path / f"agent_performance_{DATE}.json").write_text(
        json.dumps({"date": DATE, "agent_results": "oops"}), encoding="utf-8"
    )
    assert make_client(tmp_path).get(f"/api/reports/{DATE}").status_code == 500


def test_broken_report_does_not_hide_other_reports(tmp_path):
    good = PROJECT_ROOT / "reports" / f"agent_performance_{DATE}.json"
    (tmp_path / good.name).write_text(good.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "agent_performance_2026-09-04.json").write_text("{", encoding="utf-8")

    dates = [item["date"] for item in make_client(tmp_path).get("/api/reports").json()]
    assert dates == [DATE]


# ---------------------------------------------------------
# Safety: read endpoints never load the AI workflow
# ---------------------------------------------------------

def test_read_endpoints_never_load_langgraph(client):
    sys.modules.pop("langgraph_agent", None)  # other test files may have imported it
    for url in [
        "/api/config",
        "/api/reports",
        f"/api/reports/{DATE}",
        f"/api/reports/{DATE}/agents",
        f"/api/reports/{DATE}/agents/A04",
    ]:
        assert client.get(url).status_code == 200
    assert "langgraph_agent" not in sys.modules

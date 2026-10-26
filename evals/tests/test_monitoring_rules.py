"""Agent Performance Monitoring: deterministic rules, tested without any AI call.

Part 1 runs the real rules on the real synthetic data (planted agents A04,
A07, A09) and checks the saved report reproduces. Part 2 builds small
datasets in a temp folder to test every threshold just at and just below
its boundary, the insufficient-data paths, and the escalation combinations.
The AI documentation review is either switched off or replaced by a fake.
"""

import json
from pathlib import Path

import pytest

import langgraph_agent as agent
import tools
from langgraph_agent import DocumentationAnalysisResult, DocumentationFinding

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads((ROOT / "reports" / "agent_performance_2026-09-07.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_ai(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("the AI documentation review must not run in these tests")
    monkeypatch.setattr(agent, "analyze_agent_documentation", refuse)


def evaluate(agent_id, date="2026-09-07", lookback="2026-08-25"):
    return agent.evaluate_agent_investigation_triggers(agent_id, date, lookback, run_semantic_screening=False)


def codes(result):
    return {f["code"] for f in result["findings"]}


# ---------------------------------------------------------------------------
# Part 1: real data
# ---------------------------------------------------------------------------

def test_a04_planted_rising_transfers_is_escalated():
    result = evaluate("A04")
    assert result["investigation_status"] == "investigation"
    assert {"RISING_TRANSFER_RATE", "HIGH_TRANSFER_RATE_VS_PEERS", "CONCENTRATED_TRANSFERS"} <= codes(result)


def test_a07_planted_faster_handling_and_short_notes_is_escalated():
    result = evaluate("A07")
    assert result["investigation_status"] == "investigation"
    assert {"FASTER_HANDLING_WITH_MORE_TRANSFERS", "MANY_SHORT_NOTES"} <= codes(result)


def test_a09_planted_case_mix_is_flagged_but_not_escalated():
    """A09's high transfer rate comes from harder cases. The rules surface it as a
    finding (they cannot see case mix) but must not escalate it on their own."""
    result = evaluate("A09")
    assert result["investigation_status"] == "findings"
    assert codes(result) == {"HIGH_TRANSFER_RATE_VS_PEERS"}


@pytest.mark.parametrize("row", REPORT["agent_results"], ids=lambda r: r["agent_id"])
def test_saved_report_rule_findings_reproduce(row):
    result = evaluate(row["agent_id"])
    saved_rule_codes = {f["code"] for f in row["findings"]} - {"SEMANTIC_DOCUMENTATION_FINDINGS"}
    assert codes(result) == saved_rule_codes
    assert (result["investigation_status"] == "investigation") == (row["investigation_status"] == "investigation")


def test_without_ai_review_most_findings_disappear():
    """Documents how much of the report's 'findings' status comes from the AI review alone."""
    statuses = {row["agent_id"]: evaluate(row["agent_id"])["investigation_status"] for row in REPORT["agent_results"]}
    assert sum(s == "screened" for s in statuses.values()) == 11
    assert sorted(a for a, s in statuses.items() if s != "screened") == ["A04", "A07", "A09", "A10"]


def test_ai_observation_alone_cannot_escalate(monkeypatch):
    fake = DocumentationAnalysisResult(
        agent_id="A01", date="2026-09-07", summary="Strongly worded concern.",
        findings=[DocumentationFinding(finding="Serious concern", request_ids=[100085], explanation="x")],
        requires_further_investigation=True, investigation_reason="The model asks for escalation.")
    monkeypatch.setattr(agent, "analyze_agent_documentation", lambda *_a, **_k: fake)
    result = agent.evaluate_agent_investigation_triggers("A01", "2026-09-07", "2026-08-25", run_semantic_screening=True)
    assert codes(result) == {"SEMANTIC_DOCUMENTATION_FINDINGS"}
    assert result["investigation_status"] == "findings"


# ---------------------------------------------------------------------------
# Part 2: synthetic boundary datasets
# ---------------------------------------------------------------------------

DAYS = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08",   # earlier half
        "2026-01-09", "2026-01-12", "2026-01-13", "2026-01-14"]   # later half; screened day = last
EARLIER, LATER, SCREENED = DAYS[:4], DAYS[4:], DAYS[-1]
GOOD_NOTE = "Customer asked about an invoice; checked the account and explained the charge."
DESTS = ["technical_support", "billing", "back_office", "supervisor"]


class World:
    """A tiny dataset: target agent A01, one peer A02."""

    def __init__(self):
        self.rows, self.shifts, self.next_id = [], [], 1

    def shift(self, agent_id, days):
        self.shifts += [{"date": d, "agent_id": agent_id, "shift_start": f"{d}T08:00:00",
                         "shift_end": f"{d}T17:00:00", "scheduled_hours": 9} for d in days]

    def add(self, agent_id, day, status="resolved", dest=None, handling=6.0, note=GOOD_NOTE,
            classification="payment_issue"):
        minute = len(self.rows) % 500
        self.rows.append({
            "request_id": self.next_id, "request_time": f"{day}T{8 + minute // 60:02d}:{minute % 60:02d}:00",
            "agent_id": agent_id, "subject": "Billing inquiry", "classification": classification,
            "wait_time_minutes": 3, "status": status,
            "transferred_to": dest if status == "transferred" else None,
            "documentation": note, "resolved_first_line": status == "resolved",
            "handling_time_minutes": handling, "customer_description": "x"})
        self.next_id += 1

    def period(self, agent_id, days, requests, transferred, handling=6.0):
        """Spread requests over days; transfers rotate destinations so none concentrates."""
        for i in range(requests):
            day = days[i % len(days)]
            if i < transferred:
                # rotate destinations within each day, independent of the day rotation
                self.add(agent_id, day, "transferred", DESTS[(i // len(days)) % len(DESTS)], handling)
            else:
                self.add(agent_id, day, handling=handling)

    def install(self, tmp_path, monkeypatch):
        (tmp_path / "requests.json").write_text(json.dumps(self.rows))
        (tmp_path / "agent_shifts.json").write_text(json.dumps(self.shifts))
        (tmp_path / "monitor_snapshots.json").write_text("[]")
        monkeypatch.setattr(tools, "DATA_DIR", tmp_path)
        monkeypatch.setattr(tools, "REQUESTS_FILE", tmp_path / "requests.json")
        monkeypatch.setattr(tools, "MONITOR_FILE", tmp_path / "monitor_snapshots.json")
        monkeypatch.setattr(tools, "AGENT_SHIFTS_FILE", tmp_path / "agent_shifts.json")


def world(target_earlier=(100, 20, 6.0), target_later=(100, 20, 6.0), peers_later=(100, 20), shift_days=DAYS):
    """Defaults: target and peer both at 20% in both halves, steady handling: no signals."""
    w = World()
    w.shift("A01", shift_days)
    w.shift("A02", DAYS)
    earlier_days = [d for d in EARLIER if d in shift_days]
    later_days = [d for d in LATER if d in shift_days]
    if target_earlier[0] and earlier_days:
        w.period("A01", earlier_days, *target_earlier)
    if target_later[0] and later_days:
        w.period("A01", later_days, *target_later)
    w.period("A02", EARLIER, 100, 20)
    w.period("A02", LATER, *peers_later)
    return w


def run(w, tmp_path, monkeypatch):
    w.install(tmp_path, monkeypatch)
    return agent.evaluate_agent_investigation_triggers("A01", SCREENED, DAYS[0], run_semantic_screening=False)


def test_baseline_world_has_no_signals(tmp_path, monkeypatch):
    result = run(world(), tmp_path, monkeypatch)
    assert codes(result) == set() and result["investigation_status"] == "screened"


@pytest.mark.parametrize("later_transfers, expected", [(35, True), (34, False)])
def test_high_transfer_rate_vs_peers_boundary(tmp_path, monkeypatch, later_transfers, expected):
    # peers 20%; target 35% (exactly +15 points) vs 34% (+14). Earlier half matches later: no rise.
    w = world(target_earlier=(100, later_transfers, 6.0), target_later=(100, later_transfers, 6.0))
    assert ("HIGH_TRANSFER_RATE_VS_PEERS" in codes(run(w, tmp_path, monkeypatch))) is expected


def test_high_transfer_rate_vs_peers_needs_20_requests(tmp_path, monkeypatch):
    w = world(target_earlier=(19, 19, 6.0), target_later=(19, 19, 6.0))  # 100% transferred, too few requests
    assert "HIGH_TRANSFER_RATE_VS_PEERS" not in codes(run(w, tmp_path, monkeypatch))


@pytest.mark.parametrize("later_transfers, expected", [(35, True), (34, False)])
def test_rising_transfer_rate_boundary(tmp_path, monkeypatch, later_transfers, expected):
    # earlier 20%, later 35% (+15) vs 34% (+14); peers at 30% so the peer rule stays quiet.
    w = world(target_later=(100, later_transfers, 6.0), peers_later=(100, 30))
    assert ("RISING_TRANSFER_RATE" in codes(run(w, tmp_path, monkeypatch))) is expected


def test_rising_transfer_rate_needs_20_requests_in_each_half(tmp_path, monkeypatch):
    w = world(target_earlier=(19, 0, 6.0), target_later=(100, 60, 6.0))
    assert "RISING_TRANSFER_RATE" not in codes(run(w, tmp_path, monkeypatch))


@pytest.mark.parametrize("later_handling, expected", [
    (8.0, {"FALLING_HANDLING_TIME"}),      # exactly -20%
    (8.1, set()),                          # -19%
    (12.0, {"RISING_HANDLING_TIME"}),      # exactly +20%
    (11.9, set()),                         # +19%
])
def test_handling_time_boundaries(tmp_path, monkeypatch, later_handling, expected):
    w = world(target_earlier=(100, 20, 10.0), target_later=(100, 20, later_handling))
    found = codes(run(w, tmp_path, monkeypatch)) & {"FALLING_HANDLING_TIME", "RISING_HANDLING_TIME"}
    assert found == expected


def test_faster_handling_with_more_transfers_escalates(tmp_path, monkeypatch):
    w = world(target_earlier=(100, 20, 10.0), target_later=(100, 35, 8.0), peers_later=(100, 30))
    result = run(w, tmp_path, monkeypatch)
    assert "FASTER_HANDLING_WITH_MORE_TRANSFERS" in codes(result)
    assert result["investigation_status"] == "investigation"


def test_fewer_than_four_working_days_skips_trends_but_still_screens_notes(tmp_path, monkeypatch):
    w = world(target_earlier=(0, 0, 6.0), target_later=(30, 0, 6.0), shift_days=DAYS[-3:])
    w.add("A01", SCREENED, note="")
    w.add("A01", SCREENED, note="   ")
    result = run(w, tmp_path, monkeypatch)
    assert result["performance_signals"]["status"] == "insufficient_data"
    assert codes(result) == {"MISSING_DOCUMENTATION"}
    assert result["investigation_status"] == "findings"


def test_no_requests_on_the_screened_day_is_insufficient_data(tmp_path, monkeypatch):
    w = world(target_later=(100, 20, 6.0))
    w.rows = [r for r in w.rows if not (r["agent_id"] == "A01" and r["request_time"].startswith(SCREENED))]
    result = run(w, tmp_path, monkeypatch)
    assert result["investigation_status"] == "insufficient_data"


def screened_day_world(notes):
    """Steady history; the screened day has exactly the given notes for A01."""
    w = world()
    w.rows = [r for r in w.rows if not (r["agent_id"] == "A01" and r["request_time"].startswith(SCREENED))]
    for note in notes:
        w.add("A01", SCREENED, note=note)
    return w


SHORT = "Handled the request today."            # 4 words
FIVE_WORDS = "Customer called; issue was handled."  # 5 words: short
SIX_WORDS = "Customer called and issue was handled."  # 6 words: not short


@pytest.mark.parametrize("total, short, expected", [
    (5, 3, True),    # 60%, three short notes
    (5, 2, False),   # 40% but only two short notes
    (7, 3, True),    # 42.9%
    (8, 3, False),   # 37.5%
    (4, 4, False),   # fewer than five requests
])
def test_many_short_notes_boundaries(tmp_path, monkeypatch, total, short, expected):
    w = screened_day_world([SHORT] * short + [GOOD_NOTE] * (total - short))
    assert ("MANY_SHORT_NOTES" in codes(run(w, tmp_path, monkeypatch))) is expected


@pytest.mark.parametrize("note, is_short", [(FIVE_WORDS, True), (SIX_WORDS, False)])
def test_short_note_word_threshold(tmp_path, monkeypatch, note, is_short):
    w = screened_day_world([note] * 5)
    assert ("MANY_SHORT_NOTES" in codes(run(w, tmp_path, monkeypatch))) is is_short


@pytest.mark.parametrize("missing, expected", [(2, True), (1, False)])
def test_missing_documentation_boundary(tmp_path, monkeypatch, missing, expected):
    w = screened_day_world([""] * missing + [GOOD_NOTE] * 6)
    assert ("MISSING_DOCUMENTATION" in codes(run(w, tmp_path, monkeypatch))) is expected


@pytest.mark.parametrize("to_one, others, expected", [
    (3, 1, True),    # 3 of 4 = 75%
    (3, 2, False),   # 3 of 5 = 60%
    (2, 0, False),   # only two transfers
    (4, 0, True),    # 4 of 4
])
def test_concentrated_transfers_boundaries(tmp_path, monkeypatch, to_one, others, expected):
    w = screened_day_world([GOOD_NOTE] * 4)
    for _ in range(to_one):
        w.add("A01", SCREENED, "transferred", "technical_support")
    for i in range(others):
        w.add("A01", SCREENED, "transferred", DESTS[1 + i % 3])
    assert ("CONCENTRATED_TRANSFERS" in codes(run(w, tmp_path, monkeypatch))) is expected


def test_escalation_rising_alone_is_only_a_finding(tmp_path, monkeypatch):
    result = run(world(target_later=(100, 35, 6.0), peers_later=(100, 30)), tmp_path, monkeypatch)
    assert codes(result) == {"RISING_TRANSFER_RATE"} and result["investigation_status"] == "findings"


def test_escalation_rising_with_missing_notes(tmp_path, monkeypatch):
    # 36 of 100, plus two undocumented requests: 36/102 = 35.3%, still +15 over 20%
    w = world(target_later=(100, 36, 6.0), peers_later=(100, 30))
    w.add("A01", SCREENED, note="")
    w.add("A01", SCREENED, note="")
    result = run(w, tmp_path, monkeypatch)
    assert codes(result) == {"RISING_TRANSFER_RATE", "MISSING_DOCUMENTATION"}
    assert result["investigation_status"] == "investigation"


def test_escalation_high_vs_peers_alone_is_only_a_finding(tmp_path, monkeypatch):
    w = world(target_earlier=(100, 40, 6.0), target_later=(100, 40, 6.0))
    result = run(w, tmp_path, monkeypatch)
    assert codes(result) == {"HIGH_TRANSFER_RATE_VS_PEERS"} and result["investigation_status"] == "findings"


@pytest.mark.parametrize("short, expected", [(6, "findings"), (7, "investigation")])
def test_escalation_short_notes_needs_70_percent(tmp_path, monkeypatch, short, expected):
    w = screened_day_world([SHORT] * short + [GOOD_NOTE] * (10 - short))  # 60% vs 70%
    assert run(w, tmp_path, monkeypatch)["investigation_status"] == expected


def test_escalation_short_notes_with_missing_notes(tmp_path, monkeypatch):
    w = screened_day_world([SHORT] * 4 + [""] * 2 + [GOOD_NOTE] * 4)  # 40% short, 2 missing
    result = run(w, tmp_path, monkeypatch)
    assert {"MANY_SHORT_NOTES", "MISSING_DOCUMENTATION"} <= codes(result)
    assert result["investigation_status"] == "investigation"


@pytest.mark.parametrize("high_rate, expected", [(True, "investigation"), (False, "findings")])
def test_escalation_concentration_needs_elevated_transfers(tmp_path, monkeypatch, high_rate, expected):
    rate = 40 if high_rate else 20
    w = world(target_earlier=(100, rate, 6.0), target_later=(100, rate, 6.0))
    w.rows = [r for r in w.rows if not (r["agent_id"] == "A01" and r["request_time"].startswith(SCREENED))]
    for _ in range(4):
        w.add("A01", SCREENED, "transferred", "technical_support")
    for _ in range(6):
        w.add("A01", SCREENED)
    result = run(w, tmp_path, monkeypatch)
    assert "CONCENTRATED_TRANSFERS" in codes(result)
    assert result["investigation_status"] == expected


def test_peer_baseline_excludes_the_agent(tmp_path, monkeypatch):
    w = world(target_later=(100, 35, 6.0), peers_later=(100, 30))
    peers = run(w, tmp_path, monkeypatch)["performance_signals"]["periods"]["peers_later"]
    assert peers["requests"] == 100 and peers["transfers"] == 30

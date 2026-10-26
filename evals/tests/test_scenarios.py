"""The proposed scenarios are well-formed, and their graders behave on real saved runs."""

import json
from collections import Counter
from pathlib import Path

import pytest

from evals import oracle
from evals.grade_scenario import grade, load_scenarios, resolve

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = load_scenarios()


def test_thirty_unique_scenarios_cover_every_category():
    assert len(SCENARIOS) == 30
    assert len({s["id"] for s in SCENARIOS}) == 30
    assert set(Counter(s["category"] for s in SCENARIOS)) == {
        "spike_cause", "counting", "per_agent", "cross_agent", "robustness", "trend"}


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["id"])
def test_scenario_references_are_valid(scenario):
    for group in scenario.get("required_tools", []):
        assert all(tool in oracle.REPLAY for tool in group), group
    for fact in scenario.get("facts", []):
        for spec in [fact["oracle"]] + fact.get("also_accept", []):
            value = resolve(spec)
            assert isinstance(value, (int, float)) and not isinstance(value, bool), (fact, value)


def saved(name):
    for folder in ("investigations/examples", "investigations/local"):
        path = ROOT / folder / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    pytest.skip(f"saved run {name} is not present (local runs are git-ignored)")


def by_id(sid):
    return next(s for s in SCENARIOS if s["id"] == sid)


def test_graders_pass_the_good_spike_answer():
    result = grade(by_id("S01"), saved("example-20261014-125852-6e015a"))
    assert result["passed"], [c for c in result["checks"] if c["verdict"] == "FAIL"]


def test_graders_catch_the_missed_staffing_cause():
    result = grade(by_id("S03"), saved("example-20261014-130022-3d26d2"))
    failed = [c["check"] for c in result["checks"] if c["verdict"] == "FAIL"]
    assert any(c.startswith("concept") for c in failed)


def test_graders_pass_the_a07_answer():
    assert grade(by_id("S15"), saved("20261020-162258-023899"))["passed"]


def test_graders_fail_the_aborted_run_and_pass_the_fixed_one():
    assert not grade(by_id("S20"), saved("20261015-144932-0e6aea"))["passed"]
    assert grade(by_id("S20"), saved("20261020-161734-58ff11"))["passed"]


def test_graders_catch_the_ten_day_errors():
    result = grade(by_id("S30"), saved("20261020-163908-8ee9ba"))
    failed = {c["check"] for c in result["checks"] if c["verdict"] == "FAIL"}
    assert "must not: saved run R8 error" in failed
    assert result["critical_failures"] >= 1

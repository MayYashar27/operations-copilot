"""The graders themselves: a grader that is wrong makes every result wrong."""

from evals import claims
from evals.trace_checks import validate_args


def values(text):
    return [n["value"] for n in claims.extract_numbers(text)]


def test_dates_times_ids_and_years_are_not_quantities():
    text = "On 2026-09-07 between 12:00–13:00, A04 and Sep 7, 2026 (Week 2): 45 requests"
    assert values(text) == [45.0]


def test_thousands_separators_and_percentages():
    found = claims.extract_numbers("1,999 requests; 30.5% transferred; −399 change")
    assert [(n["value"], n["percent"]) for n in found] == [(1999.0, False), (30.5, True), (399.0, False)]


def evidence(*results):
    return claims.Evidence(results)


def test_direct_and_rounded_matches():
    ev = evidence({"transfer_rate_percent": 53.85, "count": 45})
    for text in ("53.85%", "53.9%", "54%", "45"):
        assert ev.match(claims.extract_numbers(text)[0])[0] == "direct", text


def test_breakdown_totals_are_evidence():
    ev = evidence({"statuses": {"transferred": 61, "resolved": 139}})
    assert ev.match(claims.extract_numbers("200")[0])[0] == "direct"


def test_derived_needs_an_operand_stated_beside_it():
    ev = evidence({"statuses": {"transferred": 61, "resolved": 139}})
    n = claims.extract_numbers("61 transferred (30.5%)")
    assert ev.match(n[1], [x["value"] for x in n])[0] == "derived"
    assert ev.match(claims.extract_numbers("30.5%")[0])[0] == "loose"


def test_invented_number_is_unsupported():
    ev = evidence({"count": 45, "baseline": 19})
    assert ev.match(claims.extract_numbers("7777")[0])[0] == "unsupported"


def test_invented_and_unseen_identifiers():
    ev = evidence({"agents": [{"agent_id": "A04"}], "requests": [{"request_id": 100008}]})
    problems = claims.check_identifiers({"answer": "A001 and A04; request 100015 and 100008; ID #99999"}, ev)
    found = {(p["id"], p["problem"]) for p in problems}
    assert ("A001", "agent ID does not exist") in found
    assert (100015, "real request ID that the agent never retrieved") in found
    assert (99999, "request ID does not exist") in found
    assert not any(p["id"] in ("A04", 100008) for p in problems)


def test_argument_validation():
    assert validate_args("get_agent_performance", {"agent_id": "A001", "start_date": "2026-09-07",
                                                   "end_date": "2026-09-07"})[0]["level"] == "error"
    assert validate_args("count_requests", {"start_time": "2026-09-08T08:00:00",
                                            "end_time": "2026-09-08T17:00:00"})[0]["level"] == "error"
    warn = validate_args("get_monitor_metrics", {"start_time": "2026-08-25 08:00", "end_time": "2026-09-07 17:00"})
    assert [w["level"] for w in warn] == ["warning"]
    assert validate_args("count_requests", {"start_time": "2026-08-25T12:00:00", "end_time": "2026-08-25T13:00:00"}) == []

"""Expectations and targeted claim checks for the 8 saved runs.

Generic checks (claims.py) catch invented numbers and IDs. They cannot tell
whether a real number was combined or interpreted correctly. The targeted
checks below are an auditor's reading of each answer, written as code so the
verdicts are reproducible: every check quotes the claim it tests and
recomputes the truth from data with the independent oracle.

Verdicts: PASS, FAIL, REVIEW (needs a human judgement), NOT_EVALUABLE.
Severity: critical > high > medium > low > info.
"""

import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional

from evals import oracle

UPDATE_WORDS = re.compile(r"updat|latest application version", re.I)


def texts(record: Dict[str, Any]) -> Dict[str, str]:
    result = record.get("result") or {}
    out = {}
    for field in ("observed_facts", "supported_patterns", "hypotheses", "missing_evidence", "recommendations"):
        out[f"result.{field}"] = "\n".join(result.get(field) or [])
    out["result.confirmed_root_cause"] = result.get("confirmed_root_cause") or ""
    out["narrative"] = record.get("narrative") or ""
    return out


def find(record: Dict[str, Any], needle: str) -> Optional[Dict[str, str]]:
    for source, text in texts(record).items():
        i = text.find(needle)
        if i >= 0:
            line_start = text.rfind("\n", 0, i) + 1
            line_end = text.find("\n", i)
            return {"source": source, "quote": text[line_start: line_end if line_end >= 0 else None].strip()}
    return None


def check(record, cid, title, needle, verify: Callable[[], Dict[str, Any]], severity, category):
    """Run one targeted check. verify() returns {'verdict', 'evidence'} once the quote is located."""
    located = find(record, needle) if needle else {"source": "trace", "quote": ""}
    if located is None:
        return {"id": cid, "title": title, "verdict": "NOT_EVALUABLE", "severity": "info",
                "category": category, "evidence": f"quoted text not found: {needle!r}", "source": None, "quote": None}
    outcome = verify()
    return {"id": cid, "title": title, "severity": severity if outcome["verdict"] != "PASS" else "info",
            "category": category, **located, **outcome}


def _tools(record) -> List[str]:
    return [s["tool"] for s in record.get("trace") or []]


def _calls(record, tool) -> List[Dict[str, Any]]:
    return [s.get("args") or {} for s in record.get("trace") or [] if s["tool"] == tool]


def _agent(comparison, agent_id):
    return next(a for a in comparison["agents"] if a["agent_id"] == agent_id)


# ---------------------------------------------------------------------------
# Run 1: 2026-08-25 12:00-13:00 spike (planted: login failures after an app update)
# ---------------------------------------------------------------------------

def run_spike_0825(r):
    window = ("2026-08-25T12:00:00", "2026-08-25T13:00:00")
    login = [x for x in oracle._window(*window) if x["classification"] == "login_issue"]
    themes = r.get("pattern_themes") or []
    update_ids = set(themes[0]["request_ids"]) if themes else set()
    escalated_ids = set(themes[1]["request_ids"]) if len(themes) > 1 else set()
    idx = oracle.request_index()
    claimed_table = {"12:00-12:10": 2, "12:10-12:20": 17, "12:20-12:30": 10,
                     "12:30-12:40": 7, "12:40-12:50": 17, "12:50-13:00": 2}
    actual = oracle.get_requests_by_time_bucket(*window, 10)["request_counts"]

    def table():
        wrong = {k: (v, actual[k]) for k, v in claimed_table.items() if actual[k] != v}
        return {"verdict": "FAIL" if wrong else "PASS",
                "evidence": f"claimed (value, actual): {wrong}; claimed rows sum to {sum(claimed_table.values())}, "
                            f"the hour had {sum(actual.values())} requests. The agent only retrieved 5-minute "
                            "buckets and summed them itself."}

    def theme_update():
        login_ids = {x["request_id"] for x in login}
        matches = [i for i in update_ids if UPDATE_WORDS.search(idx[i]["documentation"])]
        others = login_ids - update_ids
        ok = update_ids <= login_ids and len(matches) == len(update_ids) == 36 \
            and not any(UPDATE_WORDS.search(idx[i]["documentation"]) for i in others)
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": f"{len(matches)}/{len(update_ids)} cited notes mention the update; "
                            f"{len(others)} other login notes do not; all cited IDs are login requests in the window"}

    def theme_escalated():
        transferred = {i for i in update_ids if idx[i]["status"] == "transferred"}
        ok = escalated_ids == transferred and len(transferred) == 23
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": f"{len(transferred)} of the 36 update-related requests were transferred; "
                            f"cited set equals the transferred set: {escalated_ids == transferred}"}

    def rate_label():
        return {"verdict": "FAIL",
                "evidence": "57.5% = 23/40 (all login requests). For update-related requests the rate is "
                            f"23/36 = {23 / 36 * 100:.1f}%. The figure is attributed to the wrong group."}

    def planted():
        hyp = texts(r)["result.hypotheses"].lower()
        ok = "update" in hyp and "login" in hyp
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": "Planted cause: login issues after an application update. The leading hypothesis names it, "
                            "and the root cause is correctly left unconfirmed."}

    def abandoned():
        m = oracle.get_monitor_metrics(*window)
        return {"verdict": "PASS" if m["abandoned_calls_change"] == 24 else "FAIL",
                "evidence": f"single-day window, counter difference = {m['abandoned_calls_change']}"}

    return [
        check(r, "R1-1", "10-minute volume table in the narrative", "| 12:10–12:20 | 17 |", table, "medium", "numerical"),
        check(r, "R1-2", "36 of 40 login requests mention the application update", "36 of the 40 login_issue requests", theme_update, "high", "grounding"),
        check(r, "R1-3", "23 of the 36 update-related requests were escalated", "23 of the 36 update-related", theme_escalated, "medium", "grounding"),
        check(r, "R1-4", "57.5% escalation rate attributed to update-related requests", "escalation rate (57.5%) for update-related", rate_label, "low", "numerical"),
        check(r, "R1-5", "Planted incident identified", "application update", planted, "high", "scenario"),
        check(r, "R1-6", "24 abandoned calls in the spike hour", "24 calls were abandoned", abandoned, "medium", "numerical"),
    ]


# ---------------------------------------------------------------------------
# Run 2: 2026-08-27 15:00-16:00 spike (planted: staffing shortage)
# ---------------------------------------------------------------------------

def run_spike_0827(r):
    idx = oracle.request_index()

    def planted():
        hyp = (texts(r)["result.hypotheses"] + texts(r)["result.supported_patterns"]).lower()
        named = any(w in hyp for w in ("staff", "capacity", "fewer agents", "agents on shift"))
        on_shift = {h: oracle.agents_on_shift(f"2026-08-27T{h}:00:00", f"2026-08-27T{h + 1}:00:00") for h in (14, 15)}
        others = [oracle.get_monitor_metrics(f"{d}T15:00:00", f"{d}T16:00:00")["average_available_agents"]
                  for d in ("2026-08-25", "2026-08-26", "2026-08-28", "2026-08-31")]
        return {"verdict": "PASS" if named else "FAIL",
                "evidence": f"Planted cause: staffing shortage. Raw data: agents on shift fell from {on_shift[14]} "
                            f"(14:00) to {on_shift[15]} (15:00); available agents 0.77 vs {others} at the same hour "
                            "on other days. No hypothesis names staffing. Contributing gap: no tool exposes "
                            "agents_on_shift, and the agent never fetched monitor metrics for a baseline hour."}

    def baseline_monitor():
        windows = {(a.get("start_time"), a.get("end_time")) for a in _calls(r, "get_monitor_metrics")}
        has_baseline = any(s and not s.startswith("2026-08-27T15") for s, _ in windows)
        return {"verdict": "PASS" if has_baseline else "FAIL",
                "evidence": f"monitor windows queried: {sorted(windows)}. The answer lists 'baseline abandoned "
                            "call count' and 'baseline wait time' as missing evidence, although "
                            "get_monitor_metrics and get_average_wait_time provide them for 14:00-15:00."}

    def subthemes():
        groups = {"Payment question": [30139, 30151, 30175, 30179, 30140, 30171],
                  "Pending transaction": [30156, 30138, 30169, 30150, 30168],
                  "Billing inquiry": [30141, 30144, 30180, 30155, 30172]}
        ok = all(idx[i]["subject"] == s and idx[i]["classification"] == "payment_issue"
                 for s, ids in groups.items() for i in ids)
        billing_all_transferred = all(idx[i]["status"] == "transferred" for i in groups["Billing inquiry"])
        pending = [30156, 30150, 30168]
        return {"verdict": "PASS" if ok and billing_all_transferred and all(idx[i]["status"] == "transferred" for i in pending) else "FAIL",
                "evidence": "sub-theme groups match request subjects exactly; all 5 billing inquiries and the 3 cited "
                            "pending transactions were transferred"}

    return [
        check(r, "R2-1", "Planted incident identified (staffing shortage)", "payment processing delay", planted, "medium", "scenario"),
        check(r, "R2-2", "Baseline capacity data retrieved before declaring it missing", "Baseline abandoned call count", baseline_monitor, "medium", "tool_selection"),
        check(r, "R2-3", "Payment sub-themes and escalations", "three sub-themes", subthemes, "medium", "grounding"),
    ]


# ---------------------------------------------------------------------------
# Runs 3 and 4: transfers on 2026-09-07
# ---------------------------------------------------------------------------

def _dominant_everywhere(r, cid, needle):
    def verify():
        tops = {}
        for c in oracle.CLASSIFICATIONS:
            dest = oracle.get_classification_status_breakdown("2026-09-07T08:00:00", "2026-09-07T17:00:00", c)["transfer_destinations"]
            tops[c] = max(dest.items(), key=lambda kv: kv[1])
        wrong = {c: t for c, t in tops.items() if t[0] != "technical_support"}
        return {"verdict": "FAIL" if wrong else "PASS",
                "evidence": f"top destination per classification: {tops}. general_information sent most transfers "
                            "to billing, which the answer's own observed facts state; the pattern contradicts them."}
    return check(r, cid, "'Technical Support dominant across all four classifications'", needle, verify, "medium", "reasoning")


def run_transfers_0907(r):
    def window():
        args = _calls(r, "get_transfers_by_destination")[0]
        full = oracle.get_transfers_by_destination(args["start_time"], args["end_time"])
        shift = oracle.get_transfers_by_destination("2026-09-07T08:00:00", "2026-09-07T17:00:00")
        return {"verdict": "PASS" if full["transfer_destinations"] == shift["transfer_destinations"] else "FAIL",
                "evidence": f"window {args['start_time']}..{args['end_time']} covers the whole shift"}

    return [
        check(r, "R3-1", "Date window covers the requested day", None, window, "medium", "tool_arguments"),
        _dominant_everywhere(r, "R3-2", "Technical Support was the dominant transfer destination across all four"),
    ]


def run_today_0907(r):
    def today():
        windows = {a.get("start_time", "")[:10] for s in ("get_requests_by_classification", "get_requests_by_status")
                   for a in _calls(r, s)}
        return {"verdict": "PASS" if windows == {"2026-09-07"} else "FAIL",
                "evidence": f"'today' resolved to {sorted(windows)} (expected 2026-09-07 from the date context)"}

    def highest_label():
        return {"verdict": "FAIL",
                "evidence": "The narrative table labels Payment Issue (33%) 'Highest' transfer rate; Login Issue (36%) "
                            "is the highest and is also labelled 'Highest'."}

    return [
        check(r, "R4-1", "'Today' resolved to the viewed shift", None, today, "high", "tool_arguments"),
        _dominant_everywhere(r, "R4-2", "Technical Support was the dominant transfer destination across all four"),
        check(r, "R4-3", "Payment Issue labelled 'Highest' transfer rate", "| Payment Issue | 40 (67%) | 20 (33%) | 🔴 Highest |", highest_label, "low", "numerical"),
    ]


# ---------------------------------------------------------------------------
# Run 5: the failed cross-agent run (invented ID A001)
# ---------------------------------------------------------------------------

def run_failed_agents(r):
    def failure():
        return {"verdict": "FAIL",
                "evidence": f"error: {r.get('error')}. The agent guessed agent ID 'A001'; the tool error aborted the "
                            "run and no tool calls were saved. Historic: fixed by get_agent_comparison, ID validation, "
                            "recoverable tool errors and partial traces; covered by "
                            "tests/test_agent_tools.py::test_exact_question_recovers_from_invented_ids. Run R6 is the "
                            "same question after the fix."}
    return [check(r, "R5-1", "Invented agent ID aborted the run", None, failure, "high", "hallucination")]


# ---------------------------------------------------------------------------
# Run 6: highest transfer rates on 2026-09-07 (planted: A04 rising, A09 case mix)
# ---------------------------------------------------------------------------

def run_agents_0907(r):
    day = oracle.get_agent_comparison("2026-09-07", "2026-09-07")
    base = oracle.get_agent_comparison("2026-08-25", "2026-09-04")

    def ranking():
        expected = [(a["agent_id"], a["transfer_rate_percent"]) for a in day["agents"][:5]]
        ok = [a for a, _ in expected] == ["A04", "A10", "A09", "A07", "A15"]
        return {"verdict": "PASS" if ok else "FAIL", "evidence": f"oracle top 5: {expected}"}

    def a04_always():
        bc = _agent(base, "A04")["by_classification"]
        return {"verdict": "FAIL",
                "evidence": f"A04 over 2026-08-25..09-04 (a result the agent retrieved): payment_issue "
                            f"{bc['payment_issue']['transfer_rate_percent']}%, login_issue "
                            f"{bc['login_issue']['transfer_rate_percent']}%. Near-100% holds only for 9 requests on "
                            "2026-09-07. A false claim about an individual's behaviour across the period."}

    def a09_mix():
        t = _agent(base, "A09")["by_classification"]["technical_issue"]
        ok = t["requests"] == 75 and _agent(base, "A09")["handled_requests"] == 136
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": f"A09 baseline: {t['requests']} technical of {_agent(base, 'A09')['handled_requests']}"}

    def a09_destinations():
        rows = [x for x in oracle.requests() if x["agent_id"] == "A09" and str(x["_d"]) == "2026-09-07"
                and x["status"] == "transferred"]
        return {"verdict": "FAIL",
                "evidence": f"A09 made {len(rows)} transfers: {dict(Counter(x['transferred_to'] for x in rows))}. "
                            "The quoted 3/3/1 split covers only the 7 technical_issue transfers but is presented "
                            "as A09's transfers."}

    def team_share():
        share = oracle._pct(sum(x["classification"] == "technical_issue" for x in oracle.requests()
                                if str(x["_d"]) == "2026-09-07"), 200)
        return {"verdict": "FAIL",
                "evidence": f"team technical_issue share on 2026-09-07 is {share}% "
                            "(22.53% excluding A09), not ~18%. No tool result contains 18."}

    def planted():
        hyp = texts(r)["result.hypotheses"]
        ok = "A09" in hyp and "technical_issue" in hyp and "A04" in hyp
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": "Planted: A04 rising transfers concentrated in technical_support; A09 lower volume with "
                            "complex technical cases. Both are reflected, and A09 is framed as possible case mix."}

    def wasted_calls():
        single = [a for a in _calls(r, "detect_agent_performance_signals") if a["start_date"] == a["end_date"]]
        return {"verdict": "FAIL" if single else "PASS",
                "evidence": f"{len(single)} calls with a one-day window, which can only return insufficient_data "
                            "(the tool needs four working days); the agent recovered by calling again with the full window"}

    def login_others():
        rates = {a: _agent(day, a)["by_classification"]["login_issue"]["transfer_rate_percent"] for a in ("A09", "A15", "A05")}
        return {"verdict": "PASS" if rates == {"A09": 33.33, "A15": 0.0, "A05": 0.0} else "FAIL",
                "evidence": f"login transfer rates on 2026-09-07: {rates}"}

    return [
        check(r, "R6-1", "Top-5 transfer-rate ranking", "The five agents with the highest transfer rates", ranking, "high", "numerical"),
        check(r, "R6-2", "'A04 transfers payment and login at or near 100% across the analysis period'", "at or near 100% across the analysis period", a04_always, "high", "grounding"),
        check(r, "R6-3", "A09 baseline case mix (75 of 136 technical)", "75 of 136", a09_mix, "medium", "numerical"),
        check(r, "R6-4", "A09 transfer destinations", "technical_support (3), back_office (3), and billing (1)", a09_destinations, "medium", "numerical"),
        check(r, "R6-5", "'~18% team average' technical share", "~18% team average", team_share, "low", "numerical"),
        check(r, "R6-6", "Planted agent scenarios reflected", "A09's elevated transfer rate may be partly driven", planted, "high", "scenario"),
        check(r, "R6-7", "Signal tool called with windows it cannot analyse", None, wasted_calls, "low", "tool_arguments"),
        check(r, "R6-8", "Login transfer rates of A09, A15, A05", "A15: 0%, A05: 0%", login_others, "low", "numerical"),
    ]


# ---------------------------------------------------------------------------
# Run 7: A07 performance change (planted: faster handling, short notes)
# ---------------------------------------------------------------------------

def run_a07(r):
    idx = oracle.request_index()

    def planted():
        facts = texts(r)["result.observed_facts"]
        ok = "37.04%" in facts and "3.95" in facts and "documentation quality visibly degraded" in facts
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": "Planted: falling handling time and increasingly short notes. Both found with correct "
                            "period figures (transfer 18.33% -> 37.04%, handling 6.01 -> 3.95 min)."}

    def short_notes():
        def share(a, b):
            rows = [x for x in oracle.requests() if x["agent_id"] == "A07" and a <= str(x["_d"]) <= b]
            return sum(len(x["documentation"].split()) < 6 for x in rows), len(rows)
        e, l = share("2026-08-25", "2026-08-31"), share("2026-09-01", "2026-09-07")
        return {"verdict": "PASS" if e[0] == 0 and l[0] > l[1] / 2 else "FAIL",
                "evidence": f"notes under six words: earlier {e[0]}/{e[1]}, later {l[0]}/{l[1]} (full periods, "
                            "not just the 30-request samples the agent read)"}

    def mismatches():
        claimed = {70098: ("general_information", "billing"), 70065: ("payment_issue", "technical_support"),
                   80003: ("login_issue", "technical_support"), 80109: ("login_issue", "back_office")}
        ok = all(idx[i]["agent_id"] == "A07" and (idx[i]["classification"], idx[i]["transferred_to"]) == v
                 for i, v in claimed.items())
        return {"verdict": "PASS" if ok else "FAIL",
                "evidence": "all four cited requests exist, belong to A07, and have the stated classification and destination"}

    def destinations():
        d = oracle.get_agent_performance("A07", "2026-08-25", "2026-09-07")["agent"]["transfer_destinations"]
        return {"verdict": "PASS" if d == {"technical_support": 15, "billing": 13, "back_office": 3} else "FAIL",
                "evidence": f"oracle: {d}"}

    def progressive():
        series = [d["transfer_rate_percent"] for d in oracle.get_agent_daily_trends("A07", "2026-08-25", "2026-09-07")["daily_trends"]
                  if d["handled_requests"]]
        return {"verdict": "REVIEW",
                "evidence": f"daily transfer rates: {series}. Rising overall but not progressive (dips on Sep 1 and "
                            "Sep 4); the narrative itself calls it volatile. Is 'trended progressively upward' acceptable?"}

    return [
        check(r, "R7-1", "Planted A07 scenario identified", "documentation quality visibly degraded", planted, "high", "scenario"),
        check(r, "R7-2", "Documentation degradation is real across full periods", "documentation quality visibly degraded", short_notes, "medium", "grounding"),
        check(r, "R7-3", "Cited mismatched transfers", "Req. 70098", mismatches, "medium", "grounding"),
        check(r, "R7-4", "Transfer destinations over the period", "technical_support (15), billing (13), back_office (3)", destinations, "low", "numerical"),
        check(r, "R7-5", "'Transfer rate trended progressively upward'", "Transfer rate trended progressively upward", progressive, "low", "reasoning"),
    ]


# ---------------------------------------------------------------------------
# Run 8: trends over the last 10 working days
# ---------------------------------------------------------------------------

def run_trends_10d(r):
    w1 = ("2026-08-25 08:00", "2026-09-01 17:00")
    w2 = ("2026-09-02 08:00", "2026-09-07 17:00")
    d1, d2 = oracle.working_days(*w1), oracle.working_days(*w2)

    def volume_drop():
        c1, c2 = oracle.count_requests(*w1)["request_count"], oracle.count_requests(*w2)["request_count"]
        return {"verdict": "FAIL",
                "evidence": f"'Week 1' has {len(d1)} working days and 'Week 2' has {len(d2)}. Per working day: "
                            f"{c1 / len(d1):.1f} vs {c2 / len(d2):.1f} requests. There is no volume drop; the "
                            "-33% is an artefact of unequal periods, yet it is the first warning sign and drives a "
                            "recommendation to check for a routing failure."}

    def abandoned_total():
        true_total = oracle.abandoned_calls_between("2026-08-25 08:00", "2026-09-07 17:00")
        return {"verdict": "FAIL",
                "evidence": f"true abandoned calls over the 10 days: {true_total}. 53 is the first-to-last counter "
                            "difference across days; the counter resets daily, so 53 is just 2026-09-07's total. "
                            "The tool returned a valid number for an invalid window, and nothing warned the agent."}

    def abandoned_weeks():
        a1, a2 = oracle.abandoned_calls_between(*w1), oracle.abandoned_calls_between(*w2)
        return {"verdict": "FAIL",
                "evidence": f"true: week 1 = {a1}, week 2 = {a2} (per working day {a1 / len(d1):.1f} vs "
                            f"{a2 / len(d2):.1f}). Claimed 63 and 52 are the last day's counters. The direction "
                            "('fewer abandonments') happens to hold per day, but every figure is wrong."}

    def band():
        rates = sorted((a["transfer_rate_percent"], a["agent_id"])
                       for a in oracle.get_agent_comparison("2026-08-25", "2026-09-07")["agents"])
        return {"verdict": "FAIL",
                "evidence": f"14 agents besides A04, not 13. A09 at {dict((b, a) for a, b in rates)['A09']}% is "
                            "outside the stated 18.9-27.4% band and is silently left out, so 'A04 is the clear "
                            "outlier' hides the second outlier (A09, a planted scenario)."}

    def peak_hour():
        tops = []
        for d in oracle.data_dates():
            c = Counter(x["_t"].hour for x in oracle.requests() if x["_d"] == d)
            tops.append(c.most_common(1)[0][0])
        n14 = sum(h == 14 for h in tops)
        return {"verdict": "FAIL",
                "evidence": f"14:00 was the busiest hour on {n14} of {len(tops)} days (daily peak hours: {tops}). "
                            "The 10-day total is inflated by the 2026-08-26 14:00 incident (45 requests). "
                            "'Consistently' is unsupported, and the staffing recommendation rests on it."}

    def avg_label():
        return {"verdict": "FAIL",
                "evidence": "values (200, 218, ...) are 10-day totals per hour slot, not averages "
                            "(about 20-26 requests per hour per day)"}

    def incidents():
        text = "\n".join(texts(r).values())
        hits = [d for d in ("08-25", "08-26", "08-27", "Aug 25", "Aug 26", "Aug 27", "August 25", "August 26", "August 27")
                if re.search(re.escape(d) + r"[^\n]{0,40}(1[2-5]:00|spike|incident|surge)", text)]
        return {"verdict": "PASS" if hits else "FAIL",
                "evidence": "The three planted incident hours (2026-08-25 12:00, 08-26 14:00, 08-27 15:00; about "
                            "45 requests vs about 20 normal) are not reported as warning signs. Only aggregated "
                            "windows were queried, so the spikes were averaged away."}

    def a04_all_classes():
        later = [x for x in oracle.requests() if "2026-09-01" <= str(x["_d"]) <= "2026-09-07"]
        rates = {}
        for c in oracle.CLASSIFICATIONS:
            own = [x for x in later if x["agent_id"] == "A04" and x["classification"] == c]
            peer = [x for x in later if x["agent_id"] != "A04" and x["classification"] == c]
            rates[c] = (oracle._pct(sum(x["status"] == "transferred" for x in own), len(own)),
                        oracle._pct(sum(x["status"] == "transferred" for x in peer), len(peer)))
        ok = all(a > p + 15 for a, p in rates.values())
        return {"verdict": "PASS" if ok else "FAIL", "evidence": f"A04 vs peers, later period (A04%, peers%): {rates}"}

    return [
        check(r, "R8-1", "'Volume dropped 33% in Week 2' (warning sign #1)", "Absolute change: −399 (−33.3%)", volume_drop, "high", "reasoning"),
        check(r, "R8-2", "'Total abandoned calls across the full period: 53'", "Total abandoned calls across the full period: 53", abandoned_total, "high", "numerical"),
        check(r, "R8-3", "Abandoned calls week 1 = 63, week 2 = 52", "Abandoned calls in Week 1: 63", abandoned_weeks, "high", "numerical"),
        check(r, "R8-4", "'13 remaining agents ... 18.90% to 27.41%'", "The 13 remaining agents", band, "medium", "grounding"),
        check(r, "R8-5", "'14:00-15:00 is consistently the highest-volume hour'", "consistently the highest-volume hour", peak_hour, "medium", "reasoning"),
        check(r, "R8-6", "Hourly table labelled as averages", "Avg. Requests (across 10 days)", avg_label, "low", "numerical"),
        check(r, "R8-7", "Planted incident hours surfaced as warning signs", None, incidents, "medium", "scenario"),
        check(r, "R8-8", "A04 elevated across all four classifications", "elevated across all four request classifications", a04_all_classes, "medium", "grounding"),
    ]


# ---------------------------------------------------------------------------
# Expectations per run
# ---------------------------------------------------------------------------

RUNS: Dict[str, Dict[str, Any]] = {
    "example-20261014-125852-6e015a": {
        "label": "R1 spike 2026-08-25 12:00", "planted": "login issues after an application update",
        "required_tools": [["count_requests"], ["get_requests_by_classification"], ["get_request_details"], ["get_monitor_metrics"]],
        "question_window": ("2026-08-25T12:00:00", "2026-08-25T13:00:00"), "needs_baseline": True,
        "claims": run_spike_0825},
    "example-20261014-130022-3d26d2": {
        "label": "R2 spike 2026-08-27 15:00", "planted": "staffing capacity shortage",
        "required_tools": [["count_requests"], ["get_requests_by_classification"], ["get_monitor_metrics"]],
        "question_window": ("2026-08-27T15:00:00", "2026-08-27T16:00:00"), "needs_baseline": True,
        "claims": run_spike_0827},
    "example-20261014-130150-c42a40": {
        "label": "R3 transfers 2026-09-07", "planted": None,
        "required_tools": [["get_transfers_by_destination"], ["get_requests_by_status"],
                           ["get_classification_status_breakdown"]],
        "question_window": None, "needs_baseline": False, "claims": run_transfers_0907},
    "20261015-125818-e7490a": {
        "label": "R4 classifications 'today'", "planted": None,
        "required_tools": [["get_requests_by_classification"], ["get_requests_by_status"],
                           ["get_classification_status_breakdown", "get_transfers_by_destination"]],
        "question_window": ("2026-09-07T08:00:00", "2026-09-07T17:00:00"), "needs_baseline": False,
        "claims": run_today_0907},
    "20261015-144932-0e6aea": {
        "label": "R5 agents 2026-09-07 (failed, pre-fix)", "planted": "A04, A09",
        "required_tools": [["get_agent_comparison"]], "question_window": None, "needs_baseline": False,
        "claims": run_failed_agents},
    "20261020-161734-58ff11": {
        "label": "R6 agents 2026-09-07 (after fix)", "planted": "A04 rising transfers; A09 case mix",
        "required_tools": [["get_agent_comparison"], ["get_agent_request_evidence"]],
        "question_window": None, "needs_baseline": False, "claims": run_agents_0907},
    "20261020-162258-023899": {
        "label": "R7 A07 performance change", "planted": "A07 faster handling, short notes",
        "required_tools": [["get_agent_daily_trends"], ["detect_agent_performance_signals", "get_agent_performance"],
                           ["get_agent_request_evidence"]],
        "question_window": None, "needs_baseline": False, "claims": run_a07},
    "20261020-163908-8ee9ba": {
        "label": "R8 10-day trends", "planted": "3 incident hours; A04; A07; A09",
        "required_tools": [["get_agent_comparison"], ["count_requests"]],
        "question_window": None, "needs_baseline": False, "claims": run_trends_10d},
}

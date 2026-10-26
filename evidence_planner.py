"""Deterministic evidence planning for Ask Copilot. No AI is involved.

Before Claude starts, the workflow reads the question (and its date context),
recognises what kind of evidence the question needs, and collects it with the
deterministic tools. This guarantees coverage that Claude might otherwise
skip (found in the Phase 0 audit: a 10-day review that missed every
incident, and a staffing incident investigated without capacity data).

The plan is built from independent signals, not one fixed route:
- scope:   the dates the question is about (explicit dates, ranges, "today",
           "yesterday", "last N working days", "last week", "two weeks"...)
- intents: broad review/trend, change/comparison, staffing/capacity,
           spike, cause, agent focus
Each rule adds evidence on its own, so a multi-day staffing question gets
both the day-level series and capacity context. When nothing matches, the
plan is empty and Claude investigates exactly as before. In every case
Claude can still call any tool afterwards.
"""

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

MAX_DRILL_DOWNS = 5  # capacity checks for unusual hours found by the pre-fetch

MONTHS = {name: i for i, names in enumerate([
    ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"), ("may",),
    ("jun", "june"), ("jul", "july"), ("aug", "august"), ("sep", "sept", "september"),
    ("oct", "october"), ("nov", "november"), ("dec", "december")], start=1) for name in names}
_MONTH = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_NUMBER_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

INTENTS = {
    "staffing": r"\bstaff|understaff|capacity|available agents|agents available|headcount|coverage|absen"
                r"|wait(?:ing)? (?:so )?long|long wait|waiting time|abandon",
    "spike": r"spike|unusual(?:ly)? high|surge|\bbusy\b|busiest|workload|\bpeak\b|high volume|overload",
    "review": r"trend|warning sign|over the last|\breview\b|overall|pay attention|should i (?:worry|focus)"
              r"|what should|\bpatterns?\b|\bweeks?\b|period",
    "change": r"\bchanged?\b|compare|\bdrop|declin|increas|\bvs\.?\b|versus",
    "cause": r"\bwhy\b|cause|explain|investigate|what happened",
}


def split_question(text: str) -> Tuple[str, str]:
    """The manager's question and the appended date context (Context: ...)."""
    head, _, context = text.partition("\n\nContext:")
    return head, context


def _viewing_date(context: str, working_days: List[str]) -> Optional[str]:
    match = re.search(r"viewing the shift of (\d{4}-\d{2}-\d{2})", context)
    if match:
        return match.group(1)
    return working_days[-1] if working_days else None


def _explicit_dates(question: str, year: int) -> List[str]:
    found = set(re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", question))
    q = question.lower()
    for month, day, y in re.findall(_MONTH + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?", q):
        found.add(_safe_date(int(y or year), MONTHS[month[:3] if month[:4] != "sept" else "sep"], int(day)))
    for day, month, y in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + _MONTH + r"\.?(?:,?\s+(\d{4}))?", q):
        found.add(_safe_date(int(y or year), MONTHS[month[:3] if month[:4] != "sept" else "sep"], int(day)))
    return sorted(d for d in found if d)


def _safe_date(y: int, m: int, d: int) -> Optional[str]:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def _relative_range(q: str, viewing: str, working_days: List[str]) -> Optional[Tuple[str, str]]:
    upto = [d for d in working_days if d <= viewing]
    if not upto:
        return None
    match = re.search(r"last (\d+|two|three|four|five|six|seven|eight|nine|ten) (?:working )?days", q)
    if match:
        n = int(match.group(1)) if match.group(1).isdigit() else _NUMBER_WORDS[match.group(1)]
        return upto[-n:][0], viewing
    if re.search(r"(last|past|this) week\b", q):
        return upto[-5:][0], viewing
    if re.search(r"(last|past) (two|2) weeks|fortnight|whole period|entire period|all (the )?available data|overall", q):
        return upto[0], viewing
    return None


def _time_window(question: str, day: Optional[str]) -> Optional[Tuple[str, str]]:
    if not day:
        return None
    times = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", question)
    if not times:
        return None
    start = f"{int(times[0][0]):02d}:{times[0][1]}"
    end = f"{int(times[1][0]):02d}:{times[1][1]}" if len(times) > 1 else f"{int(times[0][0]) + 1:02d}:{times[0][1]}"
    if end <= start:
        return None
    return f"{day}T{start}:00", f"{day}T{end}:00"


def plan(text: str, working_days: List[str]) -> Dict[str, Any]:
    """Return {scope, intents, calls, drill_into_anomalies, reasons}. Pure function."""
    question, context = split_question(text)
    q = question.lower()
    viewing = _viewing_date(context, working_days)
    intents = sorted(name for name, pattern in INTENTS.items() if re.search(pattern, q))
    agents = sorted(set(re.findall(r"\bA\d{2,3}\b", question)))
    if agents:
        intents.append("agent_focus")

    year = int(viewing[:4]) if viewing else date.today().year
    dates = _explicit_dates(question, year)
    if re.search(r"\btoday\b|this shift|this (morning|afternoon)", q) and viewing:
        dates.append(viewing)
    if re.search(r"\byesterday\b", q) and viewing:
        earlier = [d for d in working_days if d < viewing]
        if earlier:
            dates.append(earlier[-1])
    dates = sorted(set(dates))

    relative = _relative_range(q, viewing, working_days) if viewing else None
    if relative:
        start, end = relative
    elif dates:
        start, end = dates[0], dates[-1]
    else:
        start = end = None
    days_in_scope = [d for d in working_days if start and start <= d <= end]
    single_day = dates[0] if len(dates) == 1 and not relative else None
    window = _time_window(question, single_day)

    scope = {"start_date": start, "end_date": end, "working_days": len(days_in_scope),
             "time_window": list(window) if window else None, "viewing_date": viewing, "agents": agents}
    calls: List[Dict[str, Any]] = []
    reasons: List[str] = []
    drill = False
    multi_day = len(days_in_scope) >= 2
    # Questions about named agents use the agent tools; the operational
    # series is added for them only when they also ask about staffing.
    operational = not agents or "staffing" in intents

    if multi_day and operational:
        calls += [{"tool": "get_daily_series", "args": {"start_date": start, "end_date": end}},
                  {"tool": "detect_volume_anomalies", "args": {"start_date": start, "end_date": end}}]
        reasons.append(f"The question covers {len(days_in_scope)} working days: collected the day-by-day series "
                       "and searched every day for unusual hours.")
        if "review" in intents and not agents:
            calls.append({"tool": "get_agent_comparison", "args": {"start_date": start, "end_date": end}})
            reasons.append("Broad review: compared all agents over the same period.")
        if {"review", "staffing", "spike", "cause"} & set(intents):
            drill = True
            reasons.append("Each unusual hour found gets its demand and staffing context.")

    if window and ({"spike", "staffing", "cause"} & set(intents)):
        calls.append({"tool": "get_capacity_context", "args": {"start_time": window[0], "end_time": window[1]}})
        reasons.append("A specific hour is investigated: collected demand and staffing against the previous "
                       "hour and the typical day.")
    elif "staffing" in intents and len(days_in_scope) == 1 and not window:
        day = days_in_scope[0]
        calls += [{"tool": "get_daily_series", "args": {"start_date": day, "end_date": day}},
                  {"tool": "detect_volume_anomalies", "args": {"start_date": day, "end_date": day}}]
        drill = True
        reasons.append("Staffing question about one day: collected that day's capacity figures and its unusual hours.")

    return {"scope": scope, "intents": intents, "calls": calls, "drill_into_anomalies": drill,
            "reasons": reasons or ["No pre-fetch rule matched; the agent chooses all evidence itself."]}


def drill_down_calls(anomaly_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Capacity context for the most unusual hours found by detect_volume_anomalies."""
    calls = []
    for anomaly in (anomaly_result or {}).get("anomalies", [])[:MAX_DRILL_DOWNS]:
        calls.append({"tool": "get_capacity_context",
                      "args": {"start_time": anomaly["start_time"], "end_time": anomaly["end_time"]}})
    return calls

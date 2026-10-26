"""Checks on a saved run's tool trace: arguments, replay against the oracle, completeness."""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from evals import oracle

DATA_START = date(2026, 8, 25)
DATA_END = date(2026, 9, 7)

DATE_ARGS = ("start_date", "end_date")
TIME_ARGS = ("start_time", "end_time")


def _parse(value: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def validate_args(tool: str, args: Dict[str, Any], legacy: bool = False) -> List[Dict[str, str]]:
    """Return argument problems. level is 'error' (invalid) or 'warning' (valid but risky).

    legacy=True adds the warnings that applied to the tool contract before the
    2026-10-26 fix (multi-day monitor and bucket windows).
    """
    issues: List[Dict[str, str]] = []

    def add(level: str, message: str) -> None:
        issues.append({"level": level, "message": message})

    if tool not in oracle.REPLAY:
        add("error", f"unknown tool '{tool}'")
        return issues

    for a, b in (TIME_ARGS, DATE_ARGS):
        if a in args or b in args:
            start, end = _parse(args.get(a)), _parse(args.get(b))
            if start is None or end is None:
                add("error", f"unparseable {a}/{b}: {args.get(a)!r}, {args.get(b)!r}")
                continue
            if (a == "start_time" and start >= end) or (a == "start_date" and start > end):
                add("error", f"empty or reversed window {args.get(a)} -> {args.get(b)}")
            if end.date() < DATA_START or start.date() > DATA_END:
                add("error", "window lies entirely outside the available data (2026-08-25..2026-09-07)")

    if "classification" in args and args["classification"] is not None \
            and args["classification"] not in oracle.CLASSIFICATIONS:
        add("error", f"unknown classification '{args['classification']}'")
    if args.get("transferred_to") is not None and args["transferred_to"] not in oracle.DESTINATIONS:
        add("error", f"unknown destination '{args['transferred_to']}'")
    if "agent_id" in args and args["agent_id"] not in oracle.roster():
        add("error", f"agent_id '{args['agent_id']}' is not in the roster")
    if "limit" in args and not 1 <= int(args["limit"]) <= 100:
        add("error", "limit outside 1..100")
    if "bucket_minutes" in args and int(args["bucket_minutes"]) <= 0:
        add("error", "bucket_minutes must be positive")

    if legacy and tool == "get_monitor_metrics" and "start_time" in args \
            and oracle.counters_reset_inside(args["start_time"], args["end_time"]):
        add("warning", "multi-day monitor window under the pre-fix contract: *_change fields were "
                       "NOT totals for the window")
    if legacy and tool == "get_requests_by_time_bucket" and "start_time" in args:
        s, e = _parse(args["start_time"]), _parse(args["end_time"])
        if s and e and s.date() != e.date():
            add("warning", "multi-day bucket window under the pre-fix contract: HH:MM labels merged "
                           "all days (totals, not averages)")
    if tool == "detect_agent_performance_signals" and "start_date" in args:
        if len(oracle.working_days(args["start_date"], args["end_date"])) < 4:
            add("warning", "window has fewer than four working days; the tool can only return insufficient_data")
    return issues


def _close(a: Any, b: Any, tol: float = 0.011) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    return a == b


def _as_obj(result: Any) -> Any:
    if isinstance(result, str):
        try:
            return json.loads(result)
        except ValueError:
            return result
    return result


def is_legacy(record: Dict[str, Any]) -> bool:
    """Saved before the monitor/time-bucket contract fix."""
    return str(record.get("created_at") or "")[:10] < oracle.CONTRACT_CHANGE_DATE


def stale_fields(step: Dict[str, Any]) -> Dict[str, Any]:
    """Fields of a legacy tool result whose value changes under the current contract."""
    tool, args = step["tool"], step.get("args") or {}
    if tool not in ("get_monitor_metrics", "get_requests_by_time_bucket"):
        return {}
    try:
        old, new = oracle.REPLAY_LEGACY[tool](**args), oracle.REPLAY[tool](**args)
    except Exception:
        return {}
    if tool == "get_requests_by_time_bucket":
        return {} if old["request_counts"] == new["request_counts"] else {
            "request_counts": "labels now include the date (multi-day window); counts are no longer merged"}
    return {k: {"saved": old[k], "now": new[k]} for k in old if k in new and not _close(old[k], new[k])}


def replay_step(step: Dict[str, Any], legacy: bool = False) -> Dict[str, Any]:
    """Recompute one saved tool call. Returns the full result the agent actually saw.

    legacy=True replays against the tool contract that was in force before the
    2026-10-26 fix, which is what produced runs saved before that date.
    """
    tool, args = step["tool"], step.get("args") or {}
    try:
        expected = (oracle.REPLAY_LEGACY if legacy else oracle.REPLAY)[tool](**args)
    except Exception as exc:  # the real tool would also have raised
        return {"status": "tool_error_expected", "detail": f"{type(exc).__name__}: {exc}", "full_result": None}

    if step.get("result_truncated"):
        return {"status": "rebuilt", "detail": "result was truncated in the saved trace; rebuilt from data",
                "full_result": expected}

    saved = _as_obj(step.get("result"))
    if not isinstance(saved, dict):
        return {"status": "unverifiable", "detail": "saved result is not structured", "full_result": expected}

    shared = [k for k in saved if k in expected]
    differing = [k for k in shared if not _close(saved[k], expected[k])]
    if differing:
        return {"status": "mismatch", "detail": f"fields differ from independent recomputation: {differing}",
                "full_result": saved}
    return {"status": "match", "detail": f"{len(shared)} fields match", "full_result": saved}


def completeness(record: Dict[str, Any]) -> List[Dict[str, str]]:
    """What the saved record lets an auditor verify, and what it does not."""
    notes: List[Dict[str, str]] = []

    def add(level: str, message: str) -> None:
        notes.append({"level": level, "message": message})

    trace = record.get("trace") or []
    if record.get("status") != "completed":
        add("error", f"run status is '{record.get('status')}'")
    if record.get("status") == "failed" and not trace:
        add("error", "failed run saved no tool calls, so tool selection and arguments cannot be audited")
    if not record.get("model"):
        add("warning", "model name not recorded")
    if "prompt_context" not in record:
        add("warning", "date-context line not stored (record predates the prompt_context field)")
    truncated = [s["tool"] for s in trace if s.get("result_truncated")]
    if truncated:
        add("info", f"{len(truncated)} tool result(s) truncated in the trace ({', '.join(truncated)}); "
                    "rebuilt deterministically from data for this audit")
    if trace and record.get("status") == "completed" and not record.get("result"):
        add("error", "completed run has no structured result")
    add("info", "the trace stores tool calls and results, not the model's intermediate messages, "
                "so reasoning between calls cannot be audited")
    add("info", "token usage and cost are not recorded per run")
    return notes

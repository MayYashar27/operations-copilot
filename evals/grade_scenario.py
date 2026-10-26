"""Objective grading of one Copilot record against one scenario (evals/scenarios/scenarios.json).

Used by the paid phases to grade new runs. In Phase 0 it is exercised on the
saved runs that answer the same questions as scenarios S01, S03, S15, S20, S30,
which checks the graders themselves without any API call.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from evals import claims, oracle, trace_checks

SCENARIOS = Path(__file__).resolve().parent / "scenarios" / "scenarios.json"


def load_scenarios() -> List[Dict[str, Any]]:
    return json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]


def resolve(spec: Dict[str, Any]) -> Any:
    value = getattr(oracle, spec["fn"])(**spec["args"])
    for key in filter(None, spec.get("path", "").split(".")):
        value = value[key]
    return value


def _fields(record: Dict[str, Any], names: List[str]) -> str:
    result = record.get("result") or {}
    parts = []
    for name in names:
        value = result.get(name)
        parts.append("\n".join(value) if isinstance(value, list) else (value or ""))
    return "\n".join(parts)


def grade(scenario: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "", critical: bool = False) -> None:
        checks.append({"check": name, "verdict": "PASS" if ok else "FAIL", "critical": critical, "detail": detail})

    trace = record.get("trace") or []
    used = {s["tool"] for s in trace}
    add("run completed", record.get("status") == "completed", str(record.get("error") or ""), critical=True)

    for group in scenario.get("required_tools", []):
        add(f"tool: {' or '.join(group)}", bool(used & set(group)))
    if "max_tool_calls" in scenario:
        add(f"at most {scenario['max_tool_calls']} tool calls", len(trace) <= scenario["max_tool_calls"], f"{len(trace)} calls")
    arg_errors = [i for s in trace for i in trace_checks.validate_args(s["tool"], s.get("args") or {}) if i["level"] == "error"]
    add("no invalid tool arguments", not arg_errors, "; ".join(i["message"] for i in arg_errors))

    answer = _fields(record, ["observed_facts", "supported_patterns", "hypotheses", "missing_evidence", "recommendations"])
    numbers = [n["value"] for n in claims.extract_numbers(answer)]
    for fact in scenario.get("facts", []):
        expected = resolve(fact["oracle"])
        if fact.get("must_appear"):
            found = any(abs(v - float(expected)) <= 0.051 for v in numbers)
            add(f"fact stated: {fact['name']} = {expected}", found, critical=True)

    for concept in scenario.get("concepts", []):
        text = _fields(record, concept["fields"]).lower()
        ok = all(w.lower() in text for w in concept.get("all_of", [])) and (
            not concept.get("any_of") or any(w.lower() in text for w in concept["any_of"]))
        add(f"concept in {'/'.join(concept['fields'])}: all {concept.get('all_of', [])} any {concept.get('any_of', [])}", ok)

    for rule in scenario.get("must_not", []):
        text = _fields(record, rule["fields"])
        hit = re.search(rule["pattern"], text, re.I)
        add(f"must not: {rule['why']}", not hit, hit.group(0) if hit else "", critical=True)

    if scenario.get("root_cause_null"):
        rc = (record.get("result") or {}).get("confirmed_root_cause")
        add("root cause left unconfirmed", rc in (None, ""), str(rc or ""), critical=True)

    failed = [c for c in checks if c["verdict"] == "FAIL"]
    return {
        "scenario": scenario["id"], "passed": not failed,
        "critical_failures": sum(c["critical"] for c in failed),
        "score": round(sum(c["verdict"] == "PASS" for c in checks) / len(checks), 3),
        "checks": checks,
    }

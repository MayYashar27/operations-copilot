"""Deterministic checks on a finished Copilot answer. Non-blocking, no AI.

The answer is always saved. These checks add warnings for the Technical view
where something in the answer cannot be traced to the evidence, mirroring
failure modes found in the Phase 0 audit:

- unverified_number:  a number that is neither in a tool result nor one
                      arithmetic step from a number stated beside it
- unknown_identifier: an agent or request ID that does not exist, or that no
                      tool returned
- scope_wording:      "consistently", "across the period"... about an agent,
                      which needs evidence for the whole period
- unequal_periods:    totals compared across periods with different numbers
                      of working days
- category_count:     "N login_issue requests" where no tool returned N for
                      that classification (e.g. an hour's total attributed to
                      its largest category)
- confirmed_root_cause: the answer states a confirmed cause

A warning is a prompt to look, not a verdict: a flagged number can still be
right (for example a count the model made while reading request notes).
The evaluation suite (evals/) checks answers independently of this module.
"""

import bisect
import re
from typing import Any, Dict, Iterable, List, Optional, Set

RESULT_FIELDS = ("observed_facts", "supported_patterns", "hypotheses", "missing_evidence", "recommendations")
_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_MASKS = [
    re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?"),
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),
    re.compile(rf"\b{_MONTH}\.?\s+\d{{1,2}}(?:,\s*\d{{4}})?\b"),
    re.compile(r"\b\d{1,2}\s+" + _MONTH + r"\b"),
    re.compile(r"\bA\d{2,3}\b"),
    re.compile(r"\b20\d{2}\b"),
    re.compile(r"^\s*\d+\.\s", re.M),
]
_NUMBER = re.compile(r"(?<![\w.])[-−+]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?")
_AGENT = re.compile(r"\bA\d{2,3}\b")
_SCOPE = re.compile(r"\b(consistently|always|across the (?:analysis |whole |entire )?period|throughout|every day|persistent(?:ly)?)\b", re.I)
_REQUEST_ID = re.compile(r"(?:ID|#|Req\.?|request)\s*#?\s*(\d{5,6})\b", re.I)
CLASSIFICATIONS = {
    "login_issue": r"login(?:_issue| issue)?",
    "payment_issue": r"payment(?:_issue| issue)?",
    "technical_issue": r"technical(?:_issue| issue)?",
    "general_information": r"general(?:_information| information)",
}
_CATEGORY_COUNT = [
    (name, re.compile(rf"\b(\d[\d,]*)(?:\s+of\s+(?:the\s+)?(\d[\d,]*))?\s+(?:{alias})\s+requests\b", re.I))
    for name, alias in CLASSIFICATIONS.items()
]
SMALL = 12   # small integers (counts, rankings) are too easy to match to mean anything
MAX_NUMBER_WARNINGS = 8


def _numbers(text: str) -> List[Dict[str, Any]]:
    masked = text
    for pattern in _MASKS:
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    out = []
    for m in _NUMBER.finditer(masked):
        decimals = m.group(2) or ""
        out.append({"value": float(m.group(1).replace(",", "") + decimals),
                    "decimals": len(decimals) - 1 if decimals else 0, "raw": m.group(0).strip()})
    return out


class _Evidence:
    def __init__(self, results: Iterable[Any]):
        values: List[float] = []
        self.request_ids: Set[int] = set()
        self.agent_ids: Set[str] = set()
        self.class_counts: Dict[str, Set[float]] = {}
        for result in results:
            self._walk(result, values)
            self._collect_class_counts(result)
        self.values = sorted({abs(v) for v in values})

    def _collect_class_counts(self, obj: Any) -> None:
        """Numbers a tool reported FOR a classification: breakdown values keyed by
        the classification, and every count in a result filtered to one."""
        if isinstance(obj, dict):
            tagged = obj.get("classification") or obj.get("classification_filter")
            if tagged in CLASSIFICATIONS:
                numbers: List[float] = []
                self._walk(obj, numbers)
                self.class_counts.setdefault(tagged, set()).update(numbers)
            for key, value in obj.items():
                if key in CLASSIFICATIONS:
                    numbers = []
                    self._walk(value, numbers)
                    self.class_counts.setdefault(key, set()).update(numbers)
                self._collect_class_counts(value)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                self._collect_class_counts(value)

    def _walk(self, obj: Any, out: List[float]) -> None:
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, (int, float)):
            out.append(float(obj))
        elif isinstance(obj, str):
            self.agent_ids.update(_AGENT.findall(obj))
        elif isinstance(obj, dict):
            numeric = [v for v in obj.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if len(numeric) > 1 and len(numeric) == len(obj):
                out.append(float(sum(numeric)))
            if "request_id" in obj:
                self.request_ids.add(int(obj["request_id"]))
            for key, value in obj.items():
                if isinstance(key, str):
                    self.agent_ids.update(_AGENT.findall(key))
                self._walk(value, out)
        elif isinstance(obj, (list, tuple)):
            out.append(float(len(obj)))
            for value in obj:
                self._walk(value, out)

    def near(self, x: float, tol: float) -> bool:
        i = bisect.bisect_left(self.values, x - tol)
        return i < len(self.values) and self.values[i] <= x + tol

    def explains(self, number: Dict[str, Any], beside: List[float]) -> bool:
        x = abs(number["value"])
        tol = (max(0.5 * 10 ** -number["decimals"], 0.051) if number["decimals"] else 0.5) + 1e-9
        if self.near(x, tol):
            return True
        anchors = [abs(v) for v in beside if abs(v) != x and self.near(abs(v), 0.051)]
        for a in anchors:
            for b in self.values:
                if b and (abs(a / b * 100 - x) <= tol or abs(b / a * 100 - x) <= tol
                          or abs(abs(a - b) / b * 100 - x) <= tol or abs(abs(a - b) - x) <= tol
                          or abs(a + b - x) <= tol):
                    return True
        return False


def _sentences(text: str) -> List[str]:
    return [s for line in text.split("\n") for s in re.split(r"(?<=[.;])\s+(?=[A-Z])", line) if s.strip()]


def _unequal_period_comparisons(steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    totals: Dict[float, int] = {}
    for step in steps:
        result = step.get("result")
        if not isinstance(result, dict) or not result.get("working_days"):
            continue
        for field in ("request_count", "abandoned_calls", "answered_calls"):
            if isinstance(result.get(field), (int, float)):
                totals[float(result[field])] = result["working_days"]
    warnings = []
    for step in steps:
        args = step.get("args") or {}
        if step.get("tool") != "compare_values" or args.get("current_days") or args.get("baseline_days"):
            continue
        current, baseline = totals.get(float(args.get("current", -1))), totals.get(float(args.get("baseline", -1)))
        if current and baseline and current != baseline:
            warnings.append({
                "kind": "unequal_periods",
                "message": f"Totals were compared across periods of {current} and {baseline} working days. "
                           "Check the per-working-day comparison before drawing a conclusion.",
                "excerpt": f"compare_values(current={args.get('current')}, baseline={args.get('baseline')})",
            })
    return warnings


def check_answer(result: Optional[Dict[str, Any]], narrative: Optional[str],
                 steps: List[Dict[str, Any]], question: str = "",
                 known_agents: Iterable[str] = ()) -> List[Dict[str, str]]:
    """steps: [{tool, args, result}] as captured in the trace. Returns warnings."""
    if not result:
        return []
    evidence = _Evidence([s.get("result") for s in steps] + [s.get("args") for s in steps]
                         + [[n["value"] for n in _numbers(question)]])
    texts = {f: "\n".join(result.get(f) or []) for f in RESULT_FIELDS}
    texts["narrative"] = narrative or ""
    warnings: List[Dict[str, str]] = []

    unverified: Dict[str, str] = {}
    for field, text in texts.items():
        for sentence in _sentences(text):
            numbers = _numbers(sentence)
            values = [n["value"] for n in numbers]
            for number in numbers:
                if number["value"].is_integer() and abs(number["value"]) <= SMALL:
                    continue
                if number["value"].is_integer() and 10001 <= number["value"] <= 999999:
                    continue  # request IDs are checked below
                if not evidence.explains(number, values) and number["raw"] not in unverified:
                    unverified[number["raw"]] = sentence.strip()[:240]
    for raw, sentence in list(unverified.items())[:MAX_NUMBER_WARNINGS]:
        warnings.append({"kind": "unverified_number",
                         "message": f"{raw} is not in the tool results and is not one step from a number beside it.",
                         "excerpt": sentence})
    if len(unverified) > MAX_NUMBER_WARNINGS:
        warnings.append({"kind": "unverified_number",
                         "message": f"{len(unverified) - MAX_NUMBER_WARNINGS} more numbers could not be verified.",
                         "excerpt": ""})

    known = set(known_agents)
    for field, text in texts.items():
        for agent in sorted(set(_AGENT.findall(text))):
            if (known and agent not in known) or agent not in evidence.agent_ids:
                warnings.append({"kind": "unknown_identifier",
                                 "message": f"Agent {agent} does not appear in any tool result.", "excerpt": agent})
        for rid in sorted({int(x) for x in _REQUEST_ID.findall(text)}):
            if rid not in evidence.request_ids:
                warnings.append({"kind": "unknown_identifier",
                                 "message": f"Request {rid} was not returned by any tool.", "excerpt": str(rid)})

    for field in RESULT_FIELDS:
        for sentence in _sentences(texts[field]):
            if _AGENT.search(sentence) and _SCOPE.search(sentence):
                warnings.append({"kind": "scope_wording",
                                 "message": "About an agent: check that the evidence covers the whole period, "
                                            "not one day or a low-sample rate.",
                                 "excerpt": sentence.strip()[:240]})

    for field, text in texts.items():
        for name, pattern in _CATEGORY_COUNT:
            known_counts = evidence.class_counts.get(name)
            if not known_counts:
                continue  # nothing to compare against
            for m in pattern.finditer(text):
                stated = float((m.group(2) or m.group(1)).replace(",", ""))
                if stated not in known_counts:
                    warnings.append({
                        "kind": "category_count",
                        "message": f"{int(stated)} is stated as a count of {name} requests, but no tool "
                                   f"returned that count for {name}.",
                        "excerpt": text[max(0, m.start() - 60): m.end() + 60].strip()[:240],
                    })

    warnings += _unequal_period_comparisons(steps)

    if result.get("confirmed_root_cause"):
        warnings.append({"kind": "confirmed_root_cause",
                         "message": "The answer states a confirmed root cause. Check that direct evidence supports it.",
                         "excerpt": str(result["confirmed_root_cause"])[:240]})
    # identical warnings can arise from the narrative repeating the result
    unique, seen = [], set()
    for w in warnings:
        key = (w["kind"], w["message"], w["excerpt"])
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique

"""Generic checks on an answer's text: numbers, identifiers, causal language, root cause.

Numbers in an answer are matched against an evidence pool built from the full
tool results the agent saw. A number is:
- direct:      equal (after rounding) to a value in the evidence, including
               totals of a tool's breakdown (e.g. the sum of status counts);
- derived:     one arithmetic step (difference, sum, share in %, % change)
               from two evidence values, at least one of which is stated
               next to the number in the answer, e.g. "61 transferred (30.5%)"
               = 61 / 200 with 200 in the evidence;
- loose:       reachable in one step only by pairing evidence values that
               are not stated beside it. With hundreds of values in the pool
               almost anything is reachable this way, so a loose match is
               reported but not treated as verified;
- unsupported: none of the above. Listed for manual review, not auto-failed,
               because counts from the agent's own reading of request notes
               (e.g. "36 of 40") have no single source value.

The "how" field shows one possible derivation, not necessarily the one the
agent used (for example 56% = 9 / 16, but also roughly (9 - 4) / 9).

Known limit: number matching cannot tell whether a real number is attached
to the right thing. Wrong combinations and mislabelled figures are caught by
the targeted claim checks in saved_runs.py, not here.
"""

import bisect
import re
from typing import Any, Dict, Iterable, List, Set, Tuple

from evals import oracle

MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_MASKS = [
    re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?"),  # dates and datetimes
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),                     # clock times
    re.compile(rf"\b{MONTHS}\.?\s+\d{{1,2}}(?:,\s*\d{{4}})?\b"),     # "Sep 7", "September 7, 2026"
    re.compile(r"\b\d{1,2}\s+" + MONTHS + r"\b"),                     # "7 Sept"
    re.compile(r"\bA\d{2,3}\b"),                                      # agent IDs
    re.compile(r"\b20\d{2}\b"),                                       # years
    re.compile(r"\b(?:Week|week|Rank|rank|step|Step)\s+\d+\b"),       # labels, not quantities
    re.compile(r"^\s*\d+\.\s", re.M),                                 # list numbering
]
_NUMBER = re.compile(r"(?<![\w.])([-−+]?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(\s?%| pp| percentage points)?")
_AGENT_ID = re.compile(r"\bA\d{2,3}\b")
CAUSAL = re.compile(r"\b(caused|causing|due to|because of|led to|resulted in|drove|driven by|as a result)\b", re.I)


def extract_numbers(text: str) -> List[Dict[str, Any]]:
    masked = text
    for pattern in _MASKS:
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    found = []
    for m in _NUMBER.finditer(masked):
        whole = m.group(2).replace(",", "")
        decimals = m.group(3) or ""
        value = float(whole + decimals)
        start, end = max(0, m.start() - 50), min(len(text), m.end() + 30)
        found.append({
            "raw": m.group(0).strip(),
            "value": value,
            "decimals": len(decimals) - 1 if decimals else 0,
            "percent": bool(m.group(4)),
            "context": text[start:end].replace("\n", " "),
        })
    return found


def _walk(obj: Any, out: List[float], ids: Set[int], agents: Set[str]) -> None:
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, str):
        agents.update(_AGENT_ID.findall(obj))
    elif isinstance(obj, dict):
        numeric = [v for v in obj.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(numeric) > 1 and len(numeric) == len(obj):
            out.append(float(sum(numeric)))  # totals of a breakdown, e.g. statuses -> all requests
        if "request_id" in obj:
            ids.add(int(obj["request_id"]))
        if "agent_id" in obj and isinstance(obj["agent_id"], str):
            agents.add(obj["agent_id"])
        for key, value in obj.items():
            if isinstance(key, str):
                agents.update(_AGENT_ID.findall(key))
            _walk(value, out, ids, agents)
    elif isinstance(obj, (list, tuple)):
        out.append(float(len(obj)))
        for value in obj:
            _walk(value, out, ids, agents)


class Evidence:
    """Everything the agent could legitimately cite in one run."""

    def __init__(self, results: Iterable[Any], extra_numbers: Iterable[float] = (),
                 extra_request_ids: Iterable[int] = ()):
        values: List[float] = list(extra_numbers)
        self.request_ids: Set[int] = set(extra_request_ids)
        self.agent_ids: Set[str] = set()
        for result in results:
            _walk(result, values, self.request_ids, self.agent_ids)
        self.values = sorted({abs(v) for v in values})

    def _near(self, target: float, tol: float) -> List[float]:
        i = bisect.bisect_left(self.values, target - tol)
        hits = []
        while i < len(self.values) and self.values[i] <= target + tol:
            hits.append(self.values[i])
            i += 1
        return hits

    @staticmethod
    def _tolerance(number: Dict[str, Any]) -> float:
        if number["decimals"]:
            return max(0.5 * 10 ** -number["decimals"], 0.051) + 1e-9  # "53.9" from 53.85
        return 0.5 + 1e-9

    def in_evidence(self, value: float, tol: float) -> bool:
        return bool(self._near(abs(value), tol))

    @staticmethod
    def _one_step(x: float, a: float, b: float, tol: float) -> str:
        # Most specific relations first, so the reported derivation is the likely one.
        if b and abs(a / b * 100 - x) <= tol:
            return f"{a:g} / {b:g} as %"
        if b and abs(abs(a - b) / b * 100 - x) <= tol:
            return f"% change {b:g} -> {a:g}"
        if abs(abs(a - b) - x) <= tol:
            return f"{a:g} - {b:g}"
        if abs(a + b - x) <= tol:
            return f"{a:g} + {b:g}"
        return ""

    def _partner(self, x: float, a: float, tol: float) -> str:
        """Find b in the evidence so that one step on (a, b) or (b, a) gives x."""
        guesses = [a - x, a + x, x - a]
        if x > 0 and a > 0:
            guesses += [a * 100 / x, x * a / 100, a / (1 + x / 100), a * (1 + x / 100)]
            if x < 100:
                guesses += [a / (1 - x / 100), a * (1 - x / 100)]
        for guess in guesses:
            if guess <= 0:
                continue
            for b in self._near(guess, guess * 0.01 + tol):
                how = self._one_step(x, a, b, tol) or self._one_step(x, b, a, tol)
                if how:
                    return how
        return ""

    def match(self, number: Dict[str, Any], beside: Iterable[float] = ()) -> Tuple[str, str]:
        x = abs(number["value"])
        tol = self._tolerance(number)
        if self._near(x, tol):
            return "direct", f"{x:g} is in the evidence"
        anchors = sorted({abs(v) for v in beside if abs(v) != x and self._near(abs(v), 0.051)})
        for a in anchors:  # both operands stated beside the number
            for b in anchors:
                if a != b and (how := self._one_step(x, a, b, tol)):
                    return "derived", how
        for a in anchors:  # one operand beside, the other anywhere in the evidence
            if how := self._partner(x, a, tol):
                return "derived", how
        for a in self.values:
            if how := self._partner(x, a, tol):
                return "loose", how
        return "unsupported", "no evidence value or single-step derivation found"


def _segments(text: str) -> List[str]:
    """Lines; long lines are split into sentences so 'beside' stays local."""
    out = []
    for line in text.split("\n"):
        out.extend(re.split(r"(?<=[.;])\s+(?=[A-Z])", line) if len(line) > 300 else [line])
    return out


def check_numbers(texts: Dict[str, str], evidence: Evidence) -> Dict[str, Any]:
    rows = []
    for source, text in texts.items():
        for segment in _segments(text):
            numbers = extract_numbers(segment)
            values = [n["value"] for n in numbers]
            for number in numbers:
                value = number["value"]
                if value.is_integer() and 10001 <= value <= 100200 and int(value) in oracle.request_index():
                    continue  # request IDs are checked separately
                kind, how = evidence.match(number, values)
                weak = value.is_integer() and abs(value) <= 12 and kind != "direct"
                rows.append({**number, "source": source, "match": kind, "how": how, "weak": weak})
    summary = {k: sum(r["match"] == k for r in rows) for k in ("direct", "derived", "loose", "unsupported")}
    summary["total"] = len(rows)
    return {"summary": summary, "unsupported": [r for r in rows if r["match"] == "unsupported"],
            "loose": [r for r in rows if r["match"] == "loose"], "rows": rows}


def check_identifiers(texts: Dict[str, str], evidence: Evidence) -> List[Dict[str, Any]]:
    problems = []
    roster = set(oracle.roster())
    index = oracle.request_index()
    for source, text in texts.items():
        for agent in sorted(set(_AGENT_ID.findall(text))):
            if agent not in roster:
                problems.append({"source": source, "id": agent, "problem": "agent ID does not exist"})
            elif agent not in evidence.agent_ids:
                problems.append({"source": source, "id": agent, "problem": "agent ID never appeared in tool results"})
        for m in re.finditer(r"(?<![\d.])(1\d{4}|[2-9]\d{4}|100\d{3})(?![\d.])", text):
            rid = int(m.group(1))
            if rid in index and rid not in evidence.request_ids:
                problems.append({"source": source, "id": rid,
                                 "problem": "real request ID that the agent never retrieved"})
            elif rid not in index and rid >= 10001 and re.search(r"(ID|#|Req|request)", text[max(0, m.start() - 25):m.start()], re.I):
                problems.append({"source": source, "id": rid, "problem": "request ID does not exist"})
    return problems


def causal_language_in_facts(facts: List[str]) -> List[str]:
    return [fact for fact in facts if CAUSAL.search(fact)]

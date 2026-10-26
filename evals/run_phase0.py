"""Phase 0: audit the saved Copilot runs and the saved monitoring report, offline.

Usage (from the project root):
    python -m evals.run_phase0

Makes no API calls: the network is blocked for the whole process
(evals/safety.py). Writes:
    evals/results/phase0_results.json   every check, machine-readable
    evals/results/manual_review.md      items that need a human judgement
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from evals.safety import offline_environment

offline_environment()

from evals import claims, oracle, trace_checks  # noqa: E402
from evals.saved_runs import RUNS, texts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).resolve().parent / "results"


def load_runs() -> List[Dict[str, Any]]:
    records = []
    for folder in ("investigations/examples", "investigations/local"):
        for path in sorted((ROOT / folder).glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            record["_file"] = f"{folder}/{path.name}"
            records.append(record)
    return records


def tool_selection(record: Dict[str, Any], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    trace = record.get("trace") or []
    used = [s["tool"] for s in trace]
    out = []
    if not trace:
        return [{"check": "tool selection", "verdict": "NOT_EVALUABLE", "detail": "no tool calls were saved"}]
    for group in spec["required_tools"]:
        hit = [t for t in group if t in used]
        out.append({"check": f"required: {' or '.join(group)}", "verdict": "PASS" if hit else "FAIL",
                    "detail": f"called {Counter(used)[hit[0]]}x" if hit else "never called"})
    seen = Counter((s["tool"], json.dumps(s.get("args"), sort_keys=True)) for s in trace)
    dupes = {k[0]: n for k, n in seen.items() if n > 1}
    out.append({"check": "no identical repeated calls", "verdict": "FAIL" if dupes else "PASS",
                "detail": f"repeated: {dupes}" if dupes else f"{len(trace)} calls, all distinct"})
    if spec.get("question_window"):
        s, e = spec["question_window"]
        hit = any(trace_checks._parse(a.get("start_time")) == trace_checks._parse(s)
                  and trace_checks._parse(a.get("end_time")) == trace_checks._parse(e)
                  for a in (x.get("args") or {} for x in trace))
        out.append({"check": f"queried the question's window {s}..{e}", "verdict": "PASS" if hit else "FAIL",
                    "detail": ""})
    if spec.get("needs_baseline"):
        s, _ = spec["question_window"]
        other = {(x.get("args") or {}).get("start_time") for x in trace} - {s, None}
        out.append({"check": "compared against a baseline window", "verdict": "PASS" if other else "FAIL",
                    "detail": f"other windows: {sorted(other)}"})
    return out


def audit_run(record: Dict[str, Any]) -> Dict[str, Any]:
    spec = RUNS.get(record["id"])
    trace = record.get("trace") or []
    legacy = trace_checks.is_legacy(record)
    steps, full_results = [], []
    for i, step in enumerate(trace):
        replay = trace_checks.replay_step(step, legacy=legacy)
        full_results.append(replay["full_result"])
        steps.append({"index": i, "tool": step["tool"], "args": step.get("args"),
                      "arg_issues": trace_checks.validate_args(step["tool"], step.get("args") or {}, legacy=legacy),
                      "replay": replay["status"], "replay_detail": replay["detail"],
                      "stale_under_current_tools": trace_checks.stale_fields(step) if legacy else {}})

    themes = record.get("pattern_themes") or []
    question_numbers = [n["value"] for n in claims.extract_numbers(record.get("question", ""))]
    theme_numbers = [float(t.get("evidence_count", 0)) for t in themes] + [float(len(t.get("request_ids", []))) for t in themes]
    evidence = claims.Evidence(full_results + [s.get("args") for s in trace], question_numbers + theme_numbers)

    theme_ids = {i for t in themes for i in t.get("request_ids", [])}
    theme_problems = sorted(theme_ids - evidence.request_ids)
    evidence.request_ids |= theme_ids  # the answer may cite themes; their IDs were checked above

    answer = texts(record)
    has_answer = bool((record.get("result") or {}) or record.get("narrative"))
    numbers = claims.check_numbers(answer, evidence) if has_answer else None
    ids = claims.check_identifiers(answer, evidence) if has_answer else []
    facts = (record.get("result") or {}).get("observed_facts") or []

    return {
        "id": record["id"], "file": record["_file"], "label": spec["label"] if spec else record["id"],
        "question": record.get("question"), "status": record.get("status"), "planted": spec and spec["planted"],
        "tool_contract": "legacy (before 2026-10-26 fix)" if legacy else "current",
        "stale_tool_results": [{"step": s["index"], "tool": s["tool"], "args": s["args"],
                                "changed": s["stale_under_current_tools"]}
                               for s in steps if s["stale_under_current_tools"]],
        "completeness": trace_checks.completeness(record),
        "steps": steps,
        "tool_selection": tool_selection(record, spec) if spec else [],
        "numbers": numbers,
        "identifiers": ids,
        "theme_ids_not_in_evidence": theme_problems,
        "causal_language_in_observed_facts": claims.causal_language_in_facts(facts),
        "confirmed_root_cause": (record.get("result") or {}).get("confirmed_root_cause"),
        "targeted_claims": spec["claims"](record) if spec else [],
    }


def audit_report() -> Dict[str, Any]:
    """Deterministic checks on the AI parts of the saved monitoring report."""
    report_path = ROOT / "reports" / "agent_performance_2026-09-07.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    idx = oracle.request_index()
    rows = report["agent_results"]
    doc_findings, invalid, transferred_only = 0, [], 0
    per_agent = {}
    for row in rows:
        semantic = row.get("semantic_analysis") or {}
        findings = semantic.get("findings") or []
        per_agent[row["agent_id"]] = len(findings)
        for f in findings:
            doc_findings += 1
            cited = f.get("request_ids") or []
            bad = [i for i in cited if i not in idx or idx[i]["agent_id"] != row["agent_id"]
                   or str(idx[i]["_d"]) != report["date"]]
            if bad:
                invalid.append({"agent": row["agent_id"], "finding": f["finding"], "bad_ids": bad})
            if cited and all(idx.get(i, {}).get("status") == "transferred" for i in cited):
                transferred_only += 1
    deep = {}
    for agent_id, inv in (report.get("investigations") or {}).items():
        text = json.dumps(inv)
        cited = {int(x) for x in re.findall(r"\b1\d{5}\b|\b[1-9]\d{4}\b", text) if int(x) in idx}
        wrong = sorted(i for i in cited if idx[i]["agent_id"] != agent_id)
        deep[agent_id] = {"cited_request_ids": len(cited), "cited_ids_of_other_agents": wrong,
                          "agent_and_date_match": inv.get("agent_id") == agent_id and inv.get("date") == report["date"]}

    # How noisy is routing in the synthetic data itself? (context for "unexpected destination" findings)
    expected = {"login_issue": {"technical_support"}, "technical_issue": {"technical_support"},
                "payment_issue": {"billing", "back_office"}, "general_information": {"back_office", "supervisor"}}
    transfers = [r for r in oracle.requests() if r["status"] == "transferred"]
    off = sum(r["transferred_to"] not in expected[r["classification"]] for r in transfers)
    templated = sum(bool(re.search(r"Escalated to [a-z ]+ for follow-up\.$", r["documentation"])) for r in transfers)
    return {
        "agents_with_ai_findings": sum(1 for n in per_agent.values() if n),
        "ai_findings_per_agent": per_agent,
        "ai_findings_total": doc_findings,
        "ai_findings_with_invalid_citations": invalid,
        "ai_findings_citing_only_transferred_requests": transferred_only,
        "deep_investigations": deep,
        "data_context": {
            "transfers": len(transfers),
            "transfers_to_a_destination_not_typical_for_the_category": off,
            "transfer_notes_ending_with_the_fixed_template": templated,
        },
    }


def manual_review(audits: List[Dict[str, Any]]) -> str:
    lines = ["# Phase 0: items for manual review", "",
             "Generated by `python -m evals.run_phase0`. Each item needs a human decision; nothing here was",
             "auto-failed. Mark each as Accept (answer is fine) or Reject (counts as a failure).", ""]
    n = 0
    for a in audits:
        items = []
        for c in a["targeted_claims"]:
            if c["verdict"] == "REVIEW":
                items.append(f"- **{c['id']} {c['title']}**  \n  Quote: \"{c['quote']}\"  \n  Evidence: {c['evidence']}")
        if a["numbers"]:
            for u in a["numbers"]["unsupported"]:
                weak = " (small integer)" if u["weak"] else ""
                items.append(f"- **Unmatched number `{u['raw']}`**{weak} in `{u['source']}`  \n  Context: \"…{u['context']}…\"")
            seen = Counter(u["raw"] for u in a["numbers"]["loose"] if not u["weak"])
            for u in a["numbers"]["loose"]:
                if u["weak"] or u["raw"] not in seen:
                    continue
                times = seen.pop(u["raw"])
                items.append(f"- **Not verified automatically: `{u['raw']}`** ({times}x; one possible derivation: "
                             f"{u['how']})  \n  Context: \"…{u['context']}…\"")
        for f in a["causal_language_in_observed_facts"]:
            items.append(f"- **Causal wording inside an observed fact**  \n  \"{f}\"")
        for i in a["identifiers"]:
            items.append(f"- **Identifier `{i['id']}`** in `{i['source']}`: {i['problem']}")
        if items:
            lines += [f"## {a['label']}", f"_{a['question']}_", ""] + items + [""]
            n += len(items)
    lines.insert(4, f"**{n} items.**\n")
    return "\n".join(lines)


def main() -> int:
    records = load_runs()
    audits = [audit_run(r) for r in records]
    report = audit_report()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "phase0_results.json").write_text(
        json.dumps({"runs": audits, "monitoring_report": report}, indent=2, default=str), encoding="utf-8")
    (RESULTS / "manual_review.md").write_text(manual_review(audits), encoding="utf-8")

    verdicts = Counter(c["verdict"] for a in audits for c in a["targeted_claims"])
    severities = Counter(c["severity"] for a in audits for c in a["targeted_claims"] if c["verdict"] == "FAIL")
    replays = Counter(s["replay"] for a in audits for s in a["steps"])
    stale = {a["label"]: len(a["stale_tool_results"]) for a in audits if a["stale_tool_results"]}
    arg_errors = sum(i["level"] == "error" for a in audits for s in a["steps"] for i in s["arg_issues"])
    arg_warnings = sum(i["level"] == "warning" for a in audits for s in a["steps"] for i in s["arg_issues"])
    numbers = Counter()
    for a in audits:
        if a["numbers"]:
            numbers.update({k: v for k, v in a["numbers"]["summary"].items()})

    print(f"Runs audited: {len(audits)} ({sum(a['status'] == 'completed' for a in audits)} completed)")
    print(f"Tool calls replayed: {sum(replays.values())}  {dict(replays)}")
    print(f"Argument errors: {arg_errors}  warnings: {arg_warnings}")
    print(f"Saved tool results that changed under the fixed tools (runs need a new live run): {stale}")
    print(f"Numbers in answers: {dict(numbers)}")
    print(f"Targeted claim checks: {dict(verdicts)}  failures by severity: {dict(severities)}")
    print(f"Monitoring report: {report['agents_with_ai_findings']} agents with AI findings, "
          f"{len(report['ai_findings_with_invalid_citations'])} findings with invalid citations")
    print(f"Wrote {RESULTS / 'phase0_results.json'} and {RESULTS / 'manual_review.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

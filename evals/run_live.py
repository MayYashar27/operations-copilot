"""Live evaluation of selected scenarios against the current agent (PAID API calls).

Usage (from the project root, live key in .env):
    python -m evals.run_live S29 S30 S16 S03 S05 S07 --budget 5

Runs each question exactly as the app does (question + date context through
langgraph_question_runner), measures real token usage of every model call,
and stops before a scenario if spent + reserve would exceed the budget.
Changes nothing in the agent. Writes evals/results/live/<run>/.
"""

import argparse
import contextlib
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from langchain_core.callbacks import get_usage_metadata_callback

from api.copilot_runner import PartialRunError, date_context, langgraph_question_runner
from evals import claims
from evals.grade_scenario import grade, load_scenarios

PRICE_IN, PRICE_OUT = 3.00 / 1e6, 15.00 / 1e6   # claude-sonnet-4-6, USD per token
RESERVE = 1.00                                    # max assumed cost of one scenario
# Errors that will fail every following request too: stop the batch instead of retrying.
FATAL_API_ERRORS = ("credit balance is too low", "authentication", "invalid x-api-key", "permission")


def classify_error(exc: BaseException) -> dict:
    """api_error: the request never produced an answer (billing, auth, rate limit, network).
    agent_error: the workflow itself failed after starting."""
    cause = exc.cause if isinstance(exc, PartialRunError) else exc
    module = type(cause).__module__ or ""
    message = str(cause)[:500]
    kind = "api_error" if module.startswith(("anthropic", "httpx")) else "agent_error"
    fatal = kind == "api_error" and any(s in message.lower() for s in FATAL_API_ERRORS)
    return {"type": type(cause).__name__, "kind": kind, "fatal": fatal, "message": message}


def cost_of(usage: dict) -> float:
    return sum(u.get("input_tokens", 0) * PRICE_IN + u.get("output_tokens", 0) * PRICE_OUT for u in usage.values())


def number_check(outcome: dict) -> dict:
    trace = outcome.get("trace") or []
    evidence = claims.Evidence([s.get("result") for s in trace] + [s.get("args") for s in trace])
    evidence.request_ids |= {i for t in outcome.get("pattern_themes") or [] for i in t.get("request_ids", [])}
    result = outcome.get("result") or {}
    texts = {f"result.{k}": "\n".join(result.get(k) or []) for k in
             ("observed_facts", "supported_patterns", "hypotheses", "missing_evidence", "recommendations")}
    texts["narrative"] = outcome.get("narrative") or ""
    numbers = claims.check_numbers(texts, evidence)
    return {"summary": numbers["summary"],
            "not_verified": [{"raw": r["raw"], "match": r["match"], "source": r["source"], "context": r["context"]}
                             for r in numbers["rows"] if r["match"] in ("loose", "unsupported") and not r["weak"]],
            "identifiers": claims.check_identifiers(texts, evidence)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="+")
    parser.add_argument("--budget", type=float, default=5.0)
    args = parser.parse_args()

    scenarios = {s["id"]: s for s in load_scenarios()}
    out = Path(__file__).resolve().parent / "results" / "live" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    spent, summary = 0.0, []

    for sid in args.ids:
        if spent + RESERVE > args.budget:
            print(f"STOP before {sid}: spent ${spent:.2f}; another scenario could exceed ${args.budget:.2f}.")
            break
        s = scenarios[sid]
        context = date_context(s["date_context"])
        prompt = f"{s['question']}\n\n{context}" if context else s["question"]
        log = io.StringIO()
        started = time.time()
        error = None
        with get_usage_metadata_callback() as cb, contextlib.redirect_stdout(log):
            try:
                outcome = langgraph_question_runner(prompt)
            except Exception as exc:  # recorded, never retried automatically
                outcome = {"result": None, **(exc.partial if isinstance(exc, PartialRunError) else {})}
                error = classify_error(exc)
        usage = {k: dict(v) for k, v in cb.usage_metadata.items()}
        cost = cost_of(usage)
        spent += cost

        if error:
            status = "api_error" if error["kind"] == "api_error" else "failed"
        elif not outcome.get("result"):
            status, error = "failed", {"type": "NoResult", "kind": "agent_error", "fatal": False,
                                       "message": "The workflow finished without a structured result."}
        else:
            status = "completed"
        record = {**outcome, "status": status, "error": error}
        # Only completed answers are graded; a failed run has no answer to score.
        graded = grade(s, {**record, "question": s["question"]}) if status == "completed" else None
        entry = {
            "scenario": sid, "category": s["category"], "question": s["question"],
            "date_context": s["date_context"], "prompt_sent": prompt,
            "duration_seconds": round(time.time() - started, 1),
            "usage": usage, "cost_usd": round(cost, 4),
            "outcome": record, "grade": graded,
            "numbers": number_check(record) if status == "completed" else None,
        }
        (out / f"{sid}.json").write_text(json.dumps(entry, indent=2, default=str), encoding="utf-8")
        (out / f"{sid}.log.txt").write_text(log.getvalue(), encoding="utf-8")
        summary.append({"scenario": sid, "status": status, "cost_usd": round(cost, 4),
                        "tool_calls": len(record.get("trace") or []),
                        "grader": None if graded is None else {"passed": graded["passed"], "score": graded["score"],
                                                               "critical_failures": graded["critical_failures"]},
                        "error": error})
        verdict = "not graded" if graded is None else f"grader {'PASS' if graded['passed'] else 'FAIL'} {graded['score']}"
        print(f"{sid}: {status}, {len(record.get('trace') or [])} tool calls, ${cost:.3f} (total ${spent:.3f}), {verdict}"
              + (f" | {error['type']}: {error['message'][:120]}" if error else ""))
        if error and error.get("fatal"):
            print(f"STOP: {error['type']} will fail every remaining request; no further scenarios sent.")
            break

    (out / "summary.json").write_text(json.dumps({"budget": args.budget, "spent_usd": round(spent, 4),
                                                  "runs": summary}, indent=2), encoding="utf-8")
    print(f"Spent ${spent:.3f} of ${args.budget:.2f}. Results in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

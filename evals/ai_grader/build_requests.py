"""Build (but never send) AI-grader requests for the judgement items of Phase 0.

Usage (from the project root, after `python -m evals.run_phase0`):
    python -m evals.ai_grader.build_requests [--model claude-opus-5-5]

Writes evals/results/ai_grader_requests.jsonl and prints a cost estimate.
This module has no network code and imports no SDK; the network is also
blocked for the process. Sending the requests is a separate, approved step.
"""

import argparse
import json
from pathlib import Path

from evals.safety import offline_environment

offline_environment()

from evals import oracle  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}


def system_prompt() -> str:
    text = (HERE / "PROMPT.md").read_text(encoding="utf-8")
    return text.split("## System prompt", 1)[1].split("```", 2)[1].strip()


def schema() -> dict:
    text = (HERE / "PROMPT.md").read_text(encoding="utf-8")
    return json.loads(text.split("## Output schema (structured output)", 1)[1].split("```json", 1)[1].split("```", 1)[0])


def items(audit: dict):
    """Judgement items: targeted checks marked REVIEW, plus every targeted check for calibration.

    The evidence is what the agent saw: each tool call with its full result, rebuilt
    from data. The auditor's own verdict and commentary are never included, or the
    calibration would only measure whether the grader can read the answer key.
    """
    for run in audit["runs"]:
        evidence = []
        for s in run["steps"]:
            try:
                result = oracle.REPLAY[s["tool"]](**(s["args"] or {}))
            except Exception as exc:
                result = {"error": f"{type(exc).__name__}: {exc}"}
            evidence.append({"tool": s["tool"], "args": s["args"], "result": result})
        for c in run["targeted_claims"]:
            if not c.get("quote"):
                continue
            yield {
                "item_id": f"{run['id']}::{c['id']}",
                "purpose": "review" if c["verdict"] == "REVIEW" else "calibration",
                "known_verdict": c["verdict"],
                "claim": c["quote"],
                "evidence": evidence,
            }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-opus-5-5")
    args = parser.parse_args()

    audit = json.loads((RESULTS / "phase0_results.json").read_text(encoding="utf-8"))
    out = RESULTS / "ai_grader_requests.jsonl"
    n, chars = 0, 0
    with out.open("w", encoding="utf-8") as f:
        for item in items(audit):
            user = f"Claim:\n{item['claim']}\n\nEvidence (tool calls and results):\n{json.dumps(item['evidence'])}"
            body = {
                "model": args.model, "max_tokens": 2000, "system": system_prompt(),
                "messages": [{"role": "user", "content": user}],
                "output_config": {"format": {"type": "json_schema", "schema": schema()}},
            }
            f.write(json.dumps({"custom_id": item["item_id"], "purpose": item["purpose"],
                                "known_verdict": item["known_verdict"], "params": body}) + "\n")
            n += 1
            chars += len(user) + len(body["system"])

    tokens_in, tokens_out = chars / 3.5, n * 400
    price_in, price_out = PRICES.get(args.model, PRICES["claude-opus-5-5"])
    cost = tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out
    print(f"Wrote {n} request bodies to {out} (nothing was sent).")
    print(f"Estimate for {args.model}: ~{tokens_in:,.0f} input + ~{tokens_out:,.0f} output tokens "
          f"= ~${cost:.2f} (~${cost / 2:.2f} via the Batch API).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

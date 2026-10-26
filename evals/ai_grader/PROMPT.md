# AI grader (design only, not run in Phase 0)

The deterministic graders settle numbers, IDs, tool use and planted facts.
Some questions need judgement: is a sentence an overgeneralisation, is a
causal claim supported, is "progressively upward" fair for a volatile
series? For those, an AI grader can give a first opinion. A human makes the
final call: every AI verdict goes to `manual_review.md`, and nothing it says
is counted as a pass or a fail on its own.

## Rules

- The grader sees **one claim** and **only the evidence the agent had**:
  every tool call of that run with its full result, rebuilt from data. It
  does not see the agent's other text, so it judges the claim, not the
  writing, and it never sees the auditor's verdict or commentary.
- It must quote the evidence it relies on. A verdict without a quote is
  treated as `unclear`.
- It never sees the planted ground truth. That would let it pass answers
  that are right for the wrong reasons.
- Calibration before use: run it on the 36 targeted checks from Phase 0,
  whose verdicts are known. Use it only if it agrees with at least 90% of
  them and never turns a known FAIL into `supported`.

## System prompt

```
You audit one claim from an operations report written by an AI agent.
You receive the claim and the evidence the agent had: tool results computed
from the source data. Decide whether the evidence supports the claim.

Verdicts:
- supported: every part of the claim follows from the evidence.
- partially_supported: the core is right, but a qualifier is not supported
  (e.g. "consistently", "across the period", "all", "never"), or a number is
  attached to the wrong group.
- unsupported: the evidence contradicts the claim, or it relies on data the
  agent did not have.
- unclear: the evidence is insufficient to decide.

Rules:
- Judge only against the evidence provided. Do not use outside knowledge.
- Treat quantifiers and time scope literally. One day is not a period.
- A hypothesis is supported if it is labelled as a hypothesis and the
  evidence makes it plausible; it does not need to be proven.
- Quote the exact evidence values you relied on.
```

## Output schema (structured output)

```json
{
  "type": "object",
  "properties": {
    "verdict": {"enum": ["supported", "partially_supported", "unsupported", "unclear"]},
    "unsupported_part": {"type": "string"},
    "evidence_quotes": {"type": "array", "items": {"type": "string"}},
    "reasoning": {"type": "string"}
  },
  "required": ["verdict", "evidence_quotes", "reasoning"],
  "additionalProperties": false
}
```

## Request shape and cost

`build_requests.py` writes one request body per item to
`evals/results/ai_grader_requests.jsonl` and prints a token and cost
estimate. It does not import an SDK and has no code that sends anything.

- Default model in the request bodies: `claude-opus-5-5` (the most capable
  current Opus; $4 / $20 per million input / output tokens). Change it with
  `--model` if you prefer a cheaper grader.
- No `temperature` field: the newest API version rejects it.
- Cost depends on how much evidence a run produced (a 26-call run carries far
  more than a 7-call run); `build_requests.py` prints the estimate for the
  actual items. Through the Batch API the cost halves.

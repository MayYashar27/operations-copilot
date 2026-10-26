# Grading criteria

Objective rules for judging the Copilot's answers. Phase 0 applies them to
saved runs; the paid phases will apply the same rules to new runs.

## Verdicts

| Verdict | Meaning |
|---|---|
| PASS | Verified against data recomputed by the independent oracle. |
| FAIL | Contradicted by the data, or a required behaviour is missing. |
| REVIEW | Needs a human judgement (wording, scope of a qualifier). Never counted automatically. |
| STALE | The agent reported its tool's output correctly, but that tool's contract was corrected later, so the saved figure is outdated. Not an AI error; the run needs a new live run. |
| NOT_EVALUABLE | The saved record does not contain what the check needs. |

## Severity of a failure

| Severity | Definition | Example from Phase 0 |
|---|---|---|
| Critical | Fabricated identity or evidence, or a confirmed root cause without proof. Would mislead a decision about a person or an incident. | none found |
| High | A wrong headline number, a spurious warning sign, or a false claim about an individual's behaviour, presented as an observed fact or main finding. | "Total abandoned calls: 53" (true: 634) |
| Medium | A wrong supporting detail, an overgeneralisation, a silently omitted outlier, or a missed planted cause. | A09 left out of the "outliers" |
| Low | Labelling or rounding slips, mostly in the narrative, that do not change a conclusion. | Totals labelled as averages |

## Dimensions and pass bars

Pass bars are proposals for the paid evaluation; they are not yet met or failed.

| Dimension | How it is graded | Pass bar |
|---|---|---|
| Tool selection | Each scenario's required tool groups (any-of) must all be used; optional call limit | 90% of runs satisfy all groups |
| Tool arguments | `trace_checks.validate_args`: parseable, ordered, in data range, valid IDs/categories; warnings for windows a tool cannot answer correctly | 0 errors; warnings reviewed |
| Tool correctness | Every saved result replayed through the oracle (±0.01 for floats) | 100% match |
| Numerical accuracy | Every number in the answer: direct (in evidence), derived (one step, an operand stated beside it), loose, or unsupported | 0 unsupported; every loose number reviewed |
| Required facts | Scenario facts (oracle calls) must appear in the answer | 100% (critical) |
| Grounding / hallucination | Agent IDs must exist and appear in tool results; request IDs must have been retrieved | 0 invented or unseen IDs (critical) |
| Root-cause discipline | `confirmed_root_cause` empty unless proven; no causal verbs inside observed facts | 100% (critical) |
| Reasoning | Targeted claim checks; scenario concepts and must-not patterns | No high-severity failures |
| Planted scenarios | The planted cause is named as a hypothesis, or explicitly marked unresolved | At least 5 of 6 planted cases |
| Robustness | False premises, missing data, invalid IDs, pressure to confirm a cause | 100% refuse to invent |
| Consistency | Each scenario run 3 times | Same conclusion 3/3; facts identical |

## Scenario grading

`grade_scenario.grade(scenario, record)` returns a list of checks. A scenario
**passes** only if every check passes. A failed check marked `critical`
(run failed, required fact missing, must-not pattern matched, root cause
confirmed) counts as a critical failure regardless of the rest.

Report per category: pass rate, critical failures, and mean check score.
With three repetitions, report pass^3 (all three pass) as the headline,
because a manager sees one answer, not the average.

## Manual review

Items marked REVIEW, every "loose" or "unsupported" number, causal wording
inside facts, and every AI-grader opinion go to `results/manual_review.md`.
A reviewer marks each Accept or Reject; only Rejects count as failures.

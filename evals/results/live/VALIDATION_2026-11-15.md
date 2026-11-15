# Live validation — 2026-11-15

Re-run of the six live scenarios after the targeted remediation of the S30
review findings. One run per scenario, model `claude-sonnet-4-6`, exactly as
the app runs a question (question + date context). Full records, including every
tool call, tool result and token count: `20261115-105606/S30.json` and
`20261115-105930/*.json`. The first round (2026-11-02) is in `20261102-120453/`,
with the verbatim answers and the reviewer's evaluation in its `REPORT.md`.

**Cost:** $0.381 (S30) + $0.686 (other five) = **$1.07** for this round; $2.11
across both rounds. No retries.

## What was fixed between the rounds

| S30 finding (2026-11-02) | Root cause | Fix |
|---|---|---|
| A07 (trend-only problem) missed | Broad-review evidence held only period averages; A07's average is normal | `get_agent_comparison` adds `trend_signals` per agent; prompt: cover agents with trend signals |
| A04 category rates given for the wrong period | No tool returned category figures per half | Signal tool adds `by_classification` for each half |
| "45 login_issue requests" (actually 40) | Unusual hours reported only their total | Anomalies add `requests_by_classification`; new `category_count` answer check |
| 26 Aug incident not investigated | Nothing showed what a mixed-category hour was about | Anomalies add `top_subjects`; prompt: describe every unusual hour |

## Results

| Scenario | Grader | Factual accuracy | Reasoning | Completeness | Tool use |
|---|---|---|---|---|---|
| S30 10-day review | PASS | 363 numbers, all in tool results; A04 later-half category rates now correct | Demand vs staffing separated per incident; hypotheses hedged | **All 6 planted issues** (was 5): 3 incidents incl. 26 Aug mobile-app subjects, A04, **A07**, A09 | 11 calls, 6 pre-fetched; signals checked for A04 and A07 |
| S29 unequal periods | PASS | 99 numbers, all direct; 199.83 vs 200.0 per day | Correct: no drop | Complete | 5 calls; `compare_values` now used correctly |
| S16 A04 trend | PASS | 154 numbers, none unsupported | One-day 88.89% kept to its day; uses only the non-low-sample category (payment 60.0% vs peers 22.67%) | Complete | 7 calls |
| S03 staffing incident | FAIL (one check) | 127 numbers, none unsupported | Staffing drop + demand surge identified | Complete | One call with an empty window (15:00→15:00), immediately corrected; the grader counts it as an invalid argument |
| S05 long waits | PASS | 90 numbers, all direct | Demand + staffing; now asks to check before calling 15:00–16:00 a recurring problem | Complete | 3 calls, all pre-fetched |
| S07 busiest hour | PASS | 87 numbers, none unsupported | Correct on all three parts | Complete | 5 calls |

## Remaining issues (not release-blocking)

- **S30 narrative:** the prose still says "45 login_issue requests" before "Of those 45, 40 were login_issue". The structured result is correct, and the new answer check flags this sentence in the Technical view.
- **S03 interpretation:** "four agents left the shift at 15:00" reads more than the data shows (8 agents on shift for that hour, 12 again at 16:00); a "platform-side event" hypothesis is weakly supported. Both hedged as hypotheses.
- **S03 tool use:** one empty-window call; tools accept empty windows silently instead of returning an error.
- **One run per scenario:** these runs show the agent *can* answer these questions correctly with the current design, not that it always will. Consistency needs repeated runs.

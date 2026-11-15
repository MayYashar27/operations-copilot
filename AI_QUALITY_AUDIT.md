# AI Quality Audit — Phase 0

**Scope:** the 8 saved Copilot runs, the saved Agent Performance Monitoring
report (2026-09-07), and the deterministic monitoring rules.
**Method:** offline only. No API calls were made: the network was blocked
for every evaluation process. All checks are reproducible with
`python -m evals.run_phase0` and `python -m pytest evals/tests`.
**Model under audit:** `claude-sonnet-4-6`, as recorded in the runs.
**Status:** the findings below describe the saved runs as they were. A remediation followed;
its status is in the next section.

---

## 0. Remediation status (2026-10-26)

| Finding | What changed | Status |
|---|---|---|
| H1 multi-day abandoned calls | `get_monitor_metrics` now counts `start <= t < end`, matching the generator (each snapshot covers the 5 minutes starting at its timestamp), sums counters per day, and uses working hours (08:00–17:00) unless after-hours data is requested. 10 days = 628 (634 with the after-hours 17:00 snapshots) | **Fixed and tested** against the raw data |
| M2 merged multi-day buckets | Multi-day bucket labels include the date | **Fixed and tested** |
| H2 unequal periods | Tools report working days; `compare_values` compares per day; new `get_daily_series`; prompt rule; pre-fetch for multi-day questions; answer check for totals over unequal periods | **Correct in live runs** (S29, 2 of 2) |
| H3 one day generalised to a period | `low_sample` flags and `period_label`; per-category figures per period; prompt and final-answer rules; answer check for period-wide wording | **Correct in live runs** (S16, 2 of 2; S30 period attribution fixed on 2026-11-15) |
| M1 staffing missed | `agents_on_shift` exposed; new `get_capacity_context`; prompt requires demand and staffing; pre-fetch for spike and staffing questions | **Correct in live runs** (S03 and S05, 2 of 2 each) |
| M2/M3 broad reviews | New `detect_volume_anomalies` (with per-hour categories and subjects); `trend_signals` per agent; multi-day strategy in the prompt; pre-fetch of series, anomalies, all-agent comparison and capacity per unusual hour | **6 of 6 planted issues in the 2026-11-15 live run** (5 of 6 on 2026-11-02, 1 of 6 before the remediation) |
| M5, low findings | Prompt rule against the model's own arithmetic; answer checks for untraceable numbers and category counts | Improved; one narrative slip remained in S30 and was flagged by the answer check |

Live validation: one run per scenario on 2026-11-02 and on 2026-11-15
([evals/results/live/VALIDATION_2026-11-15.md](evals/results/live/VALIDATION_2026-11-15.md)).
Consistency across repeated runs has not been measured.
| H4 invented ID | Fixed earlier | Fixed |

Saved runs R1, R2 and R8 contain monitor figures produced by the pre-fix tool. They are kept
unchanged and marked STALE by `python -m evals.run_phase0`; they need new live runs.

**Changes to figures in this report:** under the corrected rule, the R8 week windows are 416 and
217 abandoned calls (this report first said 417 and 217, using a different boundary
convention); the 10-day total is 628 in working hours.

---

## 1. Summary

**Reliable today**
- **Tools do what their code says.** All 79 saved tool results that could be
  compared match an independent recomputation of the same contract from the
  raw data. The 2 truncated results were rebuilt. This proves faithful traces
  and correct implementations, not that every contract is meaningful: two
  contracts were not (see H1 and M2).
- **No invented identifiers or numbers in completed runs.** Of the 1,008
  numbers in the answers, 919 appear directly in tool results and 69 are
  one-step calculations from numbers stated beside them. None is
  unsupported; 20 occurrences (11 distinct values) could not be verified
  automatically and are listed for manual review. No agent or request ID was
  invented, and every cited request was actually retrieved.
- **Root-cause discipline holds.** `confirmed_root_cause` is empty in every
  run, and no observed fact contains causal wording.
- **Focused questions work well.** When asked directly about an incident or
  an agent, the Copilot found 4 of the 5 planted causes. Examples: login
  failures after an update; A07's faster handling and degrading notes; A09
  as a case-mix effect rather than poor performance.
- **The monitoring rules are exact.** 56 boundary and scenario tests pass,
  the saved report reproduces exactly, and an AI observation alone can never
  escalate an agent.

**Not yet reliable**
- **Open-ended reviews.** The 10-day review question surfaced only 1 of the 6
  planted issues and led with a warning sign that does not exist (a "33%
  volume drop" caused by comparing 6 working days with 4).
- **Multi-day monitor figures are silently wrong.** For multi-day windows,
  the monitor tool returns a counter difference that looks like a total.
  The agent reported 53 abandoned calls for 10 days; the true figure is 628 in working hours
  (634 including the after-closing 17:00 snapshots).
- **Generalisation beyond the evidence.** Examples: "A04 transfers payment
  and login at or near 100% across the period" (true for 9 requests on one
  day, 35–41% before), and "Technical Support dominant across all four
  categories" (contradicted by the answer's own facts).
- **Numbers the model computes itself**, mainly in the narrative. Examples:
  a 10-minute table summing to 55 for a 45-request hour, an invented "~18%"
  team share, and a destination split that covers only 7 of 10 transfers.

**Overall:** the Copilot is trustworthy on focused questions, with every
number checkable against its source. It is not yet trustworthy for broad
"what should I worry about" reviews, or for any question over several days
that involves monitor data. Most issues have a clear, testable fix (section 7).

---

## 2. Scorecard

| Area | Result | Verdict |
|---|---|---|
| Replay fidelity (saved results vs the tool contract in force when they were saved) | 79/79 match, 2 rebuilt | PASS |
| Tool semantics (does the contract give the number a manager means?) | 2 issues: multi-day monitor totals, merged multi-day buckets | **FAIL** at audit time; fixed since (§0) |
| Tool arguments | 0 invalid; 7 warnings (3 calls the tool cannot answer, 4 multi-day windows with misleading semantics) | PASS with warnings |
| Tool selection (required tools per question) | 32/32 checks on 7 runs; 1 run not evaluable (trace lost) | PASS |
| Numbers in answers | 919 direct, 69 derived, 20 not auto-verified (to review), 0 unsupported | PASS (surface level) |
| Identifiers | 0 invented or unseen IDs in completed runs; 1 historic invented ID (fixed) | PASS |
| Root cause and causal wording | 0 confirmed causes; 0 causal facts | PASS |
| Targeted claim checks (36) | 16 PASS, 19 FAIL, 1 REVIEW | **FAIL** |
| Planted scenarios, direct questions | 4 of 5 found | Mostly PASS |
| Planted scenarios, open-ended 10-day review | 1 of 6 found | **FAIL** |
| Monitoring rules (56 tests) | All pass; report reproduces exactly | PASS |
| Monitoring AI review | Valid citations; flags all 15 agents (see §5) | REVIEW |

Failures by severity: **5 high** (1 historic and fixed), **9 medium**,
**5 low**. **No critical failures.**

---

## 3. The runs audited

| Run | Question | Tool calls | Targeted checks |
|---|---|---|---|
| R1 | Spike 2026-08-25 12:00 | 13 | 4 pass, 2 fail |
| R2 | Spike 2026-08-27 15:00 | 12 | 1 pass, 2 fail |
| R3 | Transfers on 2026-09-07 | 7 | 1 pass, 1 fail |
| R4 | Which classifications drove "today" | 7 | 1 pass, 2 fail |
| R5 | Highest transfer rates (before the fix) | 0 (failed) | 1 fail (historic) |
| R6 | Highest transfer rates (after the fix) | 11 | 4 pass, 4 fail |
| R7 | A07 performance change | 5 | 4 pass, 1 review |
| R8 | 10-day trends and warning signs | 26 | 1 pass, 7 fail |

R1–R3 are committed examples. R4–R8 are local live runs, which are
git-ignored; their content is synthetic data only.

---

## 4. Confirmed failures

Each finding cites its check ID in `evals/results/phase0_results.json`.
"Cause" says where the fix belongs: the **model's reasoning**, a **tool's
contract**, or the **trace**.

### High

**H1. Multi-day abandoned-call figures are wrong (R8-2, R8-3).**
"Total abandoned calls across the full period: 53"; "Week 1: 63, Week 2: 52".
- **Truth (corrected rule, §0):** 628 total in working hours; 416 and 217 by week.
- **What went wrong:** monitor counters reset every day, and
  `get_monitor_metrics` returns last-minus-first across days, which is
  simply the last day's count.
- **Cause:** tool contract. The tool returns a plausible number for a
  window it cannot answer, with no warning. The agent had no way to know.
  Pinned at audit time by an xfail test; fixed since, and now covered by
  `tests/test_day_level_tools.py` and `evals/tests/test_tools_vs_oracle.py`.

**H2. A spurious "33% volume drop" is the first warning sign (R8-1).**
- **Truth:** "Week 1" has 6 working days and "Week 2" has 4. Per working
  day the volume is 199.8 vs 200.0, so there is no drop.
- **Consequence:** the answer recommends checking for a routing failure.
- **Cause:** model reasoning (no normalisation of unequal periods), helped
  by the lack of a per-day tool.

**H3. False claim about an individual across a period (R6-2).**
"A04 consistently transfers payment_issue and login_issue requests at or
near 100% across the analysis period."
- **Truth:** near 100% only on 2026-09-07 (8 of 9 requests). Over
  2026-08-25..09-04, A04's rate was 41.2% for payment and 35.3% for login,
  from a result the agent had retrieved itself.
- **Why it matters:** A04 really is an outlier, but this sentence feeds a
  recommendation for a supervisory review.
- **Cause:** model reasoning (one day generalised to a period).

**H4. Invented agent ID aborted a run (R5-1). Historic, fixed.**
The agent guessed `A001` and the run failed with no trace. Since then the
code has gained:
- `get_agent_comparison`;
- ID validation;
- recoverable tool errors;
- partial traces.

The same question now completes (R6) and is covered by a regression test.

### Medium

**M1. The planted staffing shortage was missed (R2-1, R2-2).**
- **Truth:** agents on shift fell from 12 to 8 at 15:00 on 2026-08-27, and
  available agents averaged 0.77, against 4.5–5.6 at the same hour on other
  days.
- **What the agent did:** it hypothesised a payment-system event, and listed
  "baseline abandoned calls" and "baseline wait time" as missing evidence.
  Both were available from tools it never called for the baseline hour.
- **Causes:**
  - Tool gap: `agents_on_shift` is in the data but no tool returns it.
  - Model reasoning: it did not fetch a baseline for capacity metrics.

**M2. Aggregation hides the incidents in the 10-day review (R8-5, R8-7).**
- **What the answer says:**
  - none of the three incident hours appears;
  - "14:00–15:00 is consistently the highest-volume hour", which is true on
    only 2 of 10 days;
  - the 10-day total is inflated by the 2026-08-26 incident.
- **Consequence:** a staffing recommendation rests on that claim.
- **Causes:**
  - Tool contract: hourly buckets over several days merge by HH:MM label.
    Pinned by an xfail test at audit time; fixed since (labels carry the date).
  - Model reasoning.

**M3. A second outlier is silently dropped (R8-4).**
"The 13 remaining agents range from 18.90% to 27.41%". There are 14, and
A09, at 33.77%, falls outside the band and is omitted. A07 is also never
mentioned. Of the planted agents, only A04 is surfaced.

**M4. Generalisation contradicts the answer's own facts (R3-2, R4-2; seen
in 2 runs).** "Technical Support was the dominant transfer destination
across all four classifications." The same answer states that General
Information's top destination was Billing (4 vs 3).

**M5. Wrong numbers that the model computed itself.**
- **R1-1:** a 10-minute table built by adding 5-minute buckets has three
  wrong rows (17, 10, 17 instead of 9, 12, 13) and sums to 55 for a
  45-request hour.
- **R6-4:** "A09's transfers were routed to technical_support (3),
  back_office (3), billing (1)". That covers only the 7 technical-issue
  transfers; A09 made 10 (4 / 4 / 2).

### Low

- **R1-4:** "escalation rate (57.5%) for update-related login issues". 57.5%
  is 23/40 for all login issues; for update-related issues it is 23/36 =
  63.9%.
- **R4-3:** the narrative labels Payment Issue (33%) as the "Highest"
  transfer rate. Login Issue (36%) is highest.
- **R6-5:** "~18% team average" technical share. The true share is 25.5%,
  and no tool returned 18.
- **R6-7:** three calls to the signal tool with one-day windows, which can
  only return insufficient data. The agent recovered.
- **R8-6:** hourly values labelled "Avg. Requests" are 10-day totals.

Most low-severity and two medium findings sit in the **narrative** (the
Technical view), not the structured result the Manager view is built from.
Fewer managers read it, but it is still shown to them.

---

## 5. Agent Performance Monitoring

**Deterministic rules: PASS** (`evals/tests/test_monitoring_rules.py`, 56 tests)
- **Planted agents:**
  - A04 (rising transfers, concentrated in technical support) is escalated.
  - A07 (faster handling with more transfers, short notes) is escalated.
  - **A09 (case mix) is flagged as a finding and correctly not escalated.**
    The rules cannot see case mix, and they do not overreact.
- **Thresholds:** every one is tested just at and just below its boundary.
  This covers the 15-point peer and trend rules, ±20% handling time, the
  20-request minimums, short notes (5 requests, 3 short, 40%, under six
  words), 2 missing notes, and 75% of 4 transfers.
- **Escalation:** all four escalation combinations, plus the cases that must
  stay as findings.
- **Insufficient data:** both paths behave as the README now documents.
  Fewer than four working days skips only the trend rules; no requests that
  day sets the status.
- **Reproducibility:** the committed report's rule-based findings and
  escalations reproduce exactly from the current code.
- **AI cannot escalate:** a fake AI review that demands escalation still
  yields `findings`.

**AI documentation review: REVIEW (labels needed)**
- **Citations:** all 48 findings cite request IDs that exist and belong to
  the right agent and date. The two deep investigations (A04, A07) cite
  only their own agent's requests.
- **Coverage:** it flags **all 15 agents**. Without it, 11 of the 13
  "findings" agents would simply be "screened".
- **Context:**
  - 33 of the 48 findings cite only transferred requests.
  - In the synthetic data, 502 of 517 transfer notes end with a fixed
    template.
  - By a simple category-to-team mapping (an assumption, not a rule from the
    data), 308 of 517 transfers go to a team that is unusual for the
    category.
- **What remains open:** the review is very likely reporting real properties
  of the generated data, not inventing them. Whether a manager would want
  them flagged cannot be decided without labels. A sample of hand-labelled
  notes is the open item.

---

## 6. What could not be evaluated from the saved runs

| Gap | Why | What would close it |
|---|---|---|
| Consistency | Each question was run once | 3 repetitions per scenario (paid) |
| Reasoning between tool calls | Traces store calls and results, not the model's intermediate messages | Store the message sequence in the record |
| Cost per question | Token usage is not recorded | Store `usage` per model call |
| Date context of the 3 committed examples | They predate the `prompt_context` field | Regenerate, or accept |
| Tool selection in the failed run | Pre-fix failures saved no trace (fixed since) | — |
| AI documentation review precision | No labelled ground truth for "good" notes | Hand-label a sample |
| Robustness | No saved run with a false premise, missing data or invalid ID | Scenarios S06, S12, S23–S29 (paid) |

---

## 7. Recommended improvements (as written at audit time)

Ordered by impact on the failures above. Items 1–6 were implemented on 2026-10-26 (see §0;
item 6 as `answer_checks.py`). Item 7 is partly open (token usage and model messages are still
not stored), and item 8 is open.

1. **Make multi-day monitor windows safe (H1).**
   - `get_monitor_metrics` should either sum per-day changes or refuse
     windows that span days with a clear error.
   - The pinned xfail test then passes.
2. **Add a per-day tool (H2, M2).** A daily series of volume, wait,
   abandoned and available agents, for example by exposing the existing
   `get_daily_metrics` and `detect_hourly_volume_anomalies` as tools. This
   lets the agent normalise periods and discover incidents.
3. **Expose `agents_on_shift`** in the monitor tool (M1).
4. **Make multi-day hourly buckets unambiguous** (M2): add the date to
   labels, or return per-day averages.
5. **Prompt rules** for the observed failure modes:
   - compare unequal periods per working day;
   - claims with "all", "consistently" or "across the period" need evidence
     for that whole scope;
   - list every outlier, not only the largest;
   - take sums and splits from tools, not from mental arithmetic.
6. **A deterministic answer check before saving.** Run `evals/claims.py` on
   each answer and show unverified numbers in the Technical view. It needs
   no AI and costs nothing per run.
7. **Richer traces:** model messages, token usage, and the date-context line
   for every run.
8. **Monitoring AI review:**
   - hand-label 30–50 notes to measure precision;
   - consider not raising findings that only restate the note template.

---

## 8. Proposed next step: small paid pilot (not approved, not run)

Six scenarios from `evals/scenarios/scenarios.json`, one run each, chosen to
re-test the weaknesses above:

| Scenario | Tests |
|---|---|
| S03 | Staffing incident |
| S12 | Multi-day abandoned-call trap |
| S16 | A04 overgeneralisation |
| S20 | A001 regression |
| S29 | Unequal periods |
| S30 | Open-ended 10-day review |

- **Estimated cost:** about $0.25 per typical question and up to about
  $0.50 for S30, so **about $2–3 for the pilot**.
- **Model:** `claude-sonnet-4-6`, at $3 / $15 per million input / output
  tokens.
- **Basis:** the size of the system prompt and tool definitions (about
  3,200 tokens per call) and the size of the saved traces. The pilot itself
  would measure the real cost.
- **Not included:** an optional AI-grader calibration pass over the 31
  judgement items. The request builder estimates about $1 with Opus 5.5, or
  about $0.50 via the Batch API.

No budget is assumed. The pilot runs only on explicit approval.

---

## 9. Reproduce

```bash
python -m evals.run_phase0          # writes evals/results/phase0_results.json and manual_review.md
python -m pytest evals/tests -q     # 135 passed (at audit time: 130 passed, 2 xfailed)
python -m pytest -q                 # the project's tests: 140 (56 at audit time)
```

Items for human review, 12 in total, are listed in
`evals/results/manual_review.md`:
- one REVIEW check: whether "trended progressively upward" fits a volatile
  series;
- 11 distinct numbers (20 occurrences) that could not be verified
  automatically. Examples are "+167%" and "1,006"; the latter is the model's
  own sum of two category counts.

# Evaluation framework

Checks whether the Copilot's answers are **right**, not just whether the
software runs. Phase 0 works entirely offline on saved runs and the saved
monitoring report. The findings are in [`../AI_QUALITY_AUDIT.md`](../AI_QUALITY_AUDIT.md).

Nothing here changes the application. The code only reads `data/`,
`reports/` and `investigations/`, and imports `tools.py` and
`langgraph_agent.py` only in tests, to compare against or call their rules.

## Offline by construction

`safety.py` blocks every outbound network connection for the whole process
and replaces any API key with a placeholder before the agent module is
imported. An accidental model call cannot connect, and could not
authenticate if it did. No step in Phase 0 calls the model.

## Run it

```bash
python -m evals.run_phase0                    # audit saved runs -> evals/results/
python -m pytest evals/tests -q               # 130 tests + 2 pinned known issues
python -m evals.ai_grader.build_requests      # optional: build (not send) AI-grader requests
```

The project's own suite (`python -m pytest`) is unchanged and does not
collect these tests.

Local runs in `investigations/local/` are git-ignored, so a fresh clone
audits only the 3 committed examples; tests that need a local run skip.

## Layout

| File | Purpose |
|---|---|
| `oracle.py` | Independent re-implementation of all 16 tools from the raw JSON, plus "truth" helpers (per-day abandoned calls, working days, agents on shift) |
| `trace_checks.py` | Argument validation, replay of each saved tool call against the oracle, trace completeness |
| `claims.py` | Number matching (direct / derived / loose / unsupported), identifier checks, causal wording |
| `saved_runs.py` | The auditor's targeted checks for each of the 8 saved runs, as code |
| `run_phase0.py` | Runs everything; writes `results/phase0_results.json` and `results/manual_review.md` |
| `scenarios/scenarios.json` | 30 proposed questions for the paid phases, with oracle-defined expected facts |
| `grade_scenario.py` | Objective grader for one run against one scenario |
| `GRADING_CRITERIA.md` | Verdicts, severity levels, pass bars |
| `ai_grader/` | Design of an AI grader for judgement calls (prompt, schema, dry-run request builder) |
| `tests/` | Monitoring rules and boundaries, tools vs oracle, the graders themselves, scenario validity |

## Why an independent oracle

If the evaluation called `tools.py` to get the right answer, a bug in a
tool would make the agent and the grader wrong in the same way. The oracle
is written separately from the raw data, and `tests/test_tools_vs_oracle.py`
shows the two agree everywhere except the two pinned known issues.

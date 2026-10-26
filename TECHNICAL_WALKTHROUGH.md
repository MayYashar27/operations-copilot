# Technical walkthrough

A guide to explaining Operations Copilot in technical interviews. Everything here
describes the code as it is in this repository; file and function names are real.

---

## 1. The 30-second version

> Operations Copilot helps a service-center manager understand a shift, spot which
> representatives need attention, and investigate "why" questions. A **LangGraph** agent
> uses **Claude** to decide which of **16 deterministic Python tools** to call. The tools
> compute every number; the model chooses what to look at, reads request notes, and files
> a **structured result** that separates observed facts, patterns, hypotheses and missing
> evidence. A **FastAPI** backend serves precomputed AI results to a **React** app, and only
> runs new, paid AI investigations in a local live mode.

## 2. The architecture in plain language

Think of four layers, each only talking to the one below it:

1. **Data** (`data/*.json`): synthetic requests, monitor snapshots and shift schedules,
   produced by a seeded generator.
2. **Deterministic tools** (`tools.py`): plain Python functions that count, group, average
   and compare. Same input, same output, unit-testable, no AI.
3. **AI orchestration** (`langgraph_agent.py`): LangGraph graphs in which Claude decides
   which tools to call and interprets the results; Pydantic schemas force structured output.
4. **Application** (`api/` + `web/`): FastAPI serves saved results and starts new runs
   safely; React displays them. The concise Manager views are built by TypeScript code,
   not by another AI call.

The key idea is **precompute, then serve**: expensive and non-deterministic AI work runs
ahead of time (scripts) or on explicit request (live mode). Page loads never call the model.

## 3. What each important module does

| Module | Purpose |
|---|---|
| `tools.py` | All calculations. Time-window tools (`count_requests`, `get_requests_by_classification`, `get_monitor_metrics`…), per-agent KPIs (`get_agent_performance`, `get_agent_daily_trends`), rule-based signals (`detect_agent_performance_signals`), documentation screening, `get_agent_comparison`, and `validate_agent_id`. |
| `langgraph_agent.py` | The `@tool` wrappers Claude sees; `SYSTEM_PROMPT`; Pydantic schemas (`InvestigationResult`, `PatternAnalysisResult`, `AgentInvestigationResult`, `DocumentationAnalysisResult`); the question graph (`graph`); the agent investigation graph (`agent_investigation_graph`); screening (`evaluate_agent_investigation_triggers`); the batch report (`run_daily_agent_performance_report`); the daily brief (`run_daily_summary`); a CLI (`main`). |
| `api/main.py` | FastAPI app factory (`create_app`) and read-only endpoints. |
| `api/service.py`, `api/shift.py` | Build API responses from the saved report plus fresh deterministic numbers; split screening findings into rule signals and AI observations. |
| `api/storage.py` | The only code that reads report files; validates their shape with Pydantic. |
| `api/copilot_routes.py` | Ask Copilot endpoints and the live-mode safety gates. |
| `api/copilot_runner.py` | Runs the LangGraph workflows in a background thread, one at a time; captures the tool trace; persists every outcome. |
| `api/copilot_store.py` | `InvestigationStore` interface with a JSON-file implementation (examples committed, local runs git-ignored). |
| `web/src/features/*/managerSummary.ts`, `copilotSummary.ts` | Deterministic builders that turn a saved AI result into the one-minute Manager view. |
| `scripts/generate_report.py`, `scripts/generate_examples.py` | Paid batch jobs that produce the saved AI artifacts. |

## 4. How the tools are defined and invoked

1. **Definition.** Each tool is a Python function in `tools.py`. A thin wrapper in
   `langgraph_agent.py` decorates it with LangChain's `@tool`. LangChain turns the function
   signature into a JSON schema and the docstring into the description Claude reads.
2. **Binding.** `model.bind_tools(TOOLS)` attaches all 16 schemas to every Claude call made by
   the `claude` node.
3. **Selection.** Claude returns an `AIMessage` with `tool_calls` (name, arguments, id), often
   several at once. The choice is the model's, guided by the question, the tool descriptions
   and the system prompt ("use the minimum number of tools", "never guess identifiers").
4. **Execution.** `execute_tools` looks each call up in `TOOL_MAP`, runs it, and appends a
   `ToolMessage` with the JSON result. If a call raises (for example an unknown agent ID),
   it returns `{"error": ...}` with `status="error"` instead of failing the graph.
5. **Loop.** The graph routes back to `claude` with the results. This continues until Claude
   answers without calling tools, or until the recursion limit (40) is reached.

## 5. Deterministic code vs LLM reasoning

| Deterministic | LLM |
|---|---|
| Every metric, rate, comparison and trend | Which tools to call and in what order |
| Signal thresholds and escalation rules | Reading notes; finding recurring themes |
| ID and evidence validation | Interpreting evidence; proposing hypotheses |
| Access control, persistence and run tracking | Filling the structured output schema |
| Manager-view summaries in the UI | Writing proportionate recommendations |

The rule of thumb: **anything that must be correct and reproducible is code; anything that
requires judgement over unstructured text is the model**, and the model's output is constrained
by a schema and validated where possible.

## 6. One request, end to end

Question: *"There was an unusually high workload on 2026-08-25 between 12:00 and 13:00.
Investigate what happened and explain the likely cause."* (saved as an example).

1. **UI.** The manager submits in Ask Copilot. `CopilotPage.tsx` posts to
   `POST /api/copilot/investigations` and navigates to the new record.
2. **Gate.** `copilot_routes.require_live_local` checks live mode, API key, loopback client
   and absence of proxy headers. The runner refuses if another run is active (409).
3. **Record.** `InvestigationRunner.start_question` saves a `running` record (with the exact
   date-context line it will append) and starts a background thread.
4. **Graph.** `langgraph_question_runner` streams `graph` with the question:
   - `claude` → Claude calls `count_requests` for the spike hour and the previous hour,
     `get_requests_by_classification`, `get_requests_by_time_bucket`, `get_monitor_metrics`.
   - `tools` → deterministic results (45 vs 19 requests; 40 of 45 are login issues).
   - Claude compares the baseline hour's classifications and both hours' average wait times
     (`get_requests_by_classification`, `get_average_wait_time`).
   - Claude asks for `get_request_details` → `tools` stores the request set →
     `route_after_tools` sees a new set and routes to `pattern_analysis`.
   - `pattern_analysis` → a structured call finds a theme: 36 of 40 notes mention login
     failures after an application update (high confidence), with request IDs.
   - `claude` (now with the themes appended to its system prompt) calls `compare_values` and
     `get_classification_status_breakdown`, then answers without tool calls.
   - `final_investigation` → one structured call files the `InvestigationResult`, with
     `confirmed_root_cause = null` because there is no deployment evidence.
5. **Persist.** The runner extracts the tool trace (13 calls), pattern themes, final prose and
   dates examined, and saves the record as `completed`.
6. **Display.** The UI's polling sees `completed`. `copilotSummary.ts` builds the Manager view:
   because one category holds at least half of the captured breakdown, it leads with
   *"The volume was concentrated in login issue requests: 40 of 45 (89%)"*, followed by the facts.
   Hypotheses and missing evidence stay in Technical details.
7. **Reopen.** Opening the record later reads the JSON file. Claude is not called again.

## 7. Design decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| A custom LangGraph graph instead of a prebuilt ReAct agent | Explicit nodes for pattern analysis and a final structured answer; easy to inspect and test | More code to own than `create_react_agent` / `ToolNode` |
| Separate `final_investigation` node with `with_structured_output` | Guarantees a typed, validated result regardless of how the conversation went | One extra model call per run |
| Deterministic tools, LLM for orchestration | Numbers are reproducible and testable; the model cannot "do arithmetic" | Every new kind of question may need a new tool (see the comparison tool below) |
| Precompute + demo mode | Free, fast, safe public demo; no key needed | Demo content is static |
| Deterministic Manager views instead of an AI summary | Cannot overstate the saved evidence; no extra cost; auditable rules | Less fluent than LLM prose; heuristics (e.g. question type) need tuning |
| Errors returned to the model | One bad call no longer kills a run; the model can self-correct | Possible retry loops, bounded by the recursion limit |
| Background thread + polling, one run at a time | Simple and enough for a single local user | No queue, no streaming, no horizontal scaling |
| JSON files behind an interface | Zero infrastructure; history survives restarts | Not suitable for concurrent users; swap for a database later |
| Date context appended to the question | The system prompt has no notion of "today"; stored for audit | The model's input differs slightly from what the user typed |

### How the project evolved

- **v1:** a hand-rolled tool-use loop with the Anthropic SDK (removed; in git history).
- **v2:** LangGraph with structured outputs, pattern analysis, agent screening and a Streamlit prototype (`app.py`).
- **v3:** FastAPI + React, saved results, demo/live modes, investigation history, Manager/Technical views.
- **A real bug from live testing:** a question comparing all agents failed because no tool listed
  agents; Claude guessed `A001`, the tool raised, and the uncaught error aborted the graph. The fix
  added `get_agent_comparison`, ID validation with a helpful message, recoverable tool errors, and
  partial traces on failure, plus regression tests with a scripted fake model. The same question
  then completed in a live run using the new tool.

## 8. Scalability and reliability improvements

- **Evaluation:** turn `data/demo_ground_truth.json` into an automatic eval that scores whether the
  agent's facts and hypotheses match the planted scenarios (example 2 shows a miss worth measuring).
- **Storage and jobs:** a database (PostgreSQL) behind `InvestigationStore`; a job queue with workers
  instead of one in-process thread; idempotent run IDs.
- **Multi-user:** authentication, per-user history, rate limits and a cost budget per user before
  any public live deployment.
- **Observability:** structured logging and tracing per node (tokens, latency, tool errors), and
  streaming of agent steps to the UI.
- **Cost and latency:** prompt caching for the long system prompt and tool schemas; cap tool result
  sizes sent to the model; cache deterministic tool results per day.
- **Robustness:** tool-level input validation for every argument (dates, classifications), not just
  agent IDs; timeouts per tool; a fallback answer when the recursion limit is reached.

## 9. Ten interview questions about this project

**1. Why use an agent at all instead of a fixed analytics pipeline?**
The "what happened" part is a fixed pipeline: the Overview and the screening rules are plain code.
The agent is for open questions where the next step depends on what the data showed. In example 1
it only fetched request notes after seeing that one category dominated. A fixed pipeline would
either fetch everything or miss that path.

**2. How do you stop the model from inventing numbers?**
The model never computes numbers; the tools do. The system prompt requires facts to come from tool
results. The final answer must fit `InvestigationResult`, which separates `observed_facts` from
`hypotheses`, and `confirmed_root_cause` must be null without direct evidence. For agent
investigations and documentation review, code rejects any result citing request IDs that are not in
the evidence. Saved traces let a reviewer check each fact against its tool call.

**3. How does the agent decide which tools to call?**
Claude receives all 16 tool schemas via `bind_tools`, plus the system prompt with an investigation
strategy (check whether a spike is concentrated in one category first; read request details only
when needed). It returns `tool_calls`; the graph executes them and loops. The routing after `tools`
is deterministic: new request details trigger the `pattern_analysis` node before control returns to Claude.

**4. Walk me through a failure you found and fixed.**
A live question asked which agents had the highest transfer rates. No tool listed agents, so Claude
guessed `A001`–`A010`; `get_agent_performance` raised, and `execute_tools` did not catch it, so the
whole graph aborted, and my runner lost the trace. I found the tool calls in the console log, then
fixed it with a comparison tool, ID validation that lists valid IDs, error results returned to the
model, and partial-trace capture. Regression tests replay the exact failure with a scripted model;
the real question then succeeded in a live run.

**5. How do you test an LLM agent without paying for API calls?**
The tools are pure functions with normal unit tests. The API is tested with FastAPI's `TestClient`
and injected fakes (`create_app(settings, store, runner)`). For the LangGraph graph I monkeypatch the
bound model with a scripted object that returns predetermined `AIMessage`s, so I can reproduce exact
tool-call sequences, including bad ones, and assert what the model was shown on the next turn.
56 tests run offline.

**6. Why is the Manager view built by TypeScript rather than by asking Claude to summarise?**
Cost and trust. Summarising with another model call could overstate or drop caveats, and it would
cost money on every page view. The deterministic builders only select, group and shorten saved
fields, and the Technical view documents exactly how. When the data does not support a summary line,
it is not shown.

**7. What are the security boundaries?**
The key lives only in the server's environment. Read endpoints never call the model. The only paid
endpoints require `APP_MODE=live`, a key, a loopback client and no proxy headers; servers bind to
`127.0.0.1`; one run at a time. Request notes are untrusted data and the prompts say so. For a public
deployment I would add authentication, per-user history and budgets first.

**8. How is representative performance monitored without turning it into a punitive score?**
Deterministic KPIs and rule-based signals compare each representative with their own earlier period
and with peers. An AI review of notes adds observations, but escalation to a deep investigation is
decided only by combinations of rule signals, never by the model alone. Statuses are review
categories, the UI separates rule signals from AI observations, and the wording avoids presenting
suspected routing problems as errors.

**9. What would you change to run this for a real 100-person center?**
Replace JSON with a database and the in-process thread with a job queue; ingest data from the real
ticketing and telephony systems instead of the generator; add authentication and role-based access;
build an evaluation set from real, reviewed incidents to tune thresholds and prompts; add tracing
and cost monitoring; and validate the screening thresholds with the operations team.

**10. What is the weakest part of the system today, and how would you measure it?**
Hypothesis quality. In example 2 the agent saw near-zero agent availability but hypothesised a
payment-system event, while the planted cause was a staffing shortage. I would build an eval from the
generator's ground truth, score whether hypotheses mention the planted cause, and iterate on the
investigation strategy in the prompt (for example, always checking capacity before demand).

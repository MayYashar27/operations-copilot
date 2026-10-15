"""Runs investigations in the background and persists their records.

The AI work itself is done by the EXISTING workflows in langgraph_agent.py:

  * questions -> `graph`, the same compiled graph run_agent(question) uses.
    run_agent() only prints its result, so we invoke the graph directly and
    read the final state (structured result, pattern analysis, tool calls).
  * agents    -> run_agent_performance_investigation(...), unchanged.

langgraph_agent is imported lazily, only when a live run starts, so demo
mode never loads the AI stack or needs an API key.

Safety guards: one investigation at a time, a recursion limit on the graph,
truncated tool results, and every outcome (including failures) persisted.
"""

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from api import storage
from api.copilot_store import InvestigationStore, now_iso
from api.schemas import InvestigationError, InvestigationRecord

logger = logging.getLogger("operations_copilot.runner")

MAX_TOOL_RESULT_CHARS = 16000  # fits a full all-agent comparison (~9k chars)
GRAPH_RECURSION_LIMIT = 40   # caps Claude <-> tools round trips

# A "question runner" takes a question and returns the fields to store.
QuestionRunner = Callable[[str], Dict[str, Any]]
AgentRunner = Callable[[str, str, str, Dict[str, Any]], Dict[str, Any]]
Spawn = Callable[[Callable[[], None]], None]


class InvestigationBusyError(Exception):
    pass


def new_id() -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------
# Default runners: thin adapters over langgraph_agent.py
# ---------------------------------------------------------

def _text_of(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _trace_from_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    """Pair each tool call with its result, in the order they happened."""
    steps: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            steps[call["id"]] = {"tool": call["name"], "args": call.get("args", {})}
            order.append(call["id"])
        call_id = getattr(message, "tool_call_id", None)
        if call_id in steps:
            text = _text_of(message.content)
            if len(text) <= MAX_TOOL_RESULT_CHARS:
                try:
                    steps[call_id]["result"] = json.loads(text)
                except ValueError:
                    steps[call_id]["result_preview"] = text
            else:
                steps[call_id]["result_preview"] = text[:MAX_TOOL_RESULT_CHARS]
                steps[call_id]["result_truncated"] = True
    return [steps[i] for i in order]


def _date_range(trace: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    dates = sorted(
        str(value)[:10]
        for step in trace
        for key, value in step["args"].items()
        if key in {"start_time", "end_time", "start_date", "end_date", "date"} and value
    )
    return {"start": dates[0], "end": dates[-1]} if dates else None


class PartialRunError(Exception):
    """A run that failed part-way. Carries what was captured before the failure."""

    def __init__(self, cause: Exception, partial: Dict[str, Any]):
        super().__init__(str(cause))
        self.cause = cause
        self.partial = partial


def langgraph_question_runner(question: str, graph: Any = None) -> Dict[str, Any]:
    from langchain_core.messages import AIMessage, HumanMessage
    import langgraph_agent

    graph = graph or langgraph_agent.graph
    # Stream the graph (same nodes, same result) so the latest state survives
    # an exception: a failed run still records the tool calls it made.
    state: Dict[str, Any] = {"messages": []}
    try:
        for state in graph.stream(
            {"messages": [HumanMessage(content=question)]},
            config={"recursion_limit": GRAPH_RECURSION_LIMIT},
            stream_mode="values",
        ):
            pass
    except Exception as exc:
        trace = _trace_from_messages(state.get("messages", []))
        raise PartialRunError(exc, {"trace": trace, "date_range": _date_range(trace)}) from exc

    result = state.get("investigation_result")
    patterns = state.get("pattern_analysis")
    final_ai = [m for m in state["messages"] if isinstance(m, AIMessage) and not m.tool_calls]
    trace = _trace_from_messages(state["messages"])
    return {
        "result": result.model_dump() if result is not None else None,
        "pattern_themes": [t.model_dump() for t in patterns.themes] if patterns is not None else [],
        "narrative": _text_of(final_ai[-1].content) if final_ai else None,
        "trace": trace,
        "date_range": _date_range(trace),
        "model": getattr(langgraph_agent.model, "model", None),
    }


def langgraph_agent_runner(agent_id: str, date: str, lookback_start: str, screening: Dict[str, Any]) -> Dict[str, Any]:
    import langgraph_agent

    investigation = langgraph_agent.run_agent_performance_investigation(
        agent_id=agent_id, date=date, lookback_start=lookback_start, screening_result=screening,
    )
    return {
        "result": investigation.model_dump(),
        "date_range": {"start": lookback_start, "end": date},
        "model": getattr(langgraph_agent.model, "model", None),
    }


def date_context(report_date: Optional[str]) -> Optional[str]:
    """Plain date facts the agent needs to resolve "today" or "this shift".

    The existing system prompt has no notion of the current date, so this short
    note is appended to the manager's question. It is stored on the record and
    shown in the Technical view, so the exact input is always auditable.
    """
    from api import shift

    days = shift.working_days()
    if not days:
        return None
    lines = [f"Available data covers working days {days[0]} to {days[-1]}, 08:00-17:00."]
    if report_date:
        lines.insert(0, f"The manager is viewing the shift of {report_date}; treat 'today' or 'this shift' as that date.")
    return "Context: " + " ".join(lines)


def spawn_thread(work: Callable[[], None]) -> None:
    threading.Thread(target=work, daemon=True).start()


# ---------------------------------------------------------
# Runner: one investigation at a time, always persisted
# ---------------------------------------------------------

class InvestigationRunner:
    def __init__(
        self,
        store: InvestigationStore,
        reports_dir: Path,
        run_question: QuestionRunner = langgraph_question_runner,
        run_agent: AgentRunner = langgraph_agent_runner,
        spawn: Spawn = spawn_thread,
        context: Callable[[Optional[str]], Optional[str]] = date_context,
    ):
        self.store = store
        self.reports_dir = reports_dir
        self.run_question = run_question
        self.run_agent = run_agent
        self.spawn = spawn
        self.context = context
        self._lock = threading.Lock()
        self._running_id: Optional[str] = None

    @property
    def running_id(self) -> Optional[str]:
        return self._running_id

    def _claim(self, record: InvestigationRecord) -> None:
        with self._lock:
            if self._running_id is not None:
                raise InvestigationBusyError(self._running_id)
            self._running_id = record.id
        self.store.save(record)  # persisted as "running" before any AI call

    def _finish(self, record: InvestigationRecord, work: Callable[[], Dict[str, Any]]) -> None:
        data = record.model_dump()
        try:
            data.update(work())
            if data.get("result") is None:
                data["status"] = "failed"
                data["error"] = {"type": "NoResult", "message": "The workflow finished without a structured result."}
            else:
                data["status"] = "completed"
        except Exception as exc:  # any failure is recorded, never lost
            logger.exception("Investigation %s failed", record.id)
            cause = exc.cause if isinstance(exc, PartialRunError) else exc
            if isinstance(exc, PartialRunError):
                data.update(exc.partial)  # keep the tool calls made before the failure
            data["status"] = "failed"
            data["error"] = {"type": cause.__class__.__name__, "message": str(cause)[:500]}
        finally:
            data["completed_at"] = now_iso()
            try:
                final = InvestigationRecord.model_validate(data)
            except Exception as exc:
                final = record.model_copy(update={
                    "status": "failed", "completed_at": data["completed_at"],
                    "error": InvestigationError(type="InvalidRecord", message=str(exc)[:500]),
                })
            self.store.save(final)
            with self._lock:
                self._running_id = None

    def start_question(self, question: str, report_date: Optional[str]) -> InvestigationRecord:
        context = self.context(report_date)
        record = InvestigationRecord(
            id=new_id(), kind="question", origin="local", question=question.strip(),
            report_date=report_date, status="running", created_at=now_iso(), prompt_context=context,
        )
        # The original question is stored as typed; the agent receives question + context.
        prompt = f"{record.question}\n\n{context}" if context else record.question
        self._claim(record)
        self.spawn(lambda: self._finish(record, lambda: self.run_question(prompt)))
        return record

    def start_agent(self, agent_id: str, date: str) -> InvestigationRecord:
        screening = storage.load_raw_agent_result(self.reports_dir, date, agent_id)
        lookback_start = screening.get("lookback_start") or date
        record = InvestigationRecord(
            id=new_id(), kind="agent", origin="local", agent_id=agent_id,
            question=f"Deep investigation of agent {agent_id} on {date}",
            report_date=date, status="running", created_at=now_iso(),
        )
        self._claim(record)

        def work() -> Dict[str, Any]:
            outcome = self.run_agent(agent_id, date, lookback_start, screening)
            # Also save where the Agent Detail screen reads investigations.
            storage.save_agent_investigation(self.reports_dir, date, agent_id, outcome["result"])
            return outcome

        self.spawn(lambda: self._finish(record, work))
        return record

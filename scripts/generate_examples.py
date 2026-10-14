"""Generate the pre-recorded Ask Copilot examples shown in demo mode.

These are REAL runs of the existing LangGraph workflow (paid Claude calls),
saved to investigations/examples/ with origin="example". Nothing here is
hand-written: if a run fails, the failure is saved as-is.

Usage (from the project root, with ANTHROPIC_API_KEY in .env):
    python scripts/generate_examples.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.copilot_runner import langgraph_question_runner, new_id  # noqa: E402
from api.copilot_store import JsonInvestigationStore, now_iso  # noqa: E402
from api.schemas import InvestigationRecord  # noqa: E402

REPORT_DATE = "2026-09-07"

# Each question is answerable with the agent's existing tools and refers to
# real patterns in the synthetic data (the three unusual hours, and transfers).
QUESTIONS = [
    "There was an unusually high workload on 2026-08-25 between 12:00 and 13:00. "
    "Investigate what happened and explain the likely cause.",
    "There was an unusually high workload on 2026-08-27 between 15:00 and 16:00. "
    "Investigate what happened and explain the likely cause.",
    "On 2026-09-07, how many requests were transferred, to which destinations, "
    "and which request classifications were most often transferred?",
]


def main() -> None:
    store = JsonInvestigationStore(
        examples_dir=PROJECT_ROOT / "investigations" / "examples",
        local_dir=PROJECT_ROOT / "investigations" / "local",
    )
    for question in QUESTIONS:
        print(f"\n=== {question}")
        data = {
            "id": f"example-{new_id()}", "kind": "question", "origin": "example",
            "question": question, "report_date": REPORT_DATE,
            "status": "running", "created_at": now_iso(),
        }
        try:
            data.update(langgraph_question_runner(question))
            data["status"] = "completed" if data.get("result") else "failed"
        except Exception as exc:
            data["status"] = "failed"
            data["error"] = {"type": exc.__class__.__name__, "message": str(exc)[:500]}
        data["completed_at"] = now_iso()
        record = InvestigationRecord.model_validate(data)
        store.save(record)
        print(f"--> {record.status}: {record.id} ({len(record.trace)} tool calls)")


if __name__ == "__main__":
    main()

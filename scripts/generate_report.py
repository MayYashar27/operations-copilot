"""Generate a saved daily agent report using the existing LangGraph workflow.

This makes PAID Claude API calls (one documentation review per agent, plus a
deep investigation for each agent whose screening status is "investigation").
The web app never runs this; it only reads the saved JSON it produces.

Usage (from the project root):
    python scripts/generate_report.py 2026-09-07
    python scripts/generate_report.py 2026-09-07 --lookback-start 2026-08-25
"""

import argparse
import shutil
import sys
from datetime import date as Date, datetime
from pathlib import Path

# Make the project root importable when running "python scripts/...".
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "reports"


def backup_existing_report(report_date: str) -> Path | None:
    """Copy an existing report aside so the new run never destroys it."""

    existing = REPORTS_DIR / f"agent_performance_{report_date}.json"
    if not existing.exists():
        return None

    backup_dir = REPORTS_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"agent_performance_{report_date}.{stamp}.json"
    shutil.copy2(existing, backup)
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("date", help="Report date, YYYY-MM-DD")
    parser.add_argument("--lookback-start", default="2026-08-25")
    args = parser.parse_args()

    Date.fromisoformat(args.date)
    Date.fromisoformat(args.lookback_start)

    backup = backup_existing_report(args.date)
    if backup:
        print(f"Existing report backed up to: {backup}")

    # Imported here so --help works without loading the AI stack.
    from langgraph_agent import run_daily_agent_performance_report

    report = run_daily_agent_performance_report(
        date=args.date,
        lookback_start=args.lookback_start,
    )

    print("\nSummary:", report["summary"])
    print("Investigations run for:", ", ".join(report["investigations"]) or "none")


if __name__ == "__main__":
    main()

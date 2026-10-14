"""Reads saved reports and investigations from disk.

This is the only module that knows reports are JSON files. Moving to a
database later means rewriting this file, not the rest of the API.

Saved files are validated here, so the rest of the API can trust their shape.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, ValidationError


REPORT_FILE_PATTERN = re.compile(r"^agent_performance_(\d{4}-\d{2}-\d{2})\.json$")


class ReportNotFoundError(Exception):
    pass


class ReportMalformedError(Exception):
    pass


# ---------------------------------------------------------
# Expected shape of a saved report (as written by
# run_daily_agent_performance_report in langgraph_agent.py).
# Unknown extra fields are ignored.
# ---------------------------------------------------------

class SavedAgentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_id: str
    date: str
    lookback_start: Optional[str] = None
    investigation_status: Literal["screened", "findings", "investigation", "insufficient_data"]
    investigation_reasons: List[str] = []
    findings: List[Dict[str, Any]] = []
    documentation_screening: Optional[Dict[str, Any]] = None
    performance_signals: Optional[Dict[str, Any]] = None
    semantic_analysis: Optional[Dict[str, Any]] = None
    methodology: Optional[str] = None


class SavedReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: str
    total_agents: int
    agent_results: List[SavedAgentResult]
    investigations: Dict[str, Dict[str, Any]] = {}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReportMalformedError(f"Could not read {path.name}") from exc


def list_report_dates(reports_dir: Path) -> List[str]:
    """Dates that have a saved report, newest first."""
    if not reports_dir.is_dir():
        return []
    dates = [
        match.group(1)
        for path in reports_dir.iterdir()
        if (match := REPORT_FILE_PATTERN.match(path.name))
    ]
    return sorted(dates, reverse=True)


def load_report(reports_dir: Path, date: str) -> SavedReport:
    # `date` is already validated as YYYY-MM-DD by the route, so it cannot
    # be used to reach files outside reports_dir.
    path = reports_dir / f"agent_performance_{date}.json"
    if not path.is_file():
        raise ReportNotFoundError(f"No saved report for {date}")

    try:
        return SavedReport.model_validate(_read_json(path))
    except ValidationError as exc:
        raise ReportMalformedError(f"Saved report for {date} has an unexpected format") from exc


def load_investigation(
    reports_dir: Path, report: SavedReport, agent_id: str
) -> Optional[Dict[str, Any]]:
    """Return a saved investigation for this agent and date, if any.

    A standalone file (written by a later on-demand investigation) takes
    precedence over the one embedded in the daily report, because it is newer.
    """
    standalone = reports_dir / "investigations" / f"{report.date}_{agent_id}.json"
    if standalone.is_file():
        data = _read_json(standalone)
        if not isinstance(data, dict):
            raise ReportMalformedError(f"Saved investigation for {agent_id} has an unexpected format")
        return data

    return report.investigations.get(agent_id)


def load_raw_agent_result(reports_dir: Path, date: str, agent_id: str) -> Dict[str, Any]:
    """The agent's screening result exactly as saved (all fields), used as
    input when re-running the existing deep-investigation workflow."""
    report = load_report(reports_dir, date)  # validates the file first
    raw = _read_json(reports_dir / f"agent_performance_{report.date}.json")
    for result in raw.get("agent_results", []):
        if result.get("agent_id") == agent_id:
            return result
    raise ReportNotFoundError(f"Agent {agent_id} is not in the report for {date}")


def save_agent_investigation(reports_dir: Path, date: str, agent_id: str, investigation: Dict[str, Any]) -> Path:
    """Write an on-demand investigation where load_investigation() looks first."""
    folder = reports_dir / "investigations"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{date}_{agent_id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(investigation, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path

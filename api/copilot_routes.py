"""Ask Copilot endpoints.

Reading saved investigations is always allowed (it never calls Claude).
Starting one costs money, so it requires ALL of:
  1. APP_MODE=live and an API key on the server,
  2. a request from this machine (loopback address),
  3. no proxy headers (a reverse proxy would make public traffic look local),
  4. no other investigation already running.
This is enough for a single-user local prototype. A public live deployment
would additionally need authentication, authorization and per-user history.
"""

from datetime import date as Date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request

from api import storage
from api.config import Settings
from api.copilot_runner import InvestigationBusyError, InvestigationRunner
from api.copilot_store import InvestigationStore
from api.schemas import InvestigationRecord, InvestigationSummary, NewInvestigation

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
PROXY_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip")


def build_router(settings: Settings, store: InvestigationStore, runner: InvestigationRunner) -> APIRouter:
    router = APIRouter(prefix="/api")

    def require_live_local(request: Request) -> None:
        if not settings.live_investigations_enabled:
            raise HTTPException(403, "Live investigations are disabled. This server runs in read-only demo mode.")
        host = request.client.host if request.client else None
        if host not in LOOPBACK_HOSTS or any(h in request.headers for h in PROXY_HEADERS):
            raise HTTPException(403, "Live investigations can only be started from this machine.")

    def busy(exc: InvestigationBusyError) -> HTTPException:
        return HTTPException(409, f"Another investigation is still running ({exc}). Wait for it to finish.")

    @router.get("/copilot/investigations", response_model=List[InvestigationSummary])
    def list_investigations(q: Optional[str] = Query(default=None, max_length=200)) -> List[InvestigationSummary]:
        """Saved history, newest first. `q` filters by question text."""
        records = store.list()
        if q:
            needle = q.strip().lower()
            records = [r for r in records if needle in r.question.lower() or needle in (r.agent_id or "").lower()]
        return [InvestigationSummary.model_validate(r.model_dump()) for r in records]

    @router.get("/copilot/investigations/{investigation_id}", response_model=InvestigationRecord)
    def get_investigation(investigation_id: str = Path(pattern=r"^[a-z0-9-]{6,64}$")) -> InvestigationRecord:
        """A saved record. Reading it never re-runs the AI."""
        record = store.get(investigation_id)
        if record is None:
            raise HTTPException(404, "Investigation not found")
        return record

    @router.post("/copilot/investigations", response_model=InvestigationRecord, status_code=202)
    def start_investigation(body: NewInvestigation, request: Request) -> InvestigationRecord:
        """Start a live investigation (paid). Returns at once with status 'running'."""
        require_live_local(request)
        try:
            return runner.start_question(body.question, body.report_date)
        except InvestigationBusyError as exc:
            raise busy(exc)

    @router.post("/reports/{date}/agents/{agent_id}/investigation", response_model=InvestigationRecord, status_code=202)
    def start_agent_investigation(
        date: Date, request: Request, agent_id: str = Path(pattern=r"^[A-Za-z0-9_-]{1,32}$"),
    ) -> InvestigationRecord:
        """Re-run the existing deep agent investigation (paid). Saved results are shown otherwise."""
        require_live_local(request)
        try:
            return runner.start_agent(agent_id, date.isoformat())
        except InvestigationBusyError as exc:
            raise busy(exc)
        except storage.ReportNotFoundError as exc:
            raise HTTPException(404, str(exc))

    return router

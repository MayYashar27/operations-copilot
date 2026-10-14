"""Persistence for Ask Copilot investigations.

`InvestigationStore` is the interface the rest of the API depends on.
`JsonInvestigationStore` implements it with one JSON file per record:

    investigations/examples/   committed, read-only, pre-generated examples
    investigations/local/      this machine's own live runs (git-ignored)

Moving to PostgreSQL later means writing another class with the same methods.
Single-user prototype: there is no per-user isolation yet.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Protocol

from pydantic import ValidationError

from api.schemas import InvestigationError, InvestigationRecord

logger = logging.getLogger("operations_copilot.store")

ID_PATTERN = re.compile(r"^[a-z0-9-]{6,64}$")


class InvestigationStore(Protocol):
    def list(self) -> List[InvestigationRecord]: ...
    def get(self, investigation_id: str) -> Optional[InvestigationRecord]: ...
    def save(self, record: InvestigationRecord) -> None: ...


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JsonInvestigationStore:
    def __init__(self, examples_dir: Path, local_dir: Path):
        self.examples_dir = examples_dir
        self.local_dir = local_dir

    def _read(self, path: Path) -> Optional[InvestigationRecord]:
        try:
            return InvestigationRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError):
            logger.warning("Skipping unreadable investigation file %s", path.name)
            return None

    def list(self) -> List[InvestigationRecord]:
        records = []
        for folder in (self.local_dir, self.examples_dir):
            if folder.is_dir():
                records += [r for p in sorted(folder.glob("*.json")) if (r := self._read(p))]
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def get(self, investigation_id: str) -> Optional[InvestigationRecord]:
        if not ID_PATTERN.match(investigation_id):
            return None
        for folder in (self.local_dir, self.examples_dir):
            path = folder / f"{investigation_id}.json"
            if path.is_file():
                return self._read(path)
        return None

    def save(self, record: InvestigationRecord) -> None:
        """Write atomically. Examples are written only by the generation script."""
        folder = self.examples_dir if record.origin == "example" else self.local_dir
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{record.id}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)

    def mark_interrupted(self) -> int:
        """A record left 'running' means the server stopped mid-run. Say so honestly."""
        count = 0
        for record in self.list():
            if record.status == "running" and record.origin == "local":
                record.status = "failed"
                record.completed_at = now_iso()
                record.error = InvestigationError(
                    type="Interrupted", message="The server stopped before this investigation finished."
                )
                self.save(record)
                count += 1
        return count

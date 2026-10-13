"""Application settings, read once at startup from environment variables.

APP_MODE controls whether the app may spend money on Claude:
    demo (default) - read-only; serves saved reports; no API key needed.
    live           - also allows running new investigations, but only when
                     ANTHROPIC_API_KEY is set. Intended for local use only.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

VALID_MODES = {"demo", "live"}

DISCLAIMER = (
    "Screening statuses are operational review categories, not employee "
    "performance ratings. Thresholds are exploratory and based on synthetic data."
)


@dataclass(frozen=True)
class Settings:
    app_mode: str
    reports_dir: Path
    has_api_key: bool

    @property
    def live_investigations_enabled(self) -> bool:
        # Both conditions are required: an explicit opt-in AND a key.
        return self.app_mode == "live" and self.has_api_key


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    mode = os.getenv("APP_MODE", "demo").strip().lower()
    if mode not in VALID_MODES:
        raise ValueError(f"APP_MODE must be one of {sorted(VALID_MODES)}, got {mode!r}")

    reports_dir = Path(os.getenv("REPORTS_DIR", PROJECT_ROOT / "reports"))

    return Settings(
        app_mode=mode,
        reports_dir=reports_dir,
        has_api_key=bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
    )

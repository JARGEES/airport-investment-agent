from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

DEFAULT_WEIGHTS = {
    "load_factor": 0.20,
    "utilization": 0.20,
    "pax_growth": 0.25,
    "congestion": 0.15,
    "long_haul_ratio": 0.10,
    "unmet_demand": 0.10,
}


@dataclass
class Settings:
    llm_model: str = "gemini/gemini-2.5-flash"
    analysis_mode: Literal["fast", "deep"] = "fast"
    backend_port: int = 8000
    frontend_port: int = 5173
    bts_data_years: int = 3
    bts_download_timeout: int = 120
    scoring_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    @property
    def fast_mode(self) -> bool:
        return self.analysis_mode == "fast"

    @property
    def top_n_airports(self) -> int | None:
        return 100 if self.fast_mode else None


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    weights = dict(DEFAULT_WEIGHTS)
    for key in DEFAULT_WEIGHTS:
        env_key = f"WEIGHT_{key.upper()}"
        if env_key in os.environ:
            weights[key] = float(os.environ[env_key])

    return Settings(
        llm_model=os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash"),
        analysis_mode=os.getenv("ANALYSIS_MODE", "fast"),  # type: ignore[arg-type]
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        frontend_port=int(os.getenv("FRONTEND_PORT", "5173")),
        bts_data_years=int(os.getenv("BTS_DATA_YEARS", "3")),
        bts_download_timeout=int(os.getenv("BTS_DOWNLOAD_TIMEOUT", "120")),
        scoring_weights=weights,
    )


settings = load_settings()

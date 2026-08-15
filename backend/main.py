from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.config import settings
from backend.data.loader import load_t100_data, get_data_vintage

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Airport Investment Intelligence Agent",
    version="0.1.0",
    description="AI-powered analysis of US airport modernization investment opportunities",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.frontend_port}",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("Loading BTS T-100 data into memory...")
    try:
        df = load_t100_data()
        vintage = get_data_vintage()
        logger.info(
            "Data loaded: %d records, period %s",
            vintage["record_count"],
            vintage["latest_period"],
        )
    except FileNotFoundError:
        logger.warning(
            "No BTS data found. Run data/scripts/download_bts.py first. "
            "The server will start but data endpoints will fail."
        )
    logger.info("LLM model: %s", settings.llm_model)
    logger.info("Server ready.")

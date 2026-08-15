from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agent.orchestrator import run_agent
from backend.agent.tools import (
    compare_airports,
    get_airport_stats,
    score_airports,
)
from backend.api.schemas import (
    ChatRequest,
    ChatResponse,
    CompareRequest,
    ScoreRequest,
)
from backend.config import settings
from backend.data.loader import get_data_vintage

router = APIRouter()

AVAILABLE_MODELS = [
    {"id": "gemini/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Google"},
    {"id": "gemini/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "Google"},
    {"id": "anthropic/claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "Anthropic"},
    {"id": "anthropic/claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "Anthropic"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "OpenAI"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
    {"id": "huggingface/mistralai/Mistral-7B-Instruct-v0.3", "name": "Mistral 7B", "provider": "HuggingFace"},
    {"id": "huggingface/meta-llama/Llama-3.1-8B-Instruct", "name": "Llama 3.1 8B", "provider": "HuggingFace"},
    {"id": "ollama/llama3", "name": "Llama 3 (Local)", "provider": "Ollama"},
    {"id": "ollama/mistral", "name": "Mistral (Local)", "provider": "Ollama"},
]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    result = await run_agent(
        message=req.message,
        conversation_id=req.conversation_id,
    )
    return ChatResponse(**result)


@router.get("/airports/{iata_code}/stats")
async def airport_stats(iata_code: str, year: int | None = None) -> dict:
    try:
        return get_airport_stats(iata_code, year)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/airports/compare")
async def airport_compare(req: CompareRequest) -> dict:
    if len(req.codes) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 airport codes")
    try:
        return compare_airports(req.codes, req.metrics)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/airports/score")
async def airport_score(req: ScoreRequest) -> dict:
    if not req.codes:
        raise HTTPException(status_code=400, detail="Provide at least 1 airport code")
    try:
        return score_airports(req.codes, req.weights)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health() -> dict:
    vintage = get_data_vintage()
    return {
        "status": "ok",
        "model": settings.llm_model,
        "analysis_mode": settings.analysis_mode,
        "available_models": AVAILABLE_MODELS,
        "data_vintage": vintage,
    }


@router.patch("/settings")
async def update_settings(body: dict) -> dict:
    if "model" in body:
        settings.llm_model = body["model"]
    if "analysis_mode" in body and body["analysis_mode"] in ("fast", "deep"):
        settings.analysis_mode = body["analysis_mode"]
    return {
        "model": settings.llm_model,
        "analysis_mode": settings.analysis_mode,
    }

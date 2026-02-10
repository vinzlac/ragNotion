"""
API RAG FastAPI (PRD ON-1). Endpoint /chat pour question → réponse + sources.
"""
from __future__ import annotations

import logging
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

import time

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.rag_chain import build_rag_chain
from shared.config import APISettings, LangSmithSettings
from shared.schemas import ChatResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Activation LangSmith si configuré (PRD observabilité build)
# LangChain lit LANGCHAIN_* ; on mappe depuis LANGSMITH_* (site LangSmith)
_langsmith = LangSmithSettings()
if _langsmith.api_key and _langsmith.tracing:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = _langsmith.api_key
    os.environ["LANGCHAIN_ENDPOINT"] = _langsmith.endpoint
    if _langsmith.project:
        os.environ["LANGCHAIN_PROJECT"] = _langsmith.project
    logger.info("LangSmith tracing activé (project=%s)", _langsmith.project or "default")

_api_settings = APISettings()
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="RAG Notion API",
    description="Assistant de recherche conversationnel sur la base Notion",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def log_latency(request: Request, call_next):
    """Métriques latence par requête (PRD OBS-1.1)."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("latency_ms=%.0f path=%s status=%s", duration_ms, request.url.path, response.status_code)
    return response


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


# Chaîne RAG initialisée au démarrage (singleton)
_rag = None


def get_rag():
    global _rag
    if _rag is None:
        _rag = build_rag_chain()
    return _rag


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(_api_settings.rate_limit_chat)
def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """Pose une question et reçoit une réponse sourcée (PRD ON-1.1)."""
    try:
        chain = get_rag()
        out = chain.invoke(chat_request.question)
        # Log basique pour coût/qualité : nombre de sources (OBS-1.2, OBS-2.1)
        logger.info("chat sources_count=%s rag_version=%s", len(out.sources), out.rag_version)
        # Détection basique réponses suspectes (PRD QLT-2.2)
        if len(out.sources) == 0 and "je ne sais pas" not in out.answer.lower():
            logger.warning("suspicious_response no_sources question_len=%s", len(chat_request.question))
        if len(out.answer.strip()) < 20 and len(out.sources) == 0:
            logger.warning("suspicious_response vague_or_empty answer_len=%s", len(out.answer))
        return out
    except Exception as e:
        logger.exception("Erreur RAG: %s", e)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la réponse.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

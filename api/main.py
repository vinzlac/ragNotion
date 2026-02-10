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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.rag_chain import build_rag_chain
from shared.schemas import ChatResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Notion API",
    description="Assistant de recherche conversationnel sur la base Notion",
    version="0.1.0",
)


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
def chat(request: ChatRequest) -> ChatResponse:
    """Pose une question et reçoit une réponse sourcée (PRD ON-1.1)."""
    try:
        chain = get_rag()
        return chain.invoke(request.question)
    except Exception as e:
        logger.exception("Erreur RAG: %s", e)
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la réponse.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

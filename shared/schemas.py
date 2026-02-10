"""
Schémas partagés pour les documents et métadonnées indexés (PRD OFF-3.2).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Métadonnées associées à chaque chunk pour filtrage et sourcing."""
    page_id: str = Field(..., description="ID de la page Notion")
    title: str = Field(default="", description="Titre de la page")
    source_url: str | None = Field(None, description="URL Notion si disponible")
    last_edited_time: str | None = Field(None, description="Dernière modification (ISO)")
    chunk_index: int = Field(default=0, description="Index du chunk dans la page")


class ChatSource(BaseModel):
    """Source Notion retournée avec la réponse (PRD ON-4.2)."""
    page_id: str
    title: str
    url: str | None
    snippet: str = Field(..., description="Extrait du chunk utilisé")


class ChatResponse(BaseModel):
    """Réponse du RAG avec sources."""
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
    rag_version: str = "v1"

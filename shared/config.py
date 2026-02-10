"""
Configuration centralisée (env) pour offline et api.
Aligné sur PRD : NOTION_TOKEN, QDRANT_*, COHERE_*, MISTRAL_*, LANGSMITH_*.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTION_", extra="ignore")
    token: str = Field(..., description="Token d'intégration Notion")


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")
    url: str = Field(..., description="URL Qdrant (Cloud ou local)")
    api_key: str | None = Field(None, description="API key Qdrant Cloud")
    collection_name: str = Field(default="rag_notion", description="Nom de la collection")


class CohereSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COHERE_", extra="ignore")
    api_key: str = Field(..., description="Clé API Cohere (embeddings + rerank)")


class MistralSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MISTRAL_", extra="ignore")
    api_key: str = Field(..., description="Clé API Mistral")
    model: str = Field(default="mistral-small-latest", description="Modèle Mistral")
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class LangSmithSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGSMITH_", extra="ignore")
    api_key: str | None = Field(None, description="Clé LangSmith (build)")
    tracing_v2: bool = Field(default=True, description="Activer tracing LangChain")


# Paramètres RAG externalisables (PRD §9)
class RAGPipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", extra="ignore")

    # Offline — chunking
    chunk_size: int = Field(default=512, ge=64, le=2048)
    chunk_overlap: int = Field(default=64, ge=0, le=512)

    # Online — retrieval
    top_k: int = Field(default=20, ge=1, le=100, description="Nombre de chunks récupérés avant MMR/rerank")
    top_n: int = Field(default=5, ge=1, le=20, description="Nombre de chunks après rerank (ou gardés pour le prompt)")
    mmr_lambda: float = Field(default=0.5, ge=0, le=1, description="MMR : 0 = diversité max, 1 = pertinence max")
    rerank_enabled: bool = Field(default=False, description="Activer Cohere rerank")

    # Traçabilité
    rag_version: str = Field(default="v1", description="Version du pipeline pour logs")


def get_rag_settings() -> RAGPipelineSettings:
    return RAGPipelineSettings()

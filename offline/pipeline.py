"""
Pipeline Offline : Notion → chunking → embeddings → Qdrant (PRD OFF-2.3, OFF-3.x).
Orchestration claire avec LangChain (sans agent).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_cohere import CohereEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from shared.config import CohereSettings, QdrantSettings, RAGPipelineSettings, get_rag_settings

from .notion_loader import load_notion_documents

logger = logging.getLogger(__name__)


def build_text_splitter(settings: RAGPipelineSettings) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def prepare_docs_with_metadata(
    documents: list[Document],
    splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    """
    Découpe les documents et attache les métadonnées (page_id, titre, etc.) à chaque chunk.
    """
    chunks: list[Document] = []
    for doc in documents:
        meta = doc.metadata
        page_id = meta.get("page_id", "")
        title = meta.get("title", "")
        source_url = meta.get("source_url")
        last_edited = meta.get("last_edited_time")
        sub_docs = splitter.split_documents([doc])
        for i, sub in enumerate(sub_docs):
            sub.metadata["page_id"] = page_id
            sub.metadata["title"] = title
            sub.metadata["source_url"] = source_url
            sub.metadata["last_edited_time"] = last_edited
            sub.metadata["chunk_index"] = i
            chunks.append(sub)
    return chunks


def get_qdrant_client(qdrant: QdrantSettings) -> QdrantClient:
    return QdrantClient(url=qdrant.url, api_key=qdrant.api_key)


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
) -> None:
    """Crée la collection si elle n'existe pas (taille de vecteur Cohere embed)."""
    collections = client.get_collections()
    names = [c.name for c in collections.collections]
    if collection_name not in names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        logger.info("Collection créée : %s (size=%s)", collection_name, vector_size)


def run_offline_pipeline(
    notion_token: str,
    *,
    page_ids: list[str] | None = None,
    database_id: str | None = None,
    qdrant: QdrantSettings | None = None,
    cohere: CohereSettings | None = None,
    rag_settings: RAGPipelineSettings | None = None,
) -> dict[str, Any]:
    """
    Exécute la pipeline complète (sync) :
    1. Charger les pages Notion (async run in loop)
    2. Chunker avec métadonnées
    3. Embedder (Cohere)
    4. Upsert dans Qdrant
    """
    from shared.config import CohereSettings, QdrantSettings

    qdrant = qdrant or QdrantSettings()
    cohere = cohere or CohereSettings()
    rag_settings = rag_settings or get_rag_settings()

    # 1) Chargement Notion (API async)
    documents = asyncio.run(
        load_notion_documents(
            notion_token,
            page_ids=page_ids,
            database_id=database_id,
        )
    )
    if not documents:
        logger.warning("Aucun document chargé depuis Notion")
        return {"documents_loaded": 0, "chunks_indexed": 0}

    # 2) Chunking
    splitter = build_text_splitter(rag_settings)
    chunks = prepare_docs_with_metadata(documents, splitter)
    logger.info("Documents: %s → Chunks: %s", len(documents), len(chunks))

    # 3) Embeddings + 4) Qdrant
    embeddings = CohereEmbeddings(
        model="embed-multilingual-v3.0", cohere_api_key=cohere.api_key
    )
    vector_size = 1024  # Cohere embed-multilingual-v3.0

    client = get_qdrant_client(qdrant)
    ensure_collection(client, qdrant.collection_name, vector_size)

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=qdrant.collection_name,
        embedding=embeddings,
    )
    ids = vectorstore.add_documents(chunks)
    logger.info("Indexés %s chunks dans Qdrant", len(ids))

    return {
        "documents_loaded": len(documents),
        "chunks_indexed": len(chunks),
        "rag_version": rag_settings.rag_version,
    }

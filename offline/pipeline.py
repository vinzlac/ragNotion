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

from .checkpoint import get_checkpoint_path, load_checkpoint, save_checkpoint
from .notion_loader import expand_page_ids, list_notion_page_versions, load_notion_documents

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


def delete_points_by_page_ids(
    client: QdrantClient,
    collection_name: str,
    page_ids: list[str],
) -> None:
    """Supprime tous les points dont le payload page_id est dans page_ids (PRD OFF-2.4)."""
    if not page_ids:
        return
    from qdrant_client.http import models as qm

    client.delete(
        collection_name=collection_name,
        points_selector=qm.FilterSelector(
            filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="page_id",
                        match=qm.MatchAny(any=page_ids),
                    )
                ]
            )
        ),
    )
    logger.info("Supprimés de Qdrant: %s pages", len(page_ids))


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
    Exécute la pipeline (sync). Si incremental=True et checkpoint présent :
    ne charge que les pages nouvelles ou modifiées, supprime les pages retirées de Notion (PRD OFF-2.4).
    """
    from datetime import datetime
    from shared.config import CohereSettings, QdrantSettings

    qdrant = qdrant or QdrantSettings()
    cohere = cohere or CohereSettings()
    rag_settings = rag_settings or get_rag_settings()

    client = get_qdrant_client(qdrant)
    vector_size = 1024
    ensure_collection(client, qdrant.collection_name, vector_size)

    # État actuel Notion (page_id → last_edited_time)
    # Si page_ids fournis : étendre aux sous-pages et aux lignes des tables
    if page_ids is not None:
        page_ids = asyncio.run(expand_page_ids(notion_token, page_ids))
    current_versions = asyncio.run(
        list_notion_page_versions(
            notion_token,
            page_ids=page_ids,
            database_id=database_id,
        )
    )
    if not current_versions:
        logger.warning("Aucune page trouvée dans Notion")
        return {"documents_loaded": 0, "chunks_indexed": 0, "pages_deleted": 0}

    to_fetch: list[str]
    to_delete: list[str]
    scope: str

    if rag_settings.incremental:
        checkpoint_path = get_checkpoint_path(rag_settings.checkpoint_path)
        prev = load_checkpoint(checkpoint_path)
        prev_versions = (prev or {}).get("page_last_edited") or {}
        scope = f"db:{database_id}" if database_id else "pages"
        # Nouvelles ou modifiées
        to_fetch = [
            pid
            for pid, last in current_versions.items()
            if prev_versions.get(pid) != last
        ]
        # Supprimées (dans le checkpoint mais plus dans Notion)
        to_delete = [pid for pid in prev_versions if pid not in current_versions]
        # Anciens chunks des pages modifiées (à remplacer)
        to_replace = [p for p in to_fetch if p in prev_versions]
        pages_to_remove = list(set(to_delete) | set(to_replace))
        if pages_to_remove:
            delete_points_by_page_ids(client, qdrant.collection_name, pages_to_remove)
        if not to_fetch:
            logger.info("Ingestion incrémentale : rien à mettre à jour")
            return {"documents_loaded": 0, "chunks_indexed": 0, "pages_deleted": len(to_delete)}
        # Charger uniquement les pages à mettre à jour
        documents = asyncio.run(
            load_notion_documents(notion_token, page_ids=to_fetch, database_id=None)
        )
    else:
        to_delete = []
        scope = f"db:{database_id}" if database_id else "pages"
        documents = asyncio.run(
            load_notion_documents(
                notion_token,
                page_ids=page_ids,
                database_id=database_id,
            )
        )

    if not documents:
        if rag_settings.incremental:
            save_checkpoint(
                checkpoint_path,
                last_sync_time=datetime.utcnow().isoformat() + "Z",
                scope=scope,
                page_last_edited=current_versions,
            )
        return {"documents_loaded": 0, "chunks_indexed": 0, "pages_deleted": len(to_delete)}

    splitter = build_text_splitter(rag_settings)
    chunks = prepare_docs_with_metadata(documents, splitter)
    logger.info("Documents: %s → Chunks: %s", len(documents), len(chunks))

    embeddings = CohereEmbeddings(
        model="embed-multilingual-v3.0", cohere_api_key=cohere.api_key
    )
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=qdrant.collection_name,
        embedding=embeddings,
    )
    ids = vectorstore.add_documents(chunks)
    logger.info("Indexés %s chunks dans Qdrant", len(ids))

    if rag_settings.incremental:
        save_checkpoint(
            get_checkpoint_path(rag_settings.checkpoint_path),
            last_sync_time=datetime.utcnow().isoformat() + "Z",
            scope=scope,
            page_last_edited=current_versions,
        )

    return {
        "documents_loaded": len(documents),
        "chunks_indexed": len(chunks),
        "pages_deleted": len(to_delete),
        "rag_version": rag_settings.rag_version,
    }

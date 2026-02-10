"""
Pipeline Online : retrieval → MMR → (rerank) → prompt → LLM (PRD ON-2, ON-3, ON-4).
Orchestration avec LangChain LCEL, sans agent.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_cohere import CohereEmbeddings, CohereRerank
from langchain_mistralai import ChatMistralAI
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from shared.config import (
    CohereSettings,
    MistralSettings,
    QdrantSettings,
    RAGPipelineSettings,
    get_rag_settings,
)
from shared.prompts import get_rag_prompt
from shared.schemas import ChatResponse, ChatSource

logger = logging.getLogger(__name__)


def _format_docs(docs: list) -> str:
    """Formate les documents pour le prompt."""
    return "\n\n---\n\n".join(
        f"[Source: {d.metadata.get('title', 'Sans titre')}]\n{d.page_content}"
        for d in docs
    )


def _docs_to_sources(docs: list) -> list[ChatSource]:
    """Extrait les sources pour la réponse (PRD ON-4.2)."""
    seen: set[tuple[str, str]] = set()
    sources: list[ChatSource] = []
    for d in docs:
        page_id = d.metadata.get("page_id", "")
        title = d.metadata.get("title", "")
        key = (page_id, title)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            ChatSource(
                page_id=page_id,
                title=title,
                url=d.metadata.get("source_url"),
                snippet=(d.page_content[:300] + "…") if len(d.page_content) > 300 else d.page_content,
            )
        )
    return sources


def build_retriever(
    qdrant: QdrantSettings,
    cohere: CohereSettings,
    rag_settings: RAGPipelineSettings,
) -> Any:
    """
    Retriever Qdrant avec MMR (diversité).
    search_type="mmr" avec fetch_k=top_k et lambda_mult=mmr_lambda.
    """
    client = QdrantClient(url=qdrant.url, api_key=qdrant.api_key)
    embeddings = CohereEmbeddings(
        model="embed-multilingual-v3.0",
        cohere_api_key=cohere.api_key,
    )
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=qdrant.collection_name,
        embedding=embeddings,
    )
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": rag_settings.top_n,
            "fetch_k": rag_settings.top_k,
            "lambda_mult": rag_settings.mmr_lambda,
        },
    )
    return retriever


def build_rag_chain(
    qdrant: QdrantSettings | None = None,
    cohere: CohereSettings | None = None,
    mistral: MistralSettings | None = None,
    rag_settings: RAGPipelineSettings | None = None,
) -> Any:
    """
    Chaîne LCEL : retriever → (optionnel rerank) → format_docs → prompt → LLM → str.
    Retourne un runnable qui prend {"question": str} et produit (answer, sources).
    """
    from shared.config import CohereSettings, MistralSettings, QdrantSettings

    qdrant = qdrant or QdrantSettings()
    cohere = cohere or CohereSettings()
    mistral = mistral or MistralSettings()
    rag_settings = rag_settings or get_rag_settings()

    retriever = build_retriever(qdrant, cohere, rag_settings)
    prompt = get_rag_prompt(rag_settings.rag_version)
    llm = ChatMistralAI(
        model=mistral.model,
        mistral_api_key=mistral.api_key,
        temperature=mistral.temperature,
        max_tokens=mistral.max_tokens,
    )

    if rag_settings.rerank_enabled:
        rerank = CohereRerank(
            model="rerank-multilingual-v3.0",
            cohere_api_key=cohere.api_key,
            top_n=rag_settings.top_n,
        )

        class RAGWithSources:
            def invoke(self, question: str) -> ChatResponse:
                docs = retriever.invoke(question)
                if not docs:
                    return ChatResponse(
                        answer="Je ne sais pas. Aucun document pertinent trouvé.",
                        sources=[],
                        rag_version=rag_settings.rag_version,
                    )
                # CohereRerank.compress_documents(query, documents) retourne les docs rerankés
                top_docs = rerank.compress_documents(question, docs)
                context = _format_docs(top_docs)
                result = prompt.invoke({"context": context, "question": question})
                answer = llm.invoke(result).content
                return ChatResponse(
                    answer=answer or "Je ne sais pas.",
                    sources=_docs_to_sources(top_docs),
                    rag_version=rag_settings.rag_version,
                )

        return RAGWithSources()

    # Sans rerank : on doit quand même récupérer les docs pour les sources
    class RAGWithSources:
        def invoke(self, question: str) -> ChatResponse:
            docs = retriever.invoke(question)
            context = _format_docs(docs)
            if not context.strip():
                return ChatResponse(
                    answer="Je ne sais pas. Aucun document pertinent trouvé.",
                    sources=[],
                    rag_version=rag_settings.rag_version,
                )
            result = prompt.invoke({"context": context, "question": question})
            answer = llm.invoke(result).content
            return ChatResponse(
                answer=answer or "Je ne sais pas.",
                sources=_docs_to_sources(docs),
                rag_version=rag_settings.rag_version,
            )

    return RAGWithSources()

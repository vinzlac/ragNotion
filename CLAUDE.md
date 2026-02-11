# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Notion is a Retrieval-Augmented Generation pipeline that indexes Notion databases and exposes a conversational search API. It uses Cohere embeddings/reranking, Qdrant vector store, and Mistral LLM, orchestrated via LangChain LCEL.

## Commands

```bash
just install              # Install deps (uv sync)
just api                  # Run FastAPI locally on :8000 (with reload)
just ingest-db <id>       # Index an entire Notion database
just ingest-pages <ids>   # Index specific pages (comma-separated)
just ingest-incremental   # Incremental ingestion using checkpoint
just list-pages <id>      # List Notion pages without indexing
just test                 # Run pytest
just eval                 # Run RAG evaluation
just lint                 # ruff check .
just fmt                  # ruff format .
```

Package manager is **uv** (not pip/poetry). Task runner is **just** (not make).

## Architecture

The system has two phases with shared configuration:

### Offline Phase (Ingestion): `offline/`
```
Notion API → load_notion_documents() → RecursiveCharacterTextSplitter → CohereEmbeddings → Qdrant
```
- **`run_ingest.py`**: CLI entry point
- **`pipeline.py`**: Orchestrates chunking, embedding, upserting to Qdrant; supports incremental ingestion via checkpoint
- **`notion_loader.py`**: Async Notion API client, recursively expands child_page and child_database blocks
- **`checkpoint.py`**: Tracks `page_id → last_edited_time` for incremental syncs

### Online Phase (API): `api/`
```
POST /chat → MMR retriever → (optional) Cohere rerank → prompt template → Mistral LLM → ChatResponse
```
- **`main.py`**: FastAPI app with `/health` and `/chat` endpoints, rate limiting via slowapi
- **`rag_chain.py`**: Builds the RAG chain (retriever → rerank → format → prompt → LLM), deduplicates sources by (page_id, title)

### Shared: `shared/`
- **`config.py`**: All settings as Pydantic-settings classes, driven by env vars (NotionSettings, QdrantSettings, CohereSettings, MistralSettings, RAGPipelineSettings, APISettings, LangSmithSettings)
- **`schemas.py`**: Data models (ChunkMetadata, ChatSource, ChatResponse)
- **`prompts.py`**: Versioned RAG prompt templates (French language, instructs LLM to say "Je ne sais pas" when unsure)

### Eval: `eval/`
- **`run_eval.py`**: Runs RAG chain against a dataset JSON, records metrics
- **`compare_results.py`**: Compares two eval runs side-by-side

## Key Configuration

All config is environment-driven via `.env`. See `.env.example` for all variables. Key RAG tuning params:
- `RAG_CHUNK_SIZE` (512), `RAG_CHUNK_OVERLAP` (64)
- `RAG_TOP_K` (20, fetch before MMR), `RAG_TOP_N` (5, keep after rerank)
- `RAG_MMR_LAMBDA` (0.5: balance relevance/diversity)
- `RAG_RERANK_ENABLED` (false), `RAG_INCREMENTAL` (false)

## Code Conventions

- **Language**: Code in English, comments in French for complex logic. User-facing responses in French.
- **Linting**: ruff with 100-char line length, Python 3.11+ target
- **Testing**: pytest, test files in `tests/`, pythonpath includes repo root
- **Principles**: YAGNI, one responsibility per function, no invented APIs/behavior

## Deployment

- **Dockerfile.api**: API image for Cloud Run Service
- **Dockerfile.offline**: Ingestion image for Cloud Run Job
- **docker-compose.yml**: Local dev (API + optional local Qdrant)
- **Prefect** (optional, `uv sync -E cloud`): Cloud scheduling for ingestion via `offline/prefect_flow.py`
- See `deploy/README.md` for full GCP deployment instructions

## Observability

- **Dev**: LangSmith tracing (enabled via `LANGSMITH_TRACING=true`)
- **Prod**: Langfuse (future)
- Structured logging with latency_ms, sources_count, rag_version

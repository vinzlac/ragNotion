# RAG Notion — recettes just (PRD, stack uv)
# Usage: just <recipe> [args]

# Dépendances et env Python (uv)
install:
    uv sync

# Ingestion : indexer une base Notion
ingest-db database_id:
    uv run python -m offline.run_ingest --database-id {{ database_id }}

# Ingestion : indexer des pages spécifiques (liste séparée par des virgules)
ingest-pages page_ids:
    uv run python -m offline.run_ingest --page-ids "{{ page_ids }}"

# Ingestion incrémentale (checkpoint)
ingest-incremental database_id:
    uv run python -m offline.run_ingest --database-id {{ database_id }} --incremental

# Flow Prefect (uv sync -E cloud)
prefect-ingest database_id:
    uv run python -m offline.prefect_flow --database-id {{ database_id }}

# Aide ingestion
ingest:
    @just --list | grep ingest

# API locale (FastAPI)
api:
    uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Tests
test:
    uv run pytest tests/ -v

# Évaluation RAG (dataset de questions)
eval:
    uv run python -m eval.run_eval

# Comparer deux runs d'éval (ex: just eval puis RAG_RERANK_ENABLED=true just eval → just compare-eval eval/results.json eval/results_rerank.json)
compare-eval a b:
    uv run python -m eval.compare_results {{ a }} {{ b }}

# Lint (ruff)
lint:
    uv run ruff check .

# Format (ruff)
fmt:
    uv run ruff format .

# Liste des recettes
default:
    @just --list

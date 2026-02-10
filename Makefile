# RAG Notion — commandes locales (PRD)
.PHONY: ingest ingest-db ingest-pages api install

# Ingestion : indexer une base Notion (remplacer DATABASE_ID)
ingest-db:
	python -m offline.run_ingest --database-id $(DATABASE_ID)

# Ingestion : indexer des pages spécifiques (remplacer PAGE_IDS)
ingest-pages:
	python -m offline.run_ingest --page-ids "$(PAGE_IDS)"

# Raccourci (exemple avec variable)
ingest:
	@echo "Usage: make ingest-db DATABASE_ID=xxx  OU  make ingest-pages PAGE_IDS=id1,id2"

# API locale
api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

install:
	pip install -e .

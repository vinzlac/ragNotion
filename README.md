# RAG Notion

Pipeline RAG (Retrieval-Augmented Generation) qui indexe des bases Notion et expose une API conversationnelle. Pose une question, obtiens une réponse sourcée depuis tes pages Notion.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    OFFLINE (ingestion)                   │
│                                                         │
│  Notion API → Chargement pages → Chunking → Embeddings │
│                                      ↓                  │
│                                  Qdrant Cloud           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     ONLINE (API)                        │
│                                                         │
│  POST /chat → Retriever MMR → Rerank (opt.) → Mistral  │
│       ↑           ↓                              ↓      │
│    Question    Qdrant Cloud              Réponse + Sources│
└─────────────────────────────────────────────────────────┘
```

## Stack technique

| Composant | Technologie |
|---|---|
| Orchestration RAG | LangChain (LCEL) |
| Embeddings & Rerank | Cohere (multilingual-v3.0) |
| Vector Store | Qdrant Cloud |
| LLM | Mistral AI |
| API | FastAPI |
| Source de données | Notion API |
| Orchestration batch | Prefect (optionnel) |
| Observabilité | LangSmith (dev) / Langfuse (prod) |

## Prérequis

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets)
- [just](https://github.com/casey/just) (task runner)
- Comptes API : Notion, Cohere, Mistral, Qdrant Cloud

## Installation

```bash
git clone https://github.com/vinzlac/ragNotion.git
cd ragNotion

# Configurer les variables d'environnement
cp .env.example .env
# Remplir les clés API dans .env

# Installer les dépendances
just install
```

## Utilisation

### Lancer l'API

```bash
just api
# → http://localhost:8000
# → Swagger : http://localhost:8000/docs
```

### Indexer du contenu Notion

```bash
# Indexer une base Notion complète
just ingest-db <DATABASE_ID>

# Indexer des pages spécifiques
just ingest-pages "page_id1,page_id2"

# Ingestion incrémentale (ne réindexe que les pages modifiées)
just ingest-incremental <DATABASE_ID>
```

### Explorer les pages Notion (sans indexer)

```bash
just list-pages <DATABASE_ID>
just list-pages-by-ids "page_id1,page_id2"
just list-pages-debug "page_id"          # mode debug avec blocs
```

### Tests et qualité

```bash
just test    # pytest
just lint    # ruff check
just fmt     # ruff format
just eval    # évaluation RAG sur dataset
```

## Docker

```bash
# Dev local
docker compose up api

# Build des images
docker build -f Dockerfile.api -t rag-notion-api .
docker build -f Dockerfile.offline -t rag-notion-offline .

# Lancer manuellement
docker run -p 8000:8000 --env-file .env rag-notion-api
docker run --env-file .env rag-notion-offline --database-id <ID>
```

## Déploiement Cloud (GCP)

Voir [`deploy/README.md`](deploy/README.md) pour le déploiement sur Cloud Run (API en Service, ingestion en Job) et l'orchestration via Prefect Cloud.

## Configuration

Toute la configuration est pilotée par variables d'environnement (`.env`). Voir [`.env.example`](.env.example) pour la liste complète.

Paramètres RAG ajustables :

| Variable | Défaut | Description |
|---|---|---|
| `RAG_CHUNK_SIZE` | 512 | Taille des chunks (caractères) |
| `RAG_CHUNK_OVERLAP` | 64 | Chevauchement entre chunks |
| `RAG_TOP_K` | 20 | Documents récupérés avant MMR |
| `RAG_TOP_N` | 5 | Documents retenus après rerank |
| `RAG_MMR_LAMBDA` | 0.5 | 0 = diversité max, 1 = pertinence max |
| `RAG_RERANK_ENABLED` | false | Activer le reranking Cohere |
| `RAG_INCREMENTAL` | false | Ingestion incrémentale |

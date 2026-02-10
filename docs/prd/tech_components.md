# Infrastructure technique — Local (dev) & Cloud (prod) pour RAG Notion

Ce document décrit l’infrastructure **complète** (compute, réseau, secrets, observabilité, CI/CD) pour :
- un environnement **local** (développement)
- un environnement **cloud production** (prod)

Stack cible (déjà actée) :
- Source : Notion
- Vector DB : Qdrant Cloud
- Embeddings + Rerank + (optionnel) LLM : Cohere (plan gratuit au début)
- LLM principal : Mistral
- Framework : LangChain
- Offline orchestration : Prefect Cloud
- Observabilité : LangSmith (build) → Langfuse (prod), + option OpenTelemetry/Grafana

---

## 1) Architecture fonctionnelle (vue simple)

### OFFLINE (Build / ingestion)
Notion → extraction → chunking → embeddings → upsert Qdrant

### ONLINE (Serve / retrieval + génération)
Question → retrieval Qdrant → MMR → (rerank optionnel) → prompt → LLM → réponse + sources

---

## 2) Infrastructure locale (dev)

### 2.1 Objectifs
- itérer vite sur : parsing Notion, chunking, retrieval, prompts
- débugger facilement
- rester proche de la prod (Docker, variables env, mêmes API externes)

### 2.2 Composants locaux

#### A) Code & exécution
- **Repo** (monorepo conseillé)
  - `/offline/` : ingestion Notion
  - `/api/` : service RAG (FastAPI)
  - `/shared/` : schémas docs, utilitaires, prompts
- **Python** (venv/poetry) + **Docker** pour parité prod

#### B) Services externes utilisés même en local
- **Notion API** (source)
- **Qdrant Cloud** (index)
- **Cohere API** (embeddings + rerank)
- **Mistral API** (génération)

> En local, tu peux soit utiliser Qdrant Cloud directement (simple), soit un Qdrant local (option).

#### C) Optionnel (local) : Qdrant en Docker
- utile si tu veux tester sans dépendre du cloud
- mais attention : il faudra synchroniser la config et les schémas

#### D) Orchestration locale
- exécution manuelle : `python offline/run_ingest.py`
- ou `make ingest`
- ou un cron local (rarement nécessaire)

---

### 2.3 Réseau local
- appels sortants HTTPS vers : Notion / Qdrant Cloud / Cohere / Mistral
- aucun port entrant requis (sauf API locale sur `localhost:8000`)

---

### 2.4 Secrets en local
- `.env` (non commité)
  - `NOTION_TOKEN`
  - `QDRANT_URL`, `QDRANT_API_KEY`
  - `COHERE_API_KEY`
  - `MISTRAL_API_KEY`
  - `LANGSMITH_API_KEY` (phase build)
- recommandation : `.env.example` + doc

---

### 2.5 Observabilité locale (build)
- logs structurés (json) + trace_id
- LangSmith activé en dev (tracing LangChain)
- métriques simples via logs :
  - latence retrieval / llm
  - top_k, top_n
  - coût tokens estimé

---

## 3) Infrastructure Cloud (prod)

### 3.1 Objectifs prod
- service RAG **stable**, **scalable**, **mesurable**
- ingestion **incrémentale** fiable
- coûts maîtrisés (serverless, scale-to-zero)
- observabilité : perfs + coût + qualité
- sécurité : secrets, accès API, audit

---

## 4) Environnement Cloud — OFFLINE (ingestion)

### 4.1 Orchestration : Prefect Cloud
- planifie et déclenche la pipeline (cron / manuel)
- retries / backoff par tâche
- historique des runs, statut, logs

**Responsabilités**
- “Quand exécuter”
- “Que faire si ça rate”
- “Visibilité et relance”

---

### 4.2 Compute batch : Cloud Run Jobs
- exécute le container d’ingestion (`offline-ingest:latest`)
- démarre → run → s’arrête (batch)
- scale-to-zero natif
- logs centralisés

**Responsabilités**
- “Exécuter le code offline”
- “Isoler les dépendances”
- “Offrir un runtime serverless”

---

### 4.3 Stockage / état
- **Qdrant Cloud** : embeddings + payload metadata
- **Checkpoint ingestion** (recommandé)
  - option A : table légère (ex: Firestore / SQLite cloud / bucket)
  - option B : stocker un doc “checkpoint” (ou payload) côté Qdrant
  - option C : stockage simple dans un bucket (JSON)
  
> Le checkpoint doit au minimum stocker : `last_successful_sync_time` + éventuellement un hash par page.

---

### 4.4 Flux réseau offline
Cloud Run Job → (HTTPS)
- Notion API
- Cohere (embeddings)
- Qdrant Cloud (upsert)

---

## 5) Environnement Cloud — ONLINE (API RAG)

### 5.1 Compute : Cloud Run Service
- déploie un container (`rag-api:latest`) exposé en HTTPS
- autoscaling selon trafic
- stateless (pas d’état local durable)

**Configuration recommandée V1**
- `min instances = 0` (coût minimal)
- timeouts adaptés (LLM peut être long)
- concurrency paramétrée (éviter saturation / quotas)

---

### 5.2 Flux réseau online
Cloud Run Service → (HTTPS)
- Qdrant Cloud (retrieval)
- Cohere (optionnel : rerank + embeddings question)
- Mistral (génération)

---

### 5.3 Auth & sécurité API
Options (ordre de complexité croissante) :
1. **API key** simple (header)
2. JWT / OAuth (si besoin d’identité)
3. Cloud IAM / IAP (si usage interne GCP)

**Bonnes pratiques**
- rate limiting applicatif (par user / ip / key)
- quotas (anti-abus)
- audit des requêtes (anonymisation user_id si besoin)

---

## 6) Observabilité & Qualité (cloud)

### 6.1 Phase build (pré-prod / V1) : LangSmith
- tracing complet (question, docs, prompt, réponse)
- evals offline sur dataset
- comparaison config (MMR, top_k, rerank on/off)

### 6.2 Phase prod : Langfuse
- monitoring long terme (volumétrie + rétention)
- dashboards coûts/latence
- alerting possible
- auto-hébergement (si souhaité) ou SaaS

### 6.3 Option “infra observability” (recommandée à maturité)
- **OpenTelemetry**
  - traces : retrieval, rerank, llm, total
  - metrics : latence p95, erreurs, taux cold start
- **Grafana**
  - Tempo (traces)
  - Prometheus (metrics)
  - Loki (logs) — optionnel si besoin centralisation avancée

---

## 7) CI/CD (cloud)

### 7.1 Build & Release
- Build images Docker :
  - `offline-ingest`
  - `rag-api`
- Push vers un registry (Artifact Registry / équivalent)

### 7.2 Déploiement OFFLINE
- mettre à jour Cloud Run Job vers nouvelle image
- Prefect continue de déclencher le job

### 7.3 Déploiement ONLINE
- déployer Cloud Run Service nouvelle image
- rollback simple (révision précédente)

---

## 8) Gestion des secrets (cloud)

### 8.1 Secrets requis
- Notion token
- Qdrant URL + API key
- Cohere API key
- Mistral API key
- LangSmith API key (build)
- Langfuse keys (prod)

### 8.2 Stockage recommandé
- Secret Manager (prod)
- injection au runtime via env vars sécurisées

---

## 9) Paramètres RAG (prod) à externaliser (config)
- chunk size / overlap (offline)
- top_k retrieval
- MMR on/off + paramètres
- rerank on/off + top_n
- prompt_version
- température / max_tokens
- timeouts & retries
- rate limiting & quotas
- `rag_version` (traçabilité)

---

## 10) Environnements
- **dev** : local + services cloud (Qdrant Cloud, Cohere, Mistral)
- **staging** : Cloud Run (service/job) + LangSmith + dataset d’éval
- **prod** : Cloud Run + Langfuse + alerting + rétention

---

## 11) Diagramme textuel final (prod)

### OFFLINE
Prefect Cloud
  → Cloud Run Job (offline-ingest container)
    → Notion API
    → Cohere Embeddings
    → Qdrant Cloud (upsert)
    → logs + métriques

### ONLINE
Utilisateur / App
  → Cloud Run Service (rag-api container)
    → Qdrant Cloud (retrieval + MMR)
    → Cohere Rerank (optionnel)
    → Mistral LLM (answer)
    → Langfuse (prod) / LangSmith (build)
    → logs + métriques + traces

---

## 12) Pourquoi cette infra est “bonne”
- serverless : coût proportionnel à l’usage
- séparation offline/online : robuste et scalable
- observabilité d’abord : qualité pilotable
- migrations propres : LangSmith → Langfuse préparée
- modularité : rerank activable sans refonte
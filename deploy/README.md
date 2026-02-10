# Déploiement Cloud (PRD OFF-4, ON-1.2)

## Prérequis

- `gcloud` configuré avec un projet GCP
- Artifact Registry (ou Container Registry) pour les images
- Secret Manager pour les secrets (recommandé)

## Build des images

```bash
# Depuis la racine du repo
docker build -f Dockerfile.offline -t REGION-docker.pkg.dev/PROJECT_ID/REPO/rag-notion-offline:latest .
docker build -f Dockerfile.api -t REGION-docker.pkg.dev/PROJECT_ID/REPO/rag-notion-api:latest .
docker push REGION-docker.pkg.dev/PROJECT_ID/REPO/rag-notion-offline:latest
docker push REGION-docker.pkg.dev/PROJECT_ID/REPO/rag-notion-api:latest
```

## Cloud Run Job (ingestion)

Exécution batch de l’ingestion. À déclencher par Prefect (cron) ou manuellement.

```bash
gcloud run jobs create rag-notion-ingest \
  --image REGION-docker.pkg.dev/PROJECT_ID/REPO/rag-notion-offline:latest \
  --region REGION \
  --set-secrets=NOTION_TOKEN=notion-token:latest,QDRANT_API_KEY=qdrant-key:latest,COHERE_API_KEY=cohere-key:latest \
  --set-env-vars="QDRANT_URL=https://xxx.qdrant.io" \
  --args="--database-id,DATABASE_ID_NOTION" \
  --task-timeout 3600 \
  --max-retries 2
```

Exécution manuelle :

```bash
gcloud run jobs execute rag-notion-ingest --region REGION
```

## Cloud Run Service (API RAG)

```bash
gcloud run deploy rag-notion-api \
  --image REGION-docker.pkg.dev/PROJECT_ID/REPO/rag-notion-api:latest \
  --region REGION \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets=NOTION_TOKEN=notion-token:latest,QDRANT_API_KEY=qdrant-key:latest,COHERE_API_KEY=cohere-key:latest,MISTRAL_API_KEY=mistral-key:latest \
  --set-env-vars="QDRANT_URL=https://xxx.qdrant.io" \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 60
```

## Prefect Cloud

1. Installer les deps : `uv sync -E cloud`
2. Se connecter : `prefect cloud login`
3. Créer un worker ou utiliser des déploiements qui appellent le Cloud Run Job (HTTP) ou exécutent le flow dans Prefect.

Exemple de déploiement du flow en local (pour test) :

```bash
uv run python -m offline.prefect_flow --database-id YOUR_DATABASE_ID
```

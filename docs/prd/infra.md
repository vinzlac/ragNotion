# ANNEXE PRD — Infrastructure & Platform (RAG Notion)

Cette section décrit l’infrastructure technique cible permettant
d’exécuter, opérer et faire évoluer le RAG Notion en production.

Elle est volontairement indépendante des choix d’implémentation
afin de rester durable.

---

# 1. Principes d’architecture infra

## 1.1 Principes directeurs

- Séparation stricte OFFLINE / ONLINE
- Serverless par défaut
- Stateless côté ONLINE
- Compute éphémère pour l’OFFLINE
- Observabilité native (logs, métriques, traces)
- Coût proportionnel à l’usage

---

# 2. Vue d’ensemble de l’infrastructure
        ┌──────────────┐
        │   Utilisateur │
        └──────┬───────┘
               │ HTTP
               ▼
    ┌──────────────────────┐
    │  Cloud Run Service    │
    │  (API RAG ONLINE)     │
    └──────┬───────────────┘
           │
┌──────────┼──────────┐
│          │          │
▼          ▼          ▼
Qdrant     LLM API    Reranker
(Vector)  (Mistral)  (optionnel)


    ┌──────────────────────┐
    │   Prefect Cloud       │
    │  (Orchestration)      │
    └──────┬───────────────┘
           │ trigger
           ▼
    ┌──────────────────────┐
    │   Cloud Run Job       │
    │ (Ingestion OFFLINE)  │
    └─────────┬────────────┘
              ▼
           Notion API


---

# 3. Infrastructure OFFLINE (Build / Ingestion)

## 3.1 Orchestration

### Composant
- Prefect Cloud (plan gratuit)

### Rôles
- Scheduling (cron)
- Retries
- Historique des runs
- Logs par tâche
- Relance manuelle

### Justification
- Orienté pipelines data / ML
- UI claire
- Faible overhead opérationnel

---

## 3.2 Compute batch

### Composant
- Cloud Run Jobs

### Caractéristiques
- Batch serverless
- Container Docker
- Exécution éphémère
- Scale-to-zero natif

### Justification
- Aligné avec ingestion RAG
- Free tier suffisant
- Pas d’instance always-on

---

## 3.3 Stockage & état

### Vector DB
- Qdrant Cloud

### État pipeline
- Checkpoints stockés :
  - dans Qdrant (payload)
  - ou dans un stockage clé/valeur simple

---

# 4. Infrastructure ONLINE (Serve / API)

## 4.1 Compute

### Composant
- Cloud Run Service

### Configuration clé
- min instances = 0 (par défaut)
- autoscaling activé
- stateless
- HTTPS natif

### Justification
- Faible coût
- Scalabilité automatique
- Cohérence avec l’OFFLINE

---

## 4.2 Notion d’instance

- 1 instance = 1 container Docker actif
- Instances créées / détruites dynamiquement
- Cold start possible si aucune instance active

---

## 4.3 Cold start

### Ordres de grandeur
- 1 à 4 secondes typiquement
- Comparable au temps d’un appel LLM

### Décision produit
- Accepté en V1
- Optimisé avant d’activer min instances

---

# 5. Réseau & Connectivité

## 5.1 Flux sortants

Les services doivent pouvoir accéder à :
- Notion API
- Qdrant Cloud
- APIs LLM (Mistral, etc.)

### Contraintes
- HTTPS uniquement
- Timeouts configurés
- Retries contrôlés

---

## 5.2 Sécurité réseau

- Aucun port entrant exposé hors Cloud Run
- Accès API via HTTPS
- Pas de dépendance réseau interne

---

# 6. Observabilité & Monitoring Infra

## 6.1 Logs

### Sources
- Cloud Run logs
- Cloud Run Jobs logs
- Prefect logs

### Contenu
- erreurs
- durées
- trace_id
- version pipeline

---

## 6.2 Métriques

### Métriques clés
- Latence moyenne
- Latence p95
- Cold start ratio
- Erreurs par type
- Coût estimé par requête

---

## 6.3 Tracing

### Option recommandée
- OpenTelemetry
- Export vers Grafana Tempo

### Objectif
- Identifier la brique lente :
  - retrieval
  - reranking
  - LLM
  - réseau

---

# 7. Gestion des secrets

## 7.1 Secrets critiques

- NOTION_API_TOKEN
- QDRANT_API_KEY
- LLM_API_KEY
- PREFECT_API_KEY

---

## 7.2 Stockage

### Options
- Variables d’environnement Cloud Run
- Secret Manager (recommandé en prod)

---

# 8. CI / CD

## 8.1 Déploiement OFFLINE

- Build image ingestion
- Push registry
- Déclenchement Cloud Run Job

---

## 8.2 Déploiement ONLINE

- Build image API
- Push registry
- Déploiement Cloud Run Service
- Rollback simple

---

# 9. Scalabilité & Limites

## 9.1 ONLINE

- Autoscaling horizontal
- Concurrency par instance configurable
- Rate limiting applicatif

---

## 9.2 OFFLINE

- Un job à la fois (par défaut)
- Parallélisation possible à terme

---

# 10. Coûts & Gouvernance

## 10.1 Philosophie de coût

- Payer uniquement quand ça tourne
- Pas de compute idle
- Reranking optionnel

---

## 10.2 Leviers de contrôle

- min instances = 0
- Feature flags
- Limitation top-k
- Batch ingestion incrémentale

---

# 11. Environnements

## Environnements supportés
- dev
- staging
- prod

### Différences
- quotas
- clés API
- fréquence ingestion

---

# 12. Risques techniques identifiés

- Rate limits Notion
- Latence LLM variable
- Cold start visible en démo
- Coûts reranking non maîtrisés

---

## Conclusion Infra

Cette infrastructure :
- est cohérente avec un RAG moderne
- minimise l’overhead opérationnel
- permet une montée en maturité progressive
- évite l’enfermement technologique           
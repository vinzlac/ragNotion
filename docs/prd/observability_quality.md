# MISE À JOUR PRD — Observabilité & Qualité RAG

## Décision structurante : Observabilité en deux phases

### Décision
Le projet adopte une stratégie d’observabilité en deux temps :

- **Phase Build / Design** :
  - Utilisation de LangSmith (plan gratuit)
  - Objectifs : debug, évaluation offline, comparaison de configurations RAG

- **Phase Production** :
  - Migration vers Langfuse
  - Objectifs : monitoring long terme, volumétrie élevée, gouvernance infra

Cette décision vise à :
- accélérer l’itération initiale
- éviter un lock-in prématuré
- maîtriser les coûts
- préparer une exploitation production robuste

---

## Principes d’observabilité retenus

- L’observabilité est considérée comme une **brique produit**, pas un outil annexe
- Toute requête RAG est traçable de bout en bout
- Les métriques doivent couvrir :
  - performance
  - coût
  - qualité
- L’instrumentation doit être **tool-agnostic** (portable LangSmith → Langfuse)

---

## Données de tracing obligatoires (V1)

Chaque requête RAG doit exposer les champs suivants :

- trace_id
- conversation_id
- user_id (ou hash anonymisé)
- rag_version
- prompt_version
- retrieval_config_version
- tags :
  - retrieval
  - mmr
  - rerank
  - llm
  - embedding

---

## Périmètre LangSmith (V1)

LangSmith est utilisé pour :
- inspection détaillée des requêtes
- évaluation offline sur dataset de référence
- comparaison de configurations RAG
- analyse de la qualité des réponses

LangSmith n’est pas utilisé comme :
- solution de monitoring long terme
- source de vérité métrique en production

---

## Périmètre Langfuse (V2)

Langfuse est destiné à :
- monitoring continu
- alerting
- rétention longue
- analyse de dérive qualité
- gouvernance production

La migration est facilitée par :
- conventions de tracing communes
- scripts d’évaluation conservés dans le repository
- métriques définies indépendamment de l’outil

---

# BACKLOG LINEAR — Epic Observabilité & Migration

## 🔷 EPIC OBS-MIG — Observabilité & Migration LangSmith → Langfuse

### Objectif
Garantir une observabilité complète du RAG dès la V1,
tout en préparant une migration fluide vers Langfuse pour la production.

---

### STORY OBS-MIG-1 — Instrumentation LangSmith (V1)
En tant que développeur,  
Je veux instrumenter le pipeline RAG avec LangSmith,  
Afin de tracer chaque requête de bout en bout.

**Critères d’acceptation**
- Toutes les requêtes RAG apparaissent dans LangSmith
- Retrieval, MMR, rerank et LLM sont visibles distinctement
- Les métadonnées standard sont présentes

---

### STORY OBS-MIG-2 — Convention de tracing unifiée
En tant qu’équipe,  
Je veux définir un schéma de tracing commun,  
Afin de faciliter la migration vers Langfuse.

**Critères d’acceptation**
- trace_id cohérent sur toute la requête
- tags normalisés
- versions explicites (RAG, prompt, retrieval)

---

### STORY OBS-MIG-3 — Evals offline avec LangSmith
En tant qu’équipe RAG,  
Je veux exécuter des évaluations offline sur un dataset de référence,  
Afin de comparer les configurations.

**Critères d’acceptation**
- Dataset versionné
- Scores Recall@k et Precision@k disponibles
- Comparaison MMR vs rerank Cohere possible

---

### STORY OBS-MIG-4 — Séparation eval / monitoring
En tant que plateforme,  
Je veux séparer les usages évaluation et monitoring,  
Afin d’éviter un couplage excessif à LangSmith.

---

### STORY OBS-MIG-5 — Préparation migration Langfuse
En tant qu’équipe,  
Je veux documenter la procédure de migration vers Langfuse,  
Afin de passer en production sans refonte.

---

# MÉTRIQUES À SUIVRE DÈS LA V1 (OBLIGATOIRES)

## 1. Métriques de performance

### Latence
- Latence totale (ms)
- Latence moyenne
- Latence p95

### Latence par étape
- retrieval (Qdrant)
- rerank (si activé)
- LLM
- total pipeline

**Objectif V1**
- p95 < 5–6 s

---

## 2. Métriques de coût

### Coût estimé par requête
- tokens input LLM
- tokens output LLM
- coût rerank (si activé)
- coût embeddings (si question embed)

### Agrégations
- coût moyen par requête
- coût journalier estimé

---

## 3. Métriques de retrieval (qualité amont)

- top_k utilisé
- nombre de documents réellement injectés
- score de similarité moyen
- taux de redondance avant / après MMR

---

## 4. Métriques de qualité réponse

### Indicateurs automatiques
- présence de sources (oui/non)
- nombre de sources citées
- réponses "je ne sais pas"

### Flags qualité
- réponse sans source
- réponse trop courte
- réponse trop générique

---

## 5. Métriques d’usage

- nombre de requêtes
- requêtes uniques
- taux d’erreur
- cold start vs warm

---

## 6. Métriques différées (V2+)

- feedback utilisateur (👍/👎)
- dérive des scores retrieval
- comparaison qualité dans le temps
- alerting qualité

---

## Principe directeur

> Une métrique non utilisée pour décider
> est une métrique inutile.

La V1 se concentre volontairement sur :
- peu de métriques
- mais actionnables
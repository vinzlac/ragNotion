# PRD — RAG Notion (Consolidé & Opérationnel)

## Version
v1.0 (consolidée)

## Statut
Ready for implementation

## Périmètre
RAG interne basé sur Notion, avec pipeline OFFLINE + ONLINE,
orienté qualité, observabilité, maîtrise des coûts et évolutivité.

---

# 1. Vision Produit

Construire un **assistant de recherche conversationnel** fiable permettant
d’interroger la connaissance Notion de l’organisation en langage naturel,
avec :
- des réponses sourcées
- une qualité mesurable
- une latence maîtrisée
- une gouvernance claire

---

# 2. Objectifs

## Objectifs principaux
- Réduire drastiquement le temps de recherche d’information dans Notion
- Fournir des réponses factuelles, traçables et non hallucinées
- Rendre la plateforme exploitable en production

## Objectifs secondaires
- Mesurer la qualité dans le temps
- Maîtriser les coûts
- Préparer l’extension à d’autres sources

---

# 3. Utilisateurs

## Utilisateurs finaux
- Collaborateurs internes
- Product / Tech / Ops / Support

## Utilisateurs techniques
- Équipe plateforme / data / ML
- Responsables de l’exploitation

---

# 4. Architecture fonctionnelle

Le système est structuré en **deux pipelines strictement séparées** :

- **Pipeline OFFLINE** : ingestion, préparation, embeddings, indexation, évaluation
- **Pipeline ONLINE** : retrieval, ranking, génération, observabilité

---

# 5. Pipeline OFFLINE — Ingestion & Build Index

## EPIC OFF-1 — Foundations & Setup

### US OFF-1.1 — Initialiser le repository
En tant que développeur,  
Je veux un repository structuré (offline / online séparés),  
Afin de maintenir une architecture claire.

### US OFF-1.2 — Gestion des configurations et secrets
En tant que développeur,  
Je veux une gestion centralisée des variables d’environnement,  
Afin de sécuriser les accès API.

### US OFF-1.3 — Dockerisation
En tant que plateforme,  
Je veux des images Docker reproductibles,  
Afin d’exécuter les pipelines en batch et en service.

---

## EPIC OFF-2 — Ingestion Notion

### US OFF-2.1 — Connexion à l’API Notion
En tant que système,  
Je veux extraire pages et databases Notion,  
Afin d’accéder à la source de vérité.

### US OFF-2.2 — Normalisation du contenu
En tant que pipeline,  
Je veux transformer le contenu Notion en texte exploitable,  
Afin d’éliminer le bruit.

### US OFF-2.3 — Chunking configurable
En tant que RAG,  
Je veux découper les documents en chunks paramétrables (taille, overlap),  
Afin d’optimiser le retrieval.

### US OFF-2.4 — Ingestion incrémentale
En tant que système,  
Je veux détecter les pages modifiées ou supprimées,  
Afin d’éviter les recomputations inutiles.

---

## EPIC OFF-3 — Embeddings & Vectorisation

### US OFF-3.1 — Génération d’embeddings
En tant que pipeline,  
Je veux générer des embeddings par chunk,  
Afin de permettre la recherche sémantique.

### US OFF-3.2 — Modélisation des métadonnées
En tant que RAG,  
Je veux associer chaque chunk à des métadonnées (page_id, titre, date),  
Afin de filtrer et sourcer les réponses.

### US OFF-3.3 — Indexation Qdrant
En tant que système,  
Je veux indexer les embeddings dans Qdrant,  
Afin de permettre un retrieval rapide.

---

## EPIC OFF-4 — Orchestration & Scheduling

### US OFF-4.1 — Orchestration Prefect
En tant qu’opérateur,  
Je veux orchestrer la pipeline avec retries et logs,  
Afin de fiabiliser l’ingestion.

### US OFF-4.2 — Exécution Cloud Run Jobs
En tant que plateforme,  
Je veux exécuter la pipeline en batch serverless,  
Afin de réduire les coûts.

### US OFF-4.3 — Scheduling
En tant qu’équipe,  
Je veux planifier l’ingestion (quotidienne / manuelle),  
Afin de garder l’index à jour.

---

# 6. Pipeline ONLINE — Retrieval & Génération

## EPIC ON-1 — API & Serving

### US ON-1.1 — API /chat
En tant qu’utilisateur,  
Je veux poser une question via une API HTTP,  
Afin d’obtenir une réponse.

### US ON-1.2 — Déploiement Cloud Run Service
En tant que plateforme,  
Je veux un service autoscalé et stateless,  
Afin de servir les requêtes en production.

---

## EPIC ON-2 — Retrieval

### US ON-2.1 — Vector search
En tant que RAG,  
Je veux récupérer les chunks les plus proches sémantiquement,  
Afin de maximiser le recall.

### US ON-2.2 — MMR (diversité)
En tant que RAG,  
Je veux réduire la redondance des chunks,  
Afin d’améliorer la couverture du contexte.

---

## EPIC ON-3 — Reranking (Optionnel)

### US ON-3.1 — Reranking des candidats
En tant que RAG,  
Je veux reclasser les documents par pertinence fine,  
Afin d’améliorer la précision.

### US ON-3.2 — Activation conditionnelle
En tant que plateforme,  
Je veux activer le reranking via configuration,  
Afin de maîtriser les coûts et la latence.

---

## EPIC ON-4 — Génération LLM

### US ON-4.1 — Appel LLM contrôlé
En tant que RAG,  
Je veux générer une réponse uniquement à partir du contexte fourni,  
Afin d’éviter les hallucinations.

### US ON-4.2 — Gestion des sources
En tant qu’utilisateur,  
Je veux voir les sources Notion utilisées,  
Afin de vérifier la réponse.

---

# 7. Prompts, Guardrails & Hallucinations

## EPIC QLT-1 — Prompt Engineering

### US QLT-1.1 — Prompt templates versionnés
En tant qu’équipe,  
Je veux versionner les prompts séparément du code,  
Afin de les améliorer sans redéployer.

### US QLT-1.2 — Paramètres LLM configurables
En tant que RAG,  
Je veux contrôler température, tokens, stop sequences,  
Afin de stabiliser les réponses.

---

## EPIC QLT-2 — Guardrails & Anti-hallucination

### US QLT-2.1 — Réponse conditionnée au contexte
En tant que RAG,  
Je veux répondre “je ne sais pas” si le contexte est insuffisant,  
Afin d’éviter les hallucinations.

### US QLT-2.2 — Détection basique d’hallucinations
En tant que système,  
Je veux détecter des réponses suspectes (sans sources, trop vagues),  
Afin de les tracer.

---

# 8. Observabilité, Métriques & Reporting

## EPIC OBS-1 — Observabilité ONLINE

### US OBS-1.1 — Latence
En tant qu’opérateur,  
Je veux mesurer latence moyenne et p95,  
Afin de suivre l’expérience utilisateur.

### US OBS-1.2 — Coûts
En tant que plateforme,  
Je veux estimer les coûts par requête (LLM, rerank),  
Afin de maîtriser le budget.

---

## EPIC OBS-2 — Qualité & Reporting

### US OBS-2.1 — Métriques de qualité
En tant qu’équipe,  
Je veux mesurer recall, précision et usage des sources,  
Afin d’évaluer le RAG.

### US OBS-2.2 — Reporting périodique
En tant que responsable,  
Je veux recevoir des rapports synthétiques (latence, coût, qualité),  
Afin de piloter le produit.

---

# 9. Évaluation OFFLINE

## EPIC EVAL-1 — Évaluation Retrieval & Réponses

### US EVAL-1.1 — Dataset d’évaluation
En tant qu’équipe,  
Je veux un jeu de questions de référence,  
Afin de comparer les configurations.

### US EVAL-1.2 — Comparaison de configurations
En tant que RAG,  
Je veux comparer MMR, rerank, chunking,  
Afin d’optimiser la qualité.

---

# 10. Asynchronisme & Robustesse (Optionnel / Avancé)

## EPIC OPS-1 — Performance & Résilience

### US OPS-1.1 — API asynchrone
En tant que plateforme,  
Je veux utiliser async/await et la concurrence,  
Afin de réduire la latence.

### US OPS-1.2 — Rate limiting
En tant que système,  
Je veux limiter le trafic par utilisateur,  
Afin de protéger les quotas.

### US OPS-1.3 — Retries & circuit breaker
En tant que RAG,  
Je veux gérer les pannes externes proprement,  
Afin d’éviter les cascades d’erreurs.

---

# 11. Gouvernance & Exploitabilité

## EPIC GOV-1 — Gouvernance

### US GOV-1.1 — Feature flags
En tant qu’équipe,  
Je veux activer/désactiver des fonctionnalités dynamiquement,  
Afin de tester sans risque.

### US GOV-1.2 — Versioning RAG
En tant que plateforme,  
Je veux versionner prompts, embeddings et pipeline,  
Afin d’assurer la traçabilité.

---

# 12. Critères de succès

- Réponses utiles dans >80 % des cas
- p95 < 5–6 secondes
- Coût par requête maîtrisé
- Zéro hallucination critique non détectée
- Pipeline OFFLINE fiable et observable

---

## Conclusion

Ce PRD définit un RAG :
- modulaire
- mesurable
- gouvernable
- prêt pour la production   
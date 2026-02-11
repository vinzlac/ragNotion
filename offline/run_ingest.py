"""
Point d'entrée ingestion (PRD OFF-1, OFF-4).
Usage : python -m offline.run_ingest [--database-id ID] [--page-ids id1,id2]
Charge .env depuis le répertoire racine du projet.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Charger .env à la racine du repo
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from shared.config import NotionSettings, get_rag_settings  # noqa: E402
from offline.pipeline import run_offline_pipeline  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion Notion → Qdrant")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--database-id", type=str, help="ID de la base Notion à indexer")
    g.add_argument("--page-ids", type=str, help="IDs de pages séparés par des virgules")
    parser.add_argument("--incremental", action="store_true", help="Ingestion incrémentale (checkpoint)")
    parser.add_argument("--checkpoint-path", type=str, default=None, help="Chemin du fichier checkpoint")
    args = parser.parse_args()

    notion = NotionSettings()
    rag = get_rag_settings()
    if args.incremental:
        rag = rag.model_copy(update={"incremental": True})
        if args.checkpoint_path:
            rag = rag.model_copy(update={"checkpoint_path": args.checkpoint_path})

    page_ids = None
    database_id = None
    if args.page_ids:
        page_ids = [p.strip() for p in args.page_ids.split(",") if p.strip()]
    else:
        database_id = args.database_id

    result = run_offline_pipeline(
        notion.token,
        page_ids=page_ids,
        database_id=database_id,
        rag_settings=rag,
    )
    logger.info("Résultat: %s", result)


if __name__ == "__main__":
    main()

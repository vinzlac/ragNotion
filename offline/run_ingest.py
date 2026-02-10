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

from dotenv import load_dotenv

load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from shared.config import NotionSettings, get_rag_settings
from offline.pipeline import run_offline_pipeline

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
    args = parser.parse_args()

    notion = NotionSettings()
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
    )
    logger.info("Résultat: %s", result)


if __name__ == "__main__":
    main()

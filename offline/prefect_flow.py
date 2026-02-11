"""
Flow Prefect pour orchestration ingestion (PRD OFF-4.1).
Déclenchement manuel ou par schedule depuis Prefect Cloud.
Usage : uv run python -m offline.prefect_flow [--database-id ID]
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from prefect import flow  # noqa: E402
from shared.config import NotionSettings, get_rag_settings  # noqa: E402
from offline.pipeline import run_offline_pipeline  # noqa: E402


@flow(name="rag-notion-ingest", retries=2, retry_delay_seconds=60)
def ingest_flow(database_id: str | None = None, page_ids: str | None = None) -> dict:
    """
    Exécute la pipeline d'ingestion Notion → Qdrant.
    Soit database_id, soit page_ids (virgules).
    """
    notion = NotionSettings()
    rag = get_rag_settings()
    ids = [p.strip() for p in page_ids.split(",")] if page_ids else None
    result = run_offline_pipeline(
        notion.token,
        database_id=database_id,
        page_ids=ids,
        rag_settings=rag,
    )
    return result


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--database-id", type=str)
    g.add_argument("--page-ids", type=str)
    args = p.parse_args()
    out = ingest_flow(database_id=args.database_id, page_ids=args.page_ids)
    print(out)

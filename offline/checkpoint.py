"""
Checkpoint ingestion (PRD OFF-2.4).
Stocke last_sync_time + page_id → last_edited_time pour détecter modifs/suppressions.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CHECKPOINT_DEFAULT_PATH = "data/ingest_checkpoint.json"


def get_checkpoint_path(configured_path: str | None) -> str:
    if configured_path:
        return configured_path
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", CHECKPOINT_DEFAULT_PATH)


def load_checkpoint(path: str) -> dict[str, Any] | None:
    """Charge le checkpoint depuis un fichier JSON. Retourne None si absent ou invalide."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("Checkpoint invalide ou illisible %s: %s", path, e)
        return None


def save_checkpoint(path: str, *, last_sync_time: str, scope: str, page_last_edited: dict[str, str]) -> None:
    """Enregistre le checkpoint (last_sync_time, scope, page_id → last_edited_time)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_sync_time": last_sync_time,
        "scope": scope,
        "page_last_edited": page_last_edited,
    }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Checkpoint enregistré: %s (%s pages)", path, len(page_last_edited))

"""
Extraction Notion → Documents LangChain (PRD OFF-2.1, OFF-2.2).
Utilise l'API Notion (pages + blocs) et normalise le contenu en texte.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from notion_client import AsyncClient

logger = logging.getLogger(__name__)


async def _query_data_source(
    client: AsyncClient, source_id: str, start_cursor: str | None = None
) -> dict:
    """Interroge une base via data_sources.query (API Notion actuelle)."""
    params: dict[str, Any] = {"data_source_id": source_id}
    if start_cursor:
        params["start_cursor"] = start_cursor
    return await client.data_sources.query(**params)


async def _iterate_block_children(client: AsyncClient, block_id: str):
    """Itère sur tous les blocs enfants (pagination API Notion)."""
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"block_id": block_id}
        if cursor:
            params["start_cursor"] = cursor
        resp = await client.blocks.children.list(**params)
        for block in resp.get("results", []):
            yield block
        cursor = resp.get("next_cursor")
        if not cursor:
            break


def _block_to_text(block: dict[str, Any]) -> str:
    """Extrait le texte d'un bloc Notion (paragraph, heading, list, etc.)."""
    t = block.get("type")
    if t not in block:
        return ""
    content = block[t]
    if not isinstance(content, dict):
        return ""
    rich = content.get("rich_text", [])
    return "".join(r.get("plain_text", "") for r in rich if isinstance(r, dict))


def _get_page_url(page_id: str) -> str:
    """URL Notion d'une page (format standard)."""
    base = page_id.replace("-", "")
    return f"https://www.notion.so/{base}"


async def fetch_page_content(client: AsyncClient, page_id: str) -> tuple[str, str | None]:
    """
    Récupère le titre et tout le contenu texte d'une page (blocs enfants).
    Returns (title, full_text, last_edited_time).
    """
    try:
        page = await client.pages.retrieve(page_id=page_id)
        title = ""
        if "properties" in page and isinstance(page["properties"], dict):
            for prop in page["properties"].values():
                if isinstance(prop, dict) and prop.get("type") == "title":
                    tit = prop.get("title", [])
                    title = "".join(
                        t.get("plain_text", "") for t in tit if isinstance(t, dict)
                    )
                    break
        last_edited = page.get("last_edited_time")

        parts: list[str] = []
        async for block in _iterate_block_children(client, page_id):
            if block.get("type") == "child_page":
                # Sous-page : on pourrait récurser ou ignorer
                continue
            text = _block_to_text(block)
            if text.strip():
                parts.append(text)
        full_text = "\n\n".join(parts)
        return title, full_text, last_edited
    except Exception as e:
        logger.warning("fetch_page_content failed for %s: %s", page_id, e)
        return "", "", None


async def _collect_all_page_ids(
    client: AsyncClient,
    root_page_ids: list[str],
    seen: set[str] | None = None,
) -> list[str]:
    """
    À partir de pages racines, retourne toutes les page_id à indexer :
    les pages elles-mêmes, leurs sous-pages (child_page), et les lignes
    des tables (child_database) incluses dans ces pages.
    """
    if seen is None:
        seen = set()
    result: list[str] = []
    for page_id in root_page_ids:
        if page_id in seen:
            continue
        seen.add(page_id)
        result.append(page_id)
        # Page = base en pleine page (ex. Journal) : les lignes sont des pages
        try:
            cursor = None
            while True:
                resp = await _query_data_source(client, page_id, start_cursor=cursor)
                for item in resp.get("results", []):
                    if item.get("object") == "page":
                        pid = item["id"]
                        if pid not in seen:
                            sub = await _collect_all_page_ids(client, [pid], seen)
                            result.extend(sub)
                cursor = resp.get("next_cursor")
                if not cursor:
                    break
        except Exception:
            pass
        try:
            async for block in _iterate_block_children(client, page_id):
                t = block.get("type")
                if t == "child_page":
                    child_id = block.get("id")
                    if child_id and child_id not in seen:
                        sub = await _collect_all_page_ids(client, [child_id], seen)
                        result.extend(sub)
                elif t == "child_database":
                    db_id = block.get("id")
                    if not db_id:
                        continue
                    try:
                        cursor = None
                        while True:
                            resp = await _query_data_source(client, db_id, start_cursor=cursor)
                            for item in resp.get("results", []):
                                if item.get("object") == "page":
                                    pid = item["id"]
                                    if pid not in seen:
                                        sub = await _collect_all_page_ids(client, [pid], seen)
                                        result.extend(sub)
                            cursor = resp.get("next_cursor")
                            if not cursor:
                                break
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("_collect_all_page_ids %s: %s", page_id, e)
    return result


async def expand_page_ids(notion_token: str, root_page_ids: list[str]) -> list[str]:
    """
    Étend les IDs de pages racines à toutes les pages à indexer
    (sous-pages + lignes des tables incluses). Pour cohérence liste / ingestion.
    """
    client = AsyncClient(auth=notion_token)
    return await _collect_all_page_ids(client, root_page_ids)


async def load_notion_documents(
    notion_token: str,
    *,
    page_ids: list[str] | None = None,
    database_id: str | None = None,
) -> list[Document]:
    """
    Charge des pages Notion en Documents LangChain.
    Soit page_ids (la page + ses sous-pages + les lignes des tables incluses),
    soit database_id (toutes les lignes de la base).
    """
    client = AsyncClient(auth=notion_token)
    ids_to_fetch: list[str] = []

    if page_ids:
        ids_to_fetch = await _collect_all_page_ids(client, list(page_ids))
    elif database_id:
        cursor = None
        while True:
            resp = await _query_data_source(client, database_id, start_cursor=cursor)
            for item in resp.get("results", []):
                if item.get("object") == "page":
                    ids_to_fetch.append(item["id"])
            cursor = resp.get("next_cursor")
            if not cursor:
                break
    else:
        raise ValueError("Fournir page_ids ou database_id")

    documents: list[Document] = []
    for page_id in ids_to_fetch:
        title, full_text, last_edited = await fetch_page_content(client, page_id)
        if not full_text.strip() and not title:
            continue
        text = f"# {title}\n\n{full_text}" if title else full_text
        doc = Document(
            page_content=text,
            metadata={
                "page_id": page_id,
                "title": title,
                "source_url": _get_page_url(page_id),
                "last_edited_time": last_edited or "",
            },
        )
        documents.append(doc)

    return documents


async def list_notion_page_versions(
    notion_token: str,
    *,
    page_ids: list[str] | None = None,
    database_id: str | None = None,
) -> dict[str, str]:
    """
    Retourne page_id → last_edited_time pour détection delta (ingestion incrémentale).
    Ne charge pas le contenu des pages.
    """
    client = AsyncClient(auth=notion_token)
    result: dict[str, str] = {}

    if page_ids:
        for page_id in page_ids:
            try:
                page = await client.pages.retrieve(page_id=page_id)
                if page.get("last_edited_time"):
                    result[page_id] = page["last_edited_time"]
            except Exception as e:
                logger.warning("list_notion_page_versions %s: %s", page_id, e)
        return result

    if database_id:
        cursor = None
        while True:
            resp = await _query_data_source(client, database_id, start_cursor=cursor)
            for item in resp.get("results", []):
                if item.get("object") == "page":
                    pid = item.get("id")
                    last = item.get("last_edited_time")
                    if pid and last:
                        result[pid] = last
            cursor = resp.get("next_cursor")
            if not cursor:
                break
        return result

    raise ValueError("Fournir page_ids ou database_id")

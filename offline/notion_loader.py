"""
Extraction Notion → Documents LangChain (PRD OFF-2.1, OFF-2.2).
Utilise l'API Notion (pages + blocs) et normalise le contenu en texte.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from notion_client import AsyncClient
from notion_client.helpers import iterate_block_children

logger = logging.getLogger(__name__)


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
        async for block in iterate_block_children(client, page_id):
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


async def load_notion_documents(
    notion_token: str,
    *,
    page_ids: list[str] | None = None,
    database_id: str | None = None,
) -> list[Document]:
    """
    Charge des pages Notion en Documents LangChain.
    Soit page_ids est fourni, soit on récupère les pages d'une database_id.
    """
    client = AsyncClient(auth=notion_token)
    ids_to_fetch: list[str] = []

    if page_ids:
        ids_to_fetch = list(page_ids)
    elif database_id:
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"database_id": database_id}
            if cursor:
                params["start_cursor"] = cursor
            resp = await client.databases.query(**params)
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

"""
Liste les pages Notion (et toutes les sous-pages) sans rien indexer.
Usage : uv run python -m offline.list_notion_pages --database-id ID
        uv run python -m offline.list_notion_pages --page-ids id1,id2
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

from notion_client import AsyncClient  # noqa: E402

from shared.config import NotionSettings  # noqa: E402


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


def _get_page_url(page_id: str) -> str:
    base = page_id.replace("-", "")
    return f"https://www.notion.so/{base}"


async def _get_page_title(client: AsyncClient, page_id: str) -> str:
    try:
        page = await client.pages.retrieve(page_id=page_id)
        if "properties" in page and isinstance(page["properties"], dict):
            for prop in page["properties"].values():
                if isinstance(prop, dict) and prop.get("type") == "title":
                    tit = prop.get("title", [])
                    return "".join(t.get("plain_text", "") for t in tit if isinstance(t, dict))
    except Exception:
        pass
    return "(sans titre)"


async def _query_data_source(
    client: AsyncClient, source_id: str, start_cursor: str | None = None
) -> dict:
    """Interroge une base via data_sources.query (API Notion actuelle)."""
    params: dict[str, Any] = {"data_source_id": source_id}
    if start_cursor:
        params["start_cursor"] = start_cursor
    return await client.data_sources.query(**params)


async def _list_pages_recursive(
    client: AsyncClient,
    page_id: str,
    title: str | None,
    depth: int,
    seen: set[str],
    out: list[dict[str, Any]],
) -> None:
    if page_id in seen:
        return
    seen.add(page_id)
    if title is None:
        title = await _get_page_title(client, page_id)
    out.append({
        "page_id": page_id,
        "title": title or "(sans titre)",
        "url": _get_page_url(page_id),
        "depth": depth,
    })
    # Page = base en pleine page (ex. Journal) : les lignes sont des pages qu’on obtient via query
    try:
        row_ids = await _get_database_page_ids(client, page_id)
        for row_id in row_ids:
            await _list_pages_recursive(client, row_id, None, depth + 1, seen, out)
    except Exception:
        pass
    # Blocs enfants : sous-pages et tables inline
    async for block in _iterate_block_children(client, page_id):
        t = block.get("type")
        if t == "child_page":
            child_id = block.get("id")
            if not child_id:
                continue
            child_title = ""
            if "child_page" in block and isinstance(block["child_page"], dict):
                child_title = block["child_page"].get("title") or ""
            await _list_pages_recursive(
                client, child_id, child_title or None, depth + 1, seen, out
            )
        elif t == "child_database":
            db_id = block.get("id")
            if not db_id:
                continue
            try:
                for row_page_id in await _get_database_page_ids(client, db_id):
                    await _list_pages_recursive(
                        client, row_page_id, None, depth + 1, seen, out
                    )
            except Exception:
                pass


async def _get_data_source_ids_from_database(
    client: AsyncClient, database_id: str
) -> list[str]:
    """
    Récupère les data_source_ids d'une base via databases.retrieve.
    Pour une base en pleine page (ex. Journal), database_id = page_id.
    """
    try:
        db = await client.databases.retrieve(database_id=database_id)
        sources = db.get("data_sources") or []
        return [s["id"] for s in sources if isinstance(s, dict) and s.get("id")]
    except Exception:
        return []


async def _get_database_page_ids(client: AsyncClient, source_id: str) -> list[str]:
    """
    Retourne tous les page_id (lignes) d'une base.
    source_id peut être :
    - un data_source_id (utilisé directement avec data_sources.query)
    - un database_id (base en pleine page) : on résout via databases.retrieve → data_sources
    """
    # Essayer d'abord comme database_id (base en pleine page)
    ds_ids = await _get_data_source_ids_from_database(client, source_id)
    if ds_ids:
        ids: list[str] = []
        for ds_id in ds_ids:
            cursor: str | None = None
            while True:
                resp = await _query_data_source(client, ds_id, start_cursor=cursor)
                for item in resp.get("results", []):
                    if item.get("object") == "page":
                        ids.append(item["id"])
                cursor = resp.get("next_cursor")
                if not cursor:
                    break
        return ids
    # Sinon traiter comme data_source_id
    cursor = None
    ids = []
    while True:
        resp = await _query_data_source(client, source_id, start_cursor=cursor)
        for item in resp.get("results", []):
            if item.get("object") == "page":
                ids.append(item["id"])
        cursor = resp.get("next_cursor")
        if not cursor:
            break
    return ids


async def _debug_page(client: AsyncClient, page_id: str) -> None:
    """Affiche les blocs et tente databases.retrieve + query pour diagnostiquer."""
    print(f"\n--- Debug page {page_id} ---\n")
    print("Blocs enfants:")
    async for block in _iterate_block_children(client, page_id):
        t = block.get("type")
        bid = block.get("id", "")
        extra = ""
        if t == "child_database" and "child_database" in block:
            extra = f" title={block['child_database'].get('title', '')}"
        print(f"  type={t} id={bid}{extra}")
    print("\nTentative databases.retrieve(page_id):")
    try:
        db = await client.databases.retrieve(database_id=page_id)
        ds_list = db.get("data_sources") or []
        print(f"  OK → {len(ds_list)} data_source(s)")
        for ds in ds_list:
            print(f"    - {ds.get('name', '?')}: {ds.get('id', '')}")
    except Exception as e:
        print(f"  ÉCHEC: {e}")
    print("\nTentative _get_database_page_ids (résolution database→data_sources):")
    try:
        ids = await _get_database_page_ids(client, page_id)
        print(f"  OK → {len(ids)} pages")
        for i, pid in enumerate(ids[:5]):
            print(f"    {i+1}. {pid}")
        if len(ids) > 5:
            print(f"    ... et {len(ids)-5} autres")
    except Exception as e:
        print(f"  ÉCHEC: {e}")


async def list_from_database(client: AsyncClient, source_id: str) -> list[dict[str, Any]]:
    """Liste toutes les pages d'une base. ID = database_id (URL) ou data_source_id."""
    root_ids = await _get_database_page_ids(client, source_id)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_id in root_ids:
        await _list_pages_recursive(client, page_id, None, 0, seen, out)
    return out


async def list_from_page_ids(client: AsyncClient, page_ids: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page_id in page_ids:
        await _list_pages_recursive(client, page_id, None, 0, seen, out)
    return out


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Lister les pages Notion (avec sous-pages)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--database-id", type=str, help="ID de la base Notion")
    g.add_argument("--page-ids", type=str, help="IDs de pages racines (séparés par des virgules)")
    p.add_argument("--json", action="store_true", help="Sortie JSON au lieu de l’arbre")
    p.add_argument("--debug", action="store_true", help="Afficher structure blocs + query pour diagnostiquer")
    args = p.parse_args()

    notion = NotionSettings()
    client = AsyncClient(auth=notion.token)

    if args.debug:
        target = args.database_id or (args.page_ids.split(",")[0].strip() if args.page_ids else "")
        if target:
            asyncio.run(_debug_page(client, target))
        else:
            print("--debug requiert --database-id ou --page-ids")
        return

    try:
        if args.database_id:
            pages = asyncio.run(list_from_database(client, args.database_id))
        else:
            page_ids = [x.strip() for x in args.page_ids.split(",") if x.strip()]
            pages = asyncio.run(list_from_page_ids(client, page_ids))
    except Exception as e:
        if getattr(e, "status", None) == 404:
            print(
                "Erreur 404 : base introuvable ou non partagée avec l’intégration.\n"
                "→ Utilisez une page partagée avec l’intégration et son ID avec --page-ids.\n"
                "  Ex. : just list-pages-by-ids \"040d3dc7e3dc49bc917be8597e647309\"\n"
                "  (ID = partie de l’URL Notion avant ?v=)\n"
                "→ Ou partagez la base : menu ••• > Add connections > votre intégration.",
                file=sys.stderr,
            )
        raise

    if args.json:
        import json
        print(json.dumps(pages, ensure_ascii=False, indent=2))
        return

    print(f"Total : {len(pages)} page(s)\n")
    for p in pages:
        indent = "  " * p["depth"]
        print(f"{indent}{p['title']}")
        print(f"{indent}  id: {p['page_id']}")
        print(f"{indent}  {p['url']}\n")


if __name__ == "__main__":
    main()

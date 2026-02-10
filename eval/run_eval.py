"""
Script d'évaluation RAG sur un dataset de questions (PRD EVAL-1.1, EVAL-1.2).
Usage : uv run python -m eval.run_eval [--dataset eval/dataset.json] [--output results.json]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")

from api.rag_chain import build_rag_chain


def load_dataset(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="eval/dataset.json", help="Fichier dataset JSON")
    p.add_argument("--output", default="eval/results.json", help="Fichier résultats JSON")
    args = p.parse_args()

    dataset = load_dataset(args.dataset)
    chain = build_rag_chain()
    results = []
    for item in dataset:
        q = item.get("question", "")
        qid = item.get("id", "")
        if not q:
            continue
        out = chain.invoke(q)
        results.append({
            "id": qid,
            "question": q,
            "answer_length": len(out.answer),
            "sources_count": len(out.sources),
            "rag_version": out.rag_version,
        })
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Évaluation terminée: {len(results)} questions → {args.output}")


if __name__ == "__main__":
    main()

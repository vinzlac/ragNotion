"""
Compare deux runs d'évaluation (PRD EVAL-1.2).
Usage : uv run python -m eval.compare_results results_a.json results_b.json
"""
from __future__ import annotations

import json
import sys

def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: compare_results.py <results_a.json> <results_b.json>")
        sys.exit(1)
    path_a, path_b = sys.argv[1], sys.argv[2]
    with open(path_a, encoding="utf-8") as f:
        a = json.load(f)
    with open(path_b, encoding="utf-8") as f:
        b = json.load(f)
    by_id_a = {r["id"]: r for r in a}
    by_id_b = {r["id"]: r for r in b}
    ids = sorted(set(by_id_a) | set(by_id_b))
    print("id\tquestion\tanswer_len_a\tanswer_len_b\tsources_a\tsources_b")
    for qid in ids:
        ra = by_id_a.get(qid, {})
        rb = by_id_b.get(qid, {})
        q = ra.get("question", rb.get("question", ""))[:40]
        print(f"{qid}\t{q}\t{ra.get('answer_length', 0)}\t{rb.get('answer_length', 0)}\t{ra.get('sources_count', 0)}\t{rb.get('sources_count', 0)}")
    avg_sources_a = sum(r.get("sources_count", 0) for r in a) / len(a) if a else 0
    avg_sources_b = sum(r.get("sources_count", 0) for r in b) / len(b) if b else 0
    print(f"\nAvg sources A: {avg_sources_a:.1f}  B: {avg_sources_b:.1f}")


if __name__ == "__main__":
    main()

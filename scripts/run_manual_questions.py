#!/usr/bin/env python3
"""Exécute les questions de eval/questions.txt et ajoute les sorties à eval/manual_runs.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.retrieval.rag import answer_question  # noqa: E402


def _iter_questions(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def main() -> int:
    p = argparse.ArgumentParser(
        description="Lit eval/questions.txt et enregistre les réponses RAG en JSONL.",
    )
    p.add_argument(
        "--questions",
        type=Path,
        default=ROOT / "eval" / "questions.txt",
        help="Fichier texte, une question par ligne.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "eval" / "manual_runs.jsonl",
        help="Fichier JSONL append.",
    )
    p.add_argument(
        "--collection",
        default="technical_docs",
        help="Collection Chroma.",
    )
    args = p.parse_args()

    if not args.questions.is_file():
        print(f"Fichier introuvable: {args.questions}", file=sys.stderr)
        return 1

    qs = _iter_questions(args.questions)
    if not qs:
        print("Aucune question (lignes vides ou # uniquement).", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as f:
        for q in qs:
            ts = datetime.now(timezone.utc).isoformat()
            try:
                result = answer_question(
                    q,
                    args.collection,
                    include_chunk_details=True,
                )
                row = {
                    "ts": ts,
                    "question": q,
                    "answer": result.answer,
                    "sources": result.sources,
                    "used_reranking": result.used_reranking,
                    "chunk_details": result.chunk_details,
                }
            except Exception as e:
                row = {
                    "ts": ts,
                    "question": q,
                    "error": str(e),
                }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps(row, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

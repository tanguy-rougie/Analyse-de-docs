"""CLI: python -m src.retrieval --collection technical_docs \"votre question\""""

from __future__ import annotations

from src.env import load_env

load_env()

import argparse
import json
import sys

from src.retrieval.rag import answer_question


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="RAG query against a Chroma collection.")
    p.add_argument("question", nargs="?", help="Question en langage naturel.")
    p.add_argument(
        "--collection",
        default="technical_docs",
        help="Nom de la collection Chroma (défaut: technical_docs).",
    )
    p.add_argument(
        "-q",
        "--question-arg",
        dest="question_opt",
        help="Question (alternative au mot positionnel, utile sous Windows).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Inclut des aperçus de chunks et scores cosinus dans le JSON.",
    )
    args = p.parse_args(argv)

    q = args.question_opt or args.question
    if not q or not str(q).strip():
        p.print_help()
        print("\nErreur: fournissez une question.", file=sys.stderr)
        return 1

    try:
        result = answer_question(
            str(q).strip(),
            args.collection,
            include_chunk_details=args.verbose,
        )
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
        return 1

    out = {
        "answer": result.answer,
        "sources": result.sources,
        "used_reranking": result.used_reranking,
    }
    if result.chunk_details is not None:
        out["chunk_details"] = result.chunk_details
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

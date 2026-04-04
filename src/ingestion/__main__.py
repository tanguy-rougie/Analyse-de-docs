"""CLI: python -m src.ingestion --input-dir ./Documents --collection technical_docs"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.ingestion.config import IngestionConfig
from src.ingestion.pipeline import ingest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest PDFs: extract text, chunk, embed, store in ChromaDB.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing .pdf files (non-recursive).",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="technical_docs",
        help="Chroma collection name.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the collection before adding documents.",
    )
    args = parser.parse_args(argv)

    # Ensure repo-root imports work when run as python -m src.ingestion
    cfg = IngestionConfig.from_env()
    try:
        summary = ingest(
            args.input_dir,
            args.collection,
            reset=args.reset,
            config=cfg,
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

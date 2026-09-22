"""Load text from PDF files with per-page metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from pypdf import PdfReader


@dataclass
class PageDocument:
    """One page of text plus metadata for chunking and retrieval."""

    content: str
    source: str
    page: int


def load_pdf(path: Path) -> list[PageDocument]:
    """Extract text per page from a single PDF file."""
    path = path.resolve()
    reader = PdfReader(str(path))
    docs: list[PageDocument] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue
        docs.append(PageDocument(content=text, source=str(path), page=i))
    return docs


def iter_pdfs_in_dir(input_dir: Path) -> Iterator[Path]:
    """Yield sorted PDF paths under input_dir (non-recursive)."""
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {input_dir}")
    for p in sorted(input_dir.glob("*.pdf")):
        if p.is_file():
            yield p


def load_all_pdfs(input_dir: Path) -> list[PageDocument]:
    """Load every *.pdf in input_dir into page-level documents."""
    all_pages: list[PageDocument] = []
    for pdf_path in iter_pdfs_in_dir(input_dir):
        all_pages.extend(load_pdf(pdf_path))
    return all_pages

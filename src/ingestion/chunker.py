"""Token-aware fixed-size chunking aligned with the embedding model tokenizer."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from src.ingestion.pdf_loader import PageDocument


def _effective_chunk_params(
    tokenizer: PreTrainedTokenizerBase,
    requested_size: int,
    requested_overlap: int,
) -> tuple[int, int]:
    """Cap chunk size by the tokenizer's model max length when HF sets a real limit."""
    max_len = getattr(tokenizer, "model_max_length", None)
    if max_len is None or max_len > 8192:
        size = requested_size
    else:
        size = min(requested_size, max_len)
    if size < 1:
        size = 1
    overlap = min(requested_overlap, size - 1) if size > 1 else 0
    return size, max(0, overlap)


def chunk_pages(
    pages: list[PageDocument],
    model_name: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[Document]:
    """
    Split page-level text into chunks up to chunk_size tokens (embedding tokenizer).
    Overlap is in tokens. Metadata: source, page, file_stem, chunk_index.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    eff_size, eff_overlap = _effective_chunk_params(
        tokenizer, chunk_size, chunk_overlap
    )

    def len_tokens(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=eff_size,
        chunk_overlap=eff_overlap,
        length_function=len_tokens,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    lang_docs = [
        Document(
            page_content=p.content,
            metadata={
                "source": p.source,
                "page": p.page,
                "file_stem": Path(p.source).stem,
            },
        )
        for p in pages
    ]
    splits = splitter.split_documents(lang_docs)

    per_page_counter: dict[tuple[str, int], int] = defaultdict(int)
    for doc in splits:
        key = (doc.metadata["source"], doc.metadata["page"])
        idx = per_page_counter[key]
        per_page_counter[key] = idx + 1
        doc.metadata = {
            **doc.metadata,
            "chunk_index": idx,
        }
    return splits

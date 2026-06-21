from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    document_id: str
    source_id: str
    title: str
    text: str
    metadata: dict[str, Any]
    hash: str


def chunk_document(
    *,
    document_id: str,
    source_id: str,
    title: str,
    text: str,
    metadata: dict[str, Any],
    max_chars: int = 1800,
    overlap_chars: int = 220,
) -> list[TextChunk]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    for chunk_text in _split_text(normalized, max_chars=max_chars, overlap_chars=overlap_chars):
        content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
        chunks.append(
            TextChunk(
                chunk_id=f"chk_{uuid4().hex[:16]}",
                document_id=document_id,
                source_id=source_id,
                title=title,
                text=chunk_text,
                metadata=metadata,
                hash=content_hash,
            )
        )
    return chunks


def normalize_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines)


def _split_text(text: str, *, max_chars: int, overlap_chars: int) -> Iterable[str]:
    paragraphs = text.split("\n")
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                yield current
                current = ""
            yield from _split_long_paragraph(paragraph, max_chars=max_chars, overlap_chars=overlap_chars)
            continue

        next_text = f"{current}\n{paragraph}".strip() if current else paragraph
        if len(next_text) <= max_chars:
            current = next_text
            continue

        if current:
            yield current
        current = _with_overlap(current, paragraph, overlap_chars)

    if current:
        yield current


def _split_long_paragraph(paragraph: str, *, max_chars: int, overlap_chars: int) -> Iterable[str]:
    start = 0
    while start < len(paragraph):
        end = min(start + max_chars, len(paragraph))
        yield paragraph[start:end].strip()
        if end == len(paragraph):
            break
        start = max(0, end - overlap_chars)


def _with_overlap(previous: str, paragraph: str, overlap_chars: int) -> str:
    if not previous:
        return paragraph
    overlap = previous[-overlap_chars:].strip()
    return f"{overlap}\n{paragraph}".strip()


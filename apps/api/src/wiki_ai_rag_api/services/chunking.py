from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, uuid5


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

    metadata = dict(metadata)
    chunks: list[TextChunk] = []
    chunk_texts = list(_split_text(normalized, max_chars=max_chars, overlap_chars=overlap_chars))
    metadata_identity = json.dumps(
        {
            key: metadata.get(key)
            for key in ("section", "page", "record_id", "timestamp")
            if metadata.get(key) is not None
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    chunk_ids = [
        "chk_"
        + uuid5(
            NAMESPACE_URL,
            (
                f"{source_id}:{document_id}:{metadata_identity}:{index}:"
                f"{hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()}"
            ),
        ).hex[:16]
        for index, chunk_text in enumerate(chunk_texts)
    ]
    for index, chunk_text in enumerate(chunk_texts):
        content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
        chunk_metadata = {
            **metadata,
            "chunk_index": index,
            "chunk_count": len(chunk_texts),
            "token_estimate": _estimate_tokens(chunk_text),
            "split_strategy": "semantic_paragraph",
            "previous_chunk_id": chunk_ids[index - 1] if index > 0 else None,
            "next_chunk_id": chunk_ids[index + 1] if index < len(chunk_ids) - 1 else None,
        }
        if "parent_section" not in chunk_metadata:
            chunk_metadata["parent_section"] = chunk_metadata.get("section")
        chunks.append(
            TextChunk(
                chunk_id=chunk_ids[index],
                document_id=document_id,
                source_id=source_id,
                title=title,
                text=chunk_text,
                metadata=chunk_metadata,
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


def _estimate_tokens(text: str) -> int:
    # Rough, language-agnostic estimate good enough for chunk diagnostics.
    return max(1, len(text) // 4)

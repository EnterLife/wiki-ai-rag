from wiki_ai_rag_api.services.chunking import chunk_document


def test_chunk_document_adds_navigation_and_diagnostic_metadata() -> None:
    chunks = chunk_document(
        document_id="doc_1",
        source_id="src_1",
        title="Guide",
        text="A" * 220 + "\n\n" + "B" * 220 + "\n\n" + "C" * 220,
        metadata={"section": "Setup"},
        max_chars=260,
        overlap_chars=20,
    )

    assert len(chunks) == 3
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["chunk_count"] == 3
    assert chunks[0].metadata["next_chunk_id"] == chunks[1].chunk_id
    assert chunks[1].metadata["previous_chunk_id"] == chunks[0].chunk_id
    assert chunks[1].metadata["next_chunk_id"] == chunks[2].chunk_id
    assert chunks[2].metadata["previous_chunk_id"] == chunks[1].chunk_id
    assert chunks[2].metadata["next_chunk_id"] is None
    assert chunks[0].metadata["parent_section"] == "Setup"
    assert chunks[0].metadata["token_estimate"] > 0
    assert chunks[0].metadata["split_strategy"] == "semantic_paragraph"

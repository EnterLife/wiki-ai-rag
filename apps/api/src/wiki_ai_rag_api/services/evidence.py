from wiki_ai_rag_api.schemas.evidence import EvidenceChunk
from wiki_ai_rag_api.services.vector_store import VectorStore, get_vector_store


class EvidenceService:
    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()

    def get_chunk(self, chunk_id: str) -> EvidenceChunk | None:
        chunk = self.vector_store.get_chunk(chunk_id)
        if chunk is None:
            return None
        return EvidenceChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_id=chunk.source_id,
            title=chunk.title,
            text=chunk.text,
            metadata=chunk.metadata,
            score=chunk.score,
        )


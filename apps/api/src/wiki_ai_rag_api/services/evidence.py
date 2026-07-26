from wiki_ai_rag_api.schemas.evidence import EvidenceChunk
from wiki_ai_rag_api.services.access import AccessContext, SYSTEM_ACCESS_CONTEXT
from wiki_ai_rag_api.services.vector_store import VectorStore, get_vector_store
from wiki_ai_rag_api.storage.base import MetadataStore
from wiki_ai_rag_api.storage.factory import get_metadata_store


class EvidenceService:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        store: MetadataStore | None = None,
    ) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.store = store or get_metadata_store()

    def get_chunk(
        self,
        chunk_id: str,
        access_context: AccessContext = SYSTEM_ACCESS_CONTEXT,
    ) -> EvidenceChunk | None:
        chunk = self.vector_store.get_chunk(chunk_id)
        if chunk is None:
            return None
        source = self.store.get_source(chunk.source_id)
        if (
            source is None
            or not source.get("enabled", True)
            or not access_context.can_access_source(source)
        ):
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

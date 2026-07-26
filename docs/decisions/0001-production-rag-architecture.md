# ADR 0001: Production RAG architecture

## Status

Accepted.

## Decision

- PostgreSQL is the source of truth for sources, jobs and audit events.
- Qdrant stores searchable chunks and citation payloads.
- Redis and Celery execute indexing outside API requests.
- Every source carries access groups. Retrieval filters disabled and unauthorized
  sources before querying the vector store.
- Retrieval combines dense similarity and BM25 rankings with weighted reciprocal
  rank fusion. An optional HTTP reranker processes the candidate set.
- LLM source content is treated as untrusted data. Production responses use
  structured claims and validated citation ids.
- Full replacement uploads new Qdrant points before stale points are deleted.
  Embedding-model migrations use a second collection and an atomic alias switch.

## Consequences

The local JSON, hashing and extractive providers remain available for development.
`APP_ENV=production` rejects those providers and other unsafe defaults.

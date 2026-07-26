# Wiki AI RAG

Wiki AI RAG is a FastAPI + React retrieval-augmented generation service for grounded
answers over internal knowledge bases, databases, documents, transcripts and wiki-like
exports.

Core rule:

```text
No source - no answer.
```

The system indexes connected sources, retrieves relevant evidence, asks an LLM to
answer only from that evidence, and returns citations that can be inspected through
the API.

## Current Status

The project has a working MVP plus a first RAG v2 slice:

- FastAPI backend with source management, indexing, retrieval, questions, evidence,
  metrics, audit, retrieval evaluation and opt-in agentic ask endpoints.
- React + TypeScript + Vite frontend with chat UI, source filters and source admin UI.
- Implemented source connectors: filesystem, PostgreSQL and SQLite.
- Supported file parsing: Markdown, TXT, PDF, DOCX, HTML, CSV and JSON.
- Vector stores: local JSON vector store for lightweight development and Qdrant for
  Docker-backed validation.
- Metadata stores: local JSON for development and PostgreSQL for production.
- Embeddings: deterministic local hashing provider and OpenAI-compatible embeddings
  provider.
- LLM providers: local extractive provider, Ollama and OpenAI-compatible chat
  completions.
- RAG v3 retrieval: structure-aware chunking, BM25 + dense reciprocal-rank fusion,
  relevance threshold, retrieval evaluation and local or HTTP reranking.
- Production controls: OIDC/JWKS authentication, source-group ACLs, Celery indexing,
  deterministic chunk ids and strict structured answer validation.
- Optional features: short-term conversation memory and an opt-in tool-oriented
  agentic ask endpoint.

## Repository Layout

```text
apps/
  api/        FastAPI backend
  web/        React frontend
docs/         Architecture decision records
infra/        Docker Compose and environment examples
packages/     Reserved for future shared packages
scripts/      Windows and Linux helper scripts
```

`README.md` is the canonical project document. `docs/decisions` keeps architecture
decision records that are useful as project history.

For company rollout order, acceptance gates and required organizational inputs, see
[`docs/company-rag-plan.md`](docs/company-rag-plan.md) and
[`docs/production-rollout.md`](docs/production-rollout.md).

Important backend modules:

- `apps/api/src/wiki_ai_rag_api/main.py` - FastAPI app entry point.
- `apps/api/src/wiki_ai_rag_api/api/v1` - HTTP routers.
- `apps/api/src/wiki_ai_rag_api/connectors` - source connectors.
- `apps/api/src/wiki_ai_rag_api/services` - indexing, retrieval, RAG, LLM, vector store,
  evaluation and tool orchestration.
- `apps/api/tests` - backend unit and opt-in integration tests.

## Architecture

Main RAG flow:

```text
Frontend
  -> Backend API
  -> RAG Orchestrator
  -> Retrieval Service
  -> Vector Store
  -> LLM Service
  -> Answer + Citations
```

Indexing flow:

```text
Source config
  -> Connector
  -> Parser
  -> Normalized document
  -> Semantic-ish chunking
  -> Embeddings
  -> Vector store
  -> Indexing job status
```

Retrieval v2 flow:

```text
Question
  -> Embedding
  -> Vector candidate search
  -> Keyword candidate scoring
  -> Hybrid score fusion
  -> Optional reranker
  -> Context pack
  -> Grounded LLM
```

Agentic flow is opt-in and currently exposes an internal `search_knowledge_base` tool.
It does not replace the normal `/ask` path.

## Requirements

- Python 3.11+
- Node.js 20+
- Docker Desktop or another Docker runtime for PostgreSQL and Qdrant integration
- PostgreSQL 16 and Qdrant when using the local Docker infrastructure

## Quick Start

Start infrastructure:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

Start the containerized API, worker and web UI as well:

```powershell
docker compose -f infra/docker-compose.yml --profile app up -d --build
```

Create and run the backend:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn wiki_ai_rag_api.main:app --reload
```

Create and run the frontend:

```powershell
cd apps/web
npm install
npm run dev
```

Default URLs:

- API: `http://127.0.0.1:8000/api/v1/health`
- Frontend: `http://127.0.0.1:5173`
- Qdrant dashboard: `http://localhost:6333/dashboard`

For a lightweight backend without Docker services, keep:

```text
VECTOR_STORE_PROVIDER=json
EMBEDDINGS_PROVIDER=hashing
LLM_PROVIDER=extractive
```

For Qdrant-backed retrieval:

```text
VECTOR_STORE_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_TRUST_ENV=false
```

`QDRANT_TRUST_ENV=false` is important on Windows/Docker Desktop when local proxy or
relay settings cause Python HTTP clients to see `503` while browser/curl checks still
work.

## Helper Scripts

Windows scripts live in `scripts/*.bat` and are intended for local development from
Command Prompt, PowerShell or Explorer:

```powershell
scripts\setup-dev.bat
scripts\start-project.bat
```

Useful Windows entry points:

- `scripts\setup-api-venv.bat` - create `apps/api/.venv` and install backend
  development dependencies.
- `scripts\setup-web.bat` - install frontend dependencies.
- `scripts\setup-dev.bat` - run both setup steps.
- `scripts\start-infra.bat` - start PostgreSQL and Qdrant through Docker Compose.
- `scripts\start-api.bat` - run the FastAPI backend with reload.
- `scripts\start-web.bat` - run the Vite frontend dev server.
- `scripts\start-project.bat` - start infrastructure, API and frontend in separate
  Windows terminals.
- `scripts\check-project.bat` - run backend and frontend validation checks.

Linux server scripts live in `scripts/*.sh`. On a fresh server, install Python 3.11+,
Node.js 20+ and Docker first, then run:

```bash
chmod +x scripts/*.sh
scripts/setup-server.sh
cp infra/.env.example .env
# edit .env for the server environment
scripts/start-server.sh
```

Useful server entry points:

- `scripts/setup-api-venv.sh` - create `apps/api/.venv` and install backend
  development dependencies.
- `scripts/setup-web.sh` - install frontend dependencies.
- `scripts/setup-server.sh` - prepare backend and frontend runtime dependencies.
- `scripts/start-infra.sh` - start PostgreSQL and Qdrant through Docker Compose.
- `scripts/start-api.sh` - run the FastAPI backend.
- `scripts/start-web.sh` - build the frontend and run Vite preview.
- `scripts/start-server.sh` - start infrastructure, API and frontend in the background.
- `scripts/stop-server.sh` - stop background API and frontend processes started by
  `start-server.sh`.
- `scripts/check-project.sh` - run backend and frontend validation checks.

Server logs and PID files are written under `runtime/`, which is ignored by Git.

## Environment Variables

The example environment lives in `infra/.env.example`.

Core settings:

```text
STORAGE_PATH=storage/wiki_ai_rag_state.json
VECTOR_STORE_PROVIDER=json
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=wiki_ai_rag_chunks
QDRANT_TRUST_ENV=false
EMBEDDING_DIMENSION=256
API_CORS_ORIGINS=http://localhost:5173
```

Embeddings:

```text
EMBEDDINGS_PROVIDER=hashing
EMBEDDINGS_BASE_URL=http://localhost:1234/v1
EMBEDDINGS_MODEL=text-embedding-3-small
# EMBEDDINGS_API_KEY=
```

LLM:

```text
LLM_PROVIDER=extractive
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1
# LLM_API_KEY=
```

Retrieval and RAG v2:

```text
RETRIEVAL_VECTOR_WEIGHT=0.65
RETRIEVAL_KEYWORD_WEIGHT=0.35
RETRIEVAL_KEYWORD_CANDIDATE_LIMIT=200
RETRIEVAL_CANDIDATES_TOP_K=50
RERANKER_PROVIDER=none
CONVERSATION_MEMORY_ENABLED=false
CONVERSATION_MEMORY_MAX_TURNS=6
AGENTIC_RAG_ENABLED=false
AGENTIC_MAX_STEPS=3
```

Security and operations:

```text
AUTH_ENABLED=false
# USER_API_KEY=
# ADMIN_API_KEY=
# CREDENTIALS_ENCRYPTION_KEY=
RATE_LIMIT_ENABLED=false
QUESTION_RATE_LIMIT_PER_MINUTE=60
ENABLE_SCHEDULER=false
SCHEDULER_POLL_SECONDS=60
LOG_LEVEL=INFO
LOG_QUESTION_TEXT=false
```

When `AUTH_ENABLED=true`, `/ask` accepts `X-User-API-Key` or `X-Admin-API-Key`.
Admin endpoints require `X-Admin-API-Key`.

## Supported Sources

Implemented source types:

- `filesystem`
- `postgresql`
- `sqlite`

Unsupported source types are rejected by request validation.

Filesystem source:

```json
{
  "name": "Product Wiki",
  "type": "filesystem",
  "config": {
    "path": "/data/wiki",
    "indexing": {
      "max_chars": 1800,
      "overlap_chars": 220
    }
  },
  "enabled": true,
  "schedule": {
    "mode": "manual"
  }
}
```

PostgreSQL source:

```json
{
  "name": "Knowledge DB",
  "type": "postgresql",
  "config": {
    "host": "localhost",
    "port": 5432,
    "database": "knowledge_base",
    "username": "rag_user",
    "password": "secret",
    "tables": [
      {
        "name": "public.pages",
        "id_field": "id",
        "title_field": "title",
        "text_fields": ["body"],
        "metadata_fields": ["url", "section", "updated_at"],
        "limit": 1000
      }
    ]
  },
  "enabled": true,
  "schedule": {
    "mode": "manual"
  }
}
```

SQLite source:

```json
{
  "name": "SQLite Wiki",
  "type": "sqlite",
  "config": {
    "database_path": "/data/wiki.sqlite",
    "tables": [
      {
        "name": "pages",
        "id_field": "id",
        "title_field": "title",
        "text_fields": ["body"],
        "metadata_fields": ["url"]
      }
    ]
  },
  "enabled": true,
  "schedule": {
    "mode": "manual"
  }
}
```

Sensitive source fields are encrypted when `CREDENTIALS_ENCRYPTION_KEY` is configured.
Credentials are not returned from read APIs, logged or sent to the LLM.

## Indexing

The indexing pipeline:

1. Read documents through a connector.
2. Parse files or database rows into normalized documents.
3. Normalize text.
4. Split text into chunks.
5. Create embeddings.
6. Store chunks, embeddings and metadata in the selected vector store.
7. Update indexing job status and source statistics.

Chunk metadata includes:

- `chunk_id`
- `document_id`
- `source_id`
- `title`
- `section`, `page`, `url`, `path`, `timestamp`, `record_id` when available
- `chunk_index`
- `chunk_count`
- `token_estimate`
- `parent_section`
- `previous_chunk_id`
- `next_chunk_id`
- `split_strategy`

Source-level indexing config:

```json
{
  "indexing": {
    "max_chars": 1800,
    "overlap_chars": 220
  }
}
```

One bad document does not fail the whole indexing job. The job can finish as
`completed` with `failed_documents > 0` and an error summary.

## Retrieval, Reranking and Evaluation

Retrieval uses hybrid scoring:

```text
combined_score = vector_weight * vector_score + keyword_weight * keyword_score
```

Keyword scoring helps with exact identifiers such as error codes, ticket numbers,
table names and short policy names.

Reranker providers:

- `none` - default, keeps retrieval order.
- `keyword` - deterministic local reranker for smoke and evaluation scenarios.
- `http` - external BGE/Jina-compatible HTTP reranker.

Retrieval evaluation endpoint:

```http
POST /api/v1/evaluation/retrieval
```

Request:

```json
{
  "top_k": 10,
  "items": [
    {
      "question": "How is OpenVPN configured?",
      "expected_document_ids": ["vpn_guide.md"],
      "expected_chunk_ids": [],
      "source_ids": ["src_it_wiki"]
    }
  ]
}
```

Metrics returned:

- `recall_at_5`
- `recall_at_10`
- `mrr`
- `ndcg_at_10`

Use this after changing chunking, embeddings, hybrid weights, vector stores or reranker
settings.

## Answer Policy

The LLM must answer only from retrieved context. If context is missing or insufficient,
the response must be:

```text
В базе знаний нет достаточной информации для ответа на этот вопрос.
```

Forbidden behavior:

- using external model knowledge;
- inventing facts;
- making unsupported assumptions;
- answering without retrieved evidence;
- exposing credentials, connection strings or source config secrets.

Every important claim must include citation markers such as `[1]`. Answers without
citation markers are rejected as insufficient context.

`/ask` returns structured runtime metadata:

- `confidence` for answered responses;
- `insufficient_context_reason` for refusals, for example `no_retrieved_context` or
  `llm_refused_context`.

`confidence` does not replace citations.

Short-term conversation memory can be enabled with `CONVERSATION_MEMORY_ENABLED=true`.
It is used only to expand follow-up retrieval queries. Conversation history is not
treated as evidence.

## API Summary

Base prefix:

```text
/api/v1
```

Public or user endpoints:

- `GET /health`
- `GET /metrics`
- `POST /ask`
- `GET /chunks/{chunk_id}`
- `POST /agentic/ask` when `AGENTIC_RAG_ENABLED=true`

Admin endpoints:

- `GET /sources`
- `POST /sources`
- `POST /sources/{source_id}/test`
- `PATCH /sources/{source_id}`
- `DELETE /sources/{source_id}`
- `POST /indexing/jobs`
- `GET /indexing/jobs`
- `GET /indexing/jobs/{job_id}`
- `GET /audit`
- `POST /evaluation/retrieval`

Question request:

```json
{
  "question": "What does Product X support?",
  "source_ids": ["src_123"],
  "session_id": "browser-session-123",
  "top_k": 8
}
```

Answered response:

```json
{
  "answer": "Product X supports PostgreSQL imports [1].",
  "citations": [
    {
      "id": "1",
      "chunk_id": "chk_abc123",
      "document_id": "product.md",
      "source_id": "src_123",
      "title": "Product X",
      "section": null,
      "url": "/data/wiki/product.md",
      "quote": "Product X supports PostgreSQL imports.",
      "timestamp": null,
      "score": 0.91
    }
  ],
  "status": "answered",
  "confidence": 0.91,
  "insufficient_context_reason": null
}
```

Insufficient-context response:

```json
{
  "answer": "В базе знаний нет достаточной информации для ответа на этот вопрос.",
  "citations": [],
  "status": "insufficient_context",
  "confidence": null,
  "insufficient_context_reason": "no_retrieved_context"
}
```

Agentic ask response additionally includes tool calls:

```json
{
  "answer": "Product X supports agentic retrieval [1].",
  "citations": [
    {
      "id": "1",
      "chunk_id": "chk_agentic123",
      "document_id": "product.md",
      "source_id": "src_123",
      "title": "Product X",
      "section": null,
      "url": "/data/wiki/product.md",
      "quote": "Product X supports agentic retrieval.",
      "timestamp": null,
      "score": 0.8
    }
  ],
  "status": "answered",
  "confidence": 0.8,
  "insufficient_context_reason": null,
  "tool_calls": [
    {
      "name": "search_knowledge_base",
      "status": "success",
      "summary": "retrieved 1 chunks"
    }
  ]
}
```

## Development Checks

Backend:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m compileall src tests
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

Opt-in integration tests with Docker services:

```powershell
cd apps/api
$env:RUN_QDRANT_TESTS="true"
$env:RUN_POSTGRES_TESTS="true"
$env:QDRANT_URL="http://127.0.0.1:6333"
$env:QDRANT_TRUST_ENV="false"
$env:POSTGRES_HOST="127.0.0.1"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="wiki_ai_rag"
$env:POSTGRES_USER="wiki_ai_rag"
$env:POSTGRES_PASSWORD="wiki_ai_rag"
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd apps/web
npm run lint
npm run build
npm audit
```

Most recent full validation in this workspace:

- backend unit suite: `75 passed`, `2 skipped` integration tests;
- backend compile, Ruff and mypy: passed;
- frontend lint/build/audit: passed, `0 vulnerabilities`;
- Docker Compose configuration: valid.

The PostgreSQL and Qdrant integration tests are opt-in and were skipped in this
validation because the Docker daemon was unavailable.

## Operations

Runtime state layers:

- service metadata, sources, jobs and audit log in PostgreSQL for production, or
  `STORAGE_PATH` for lightweight development;
- local JSON vector store or Qdrant collection;
- PostgreSQL when used as local infrastructure or as an indexed source.

Do not commit runtime state, dumps, uploaded files, vector snapshots, API keys or
credentials.

Structured logs are emitted by the `wiki_ai_rag_api` logger as JSON. Question text is
not logged by default; logs contain `question_hash`, `question_length`, retrieval
counts, source ids, indexing status and timing metrics.

JSON state backup:

```powershell
Copy-Item storage\wiki_ai_rag_state.json backups\wiki_ai_rag_state.json
```

JSON state restore:

```powershell
Copy-Item backups\wiki_ai_rag_state.json storage\wiki_ai_rag_state.json
```

PostgreSQL backup:

```powershell
docker compose -f infra/docker-compose.yml exec postgres pg_dump -U wiki_ai_rag wiki_ai_rag > backups\wiki_ai_rag.sql
```

Qdrant local volume backup:

```powershell
docker compose -f infra/docker-compose.yml stop qdrant
docker run --rm -v wiki-ai-rag_qdrant_data:/data -v ${PWD}\backups:/backup alpine tar czf /backup/qdrant_data.tgz -C /data .
docker compose -f infra/docker-compose.yml start qdrant
```

Recovery strategy:

1. Restore source configuration and credentials.
2. Restore or recreate vector storage.
3. Run full indexing for each source.
4. Verify `/metrics`, `/audit`, `/indexing/jobs` and representative `/ask` queries.

## Roadmap

Completed:

- MVP source management, indexing and grounded answers.
- Filesystem, PostgreSQL and SQLite connectors.
- JSON and Qdrant vector store providers.
- Hybrid retrieval scoring.
- Retrieval evaluation endpoint.
- Reranker abstraction with local `keyword` provider.
- Structured answer metadata.
- Opt-in conversation memory.
- Opt-in agentic ask endpoint with internal `search_knowledge_base` tool.
- PostgreSQL metadata persistence and Celery/Redis background indexing.
- Stable chunk ids and incremental embedding reuse.
- Source-group ACL filtering and OIDC/JWKS authentication.
- BM25 + dense RRF retrieval and HTTP reranker provider.
- Structured answer/claim validation and prompt-injection boundaries.
- Structure-aware Markdown, HTML, PDF, DOCX, CSV and JSON parsing.
- Production Docker images, CI, SQL schema and rollout guide.

Planned next:

- persistent evaluation run history and UI;
- MCP-compatible server or adapter over the existing tool registry;
- additional connectors such as MySQL/MariaDB, wiki exports, S3/MinIO and transcript
  sources;
- native sparse-vector BM25 when the target Qdrant deployment supports managed
  inference or client-side sparse embeddings.

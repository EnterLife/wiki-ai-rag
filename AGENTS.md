# AGENTS.md

## Project

Wiki AI RAG is a retrieval-augmented generation service for grounded answers over
internal knowledge bases, databases, documents, transcripts and wiki exports.

The product goal is simple: users ask questions in a chat UI, and the system answers
only from indexed sources with citations. If there is no sufficient source context,
the system must refuse to answer instead of guessing.

Main principle:

```text
No source - no answer.
```

## Tech Stack

- Backend: Python 3.11+, FastAPI, Pydantic, SQLAlchemy.
- Frontend: React, TypeScript, Vite.
- Vector database: Qdrant for MVP.
- Service database: PostgreSQL.
- Background jobs: Celery, RQ or scheduler-backed jobs when implemented.
- Embeddings: provider abstraction, with support for multilingual models.
- LLM: provider abstraction, with OpenAI, YandexGPT, Ollama, LM Studio or local models as future options.
- Tests: `pytest` for backend, TypeScript checks for frontend.
- Local environment: `.venv` for backend, `node_modules` for frontend.

## Repository Structure

- `apps/api` - FastAPI backend.
- `apps/api/src/wiki_ai_rag_api/main.py` - API application entry point.
- `apps/api/src/wiki_ai_rag_api/api` - HTTP routers.
- `apps/api/src/wiki_ai_rag_api/schemas` - Pydantic request and response schemas.
- `apps/api/src/wiki_ai_rag_api/connectors` - data source connectors.
- `apps/api/src/wiki_ai_rag_api/services` - RAG, retrieval, indexing and LLM orchestration.
- `apps/api/tests` - backend tests.
- `apps/web` - React frontend.
- `apps/web/src/App.tsx` - initial chat and source UI.
- `apps/web/src/api` - frontend API client.
- `docs` - architecture, API, indexing, LLM policy and planning docs.
- `infra` - local Docker Compose and environment examples.
- `packages` - future shared packages.

## Coding Rules

- Keep edits focused on the requested behavior.
- Preserve user changes already present in the working tree.
- Do not refactor unrelated code while fixing a local issue.
- Do not edit `.env` files unless explicitly requested.
- Do not commit secrets, tokens, local datasets, database dumps, generated indexes or runtime artifacts.
- Avoid hardcoded credentials, absolute local paths, tokens, private server URLs or machine-specific model paths.
- Keep backend dependencies in `apps/api/pyproject.toml`.
- Keep frontend dependencies in `apps/web/package.json`.
- Prefer running backend commands through `.venv\Scripts\python.exe` on Windows when a virtual environment exists.
- Do not change generated/runtime folders unless the task requires it:
  - `.venv/`
  - `node_modules/`
  - `data/`
  - `storage/`
  - `uploads/`
  - `.pytest_cache/`
  - `__pycache__/`
- Do not leave unused imports, helpers, parameters or dead code after changing files.
- Use explicit names that describe RAG behavior, source handling and indexing behavior.
- Keep comments short and useful; avoid comments for obvious assignments.

## Code Quality Rules

- Before changing behavior, identify the expected user-visible outcome and the most likely failure case.
- For bug fixes, add or update a regression test that would fail before the fix when practical.
- For new behavior, add focused tests for:
  - the successful path;
  - at least one failure, edge or invalid-input path.
- Do not add tests that only verify mocks, implementation details or duplicated source logic.
- Prefer tests that assert product behavior: connector output, chunk metadata, retrieval results, refusal behavior, citations or API responses.
- If a change is documentation-only, formatting-only or a trivial internal cleanup, tests are not required unless behavior could change.
- Keep ordinary tests small and local; they must not require real LLM calls, external APIs, large files or network access.

## Architecture Rules

- Keep HTTP concerns in API routers.
- Keep orchestration in services such as RAG, indexing and retrieval services.
- Keep source-specific logic behind connector classes.
- Keep provider-specific LLM and embeddings code behind provider interfaces.
- Do not pass credentials into prompts, logs, citations or frontend responses.
- Do not let frontend code know provider-specific LLM, embedding or vector database details.
- Do not put indexing workflow logic directly in API routes.
- Keep document parsing, chunking, embeddings and vector persistence as separate steps.
- Add focused tests when changing chunking, retrieval, prompt construction, citation handling or refusal behavior.

## Source and Connector Rules

- Every connector should expose a consistent contract for connection testing and document iteration.
- Normalize data into documents with stable ids, source ids, titles, body text and metadata.
- Preserve useful citation metadata whenever available:
  - document title;
  - section;
  - page;
  - URL or path;
  - timestamp for transcripts;
  - source record id;
  - updated time.
- Filesystem indexing should be recursive but limited to supported extensions.
- PostgreSQL indexing must allow explicit tables, text fields, metadata fields and filters.
- Secrets and connection strings must be masked in responses and logs.

## Indexing Rules

- Indexing should be repeatable and safe to resume.
- Chunk text by semantic structure where possible: headings and paragraphs before fixed-size splits.
- Store chunk metadata sufficient to reconstruct citations.
- Use hashes to skip unchanged documents when incremental indexing is implemented.
- One bad document should not fail the whole indexing job.
- Record job status, processed documents, failed documents, start time, finish time and error details.
- For full reindexing, avoid leaving the source with an empty index if the job fails midway.

## RAG and LLM Rules

- The system must answer only from retrieved context.
- If retrieved context is empty, weak or unrelated, return the insufficient-context response.
- Every important claim in an answer should be supported by a citation.
- The default refusal message is:

```text
В базе знаний нет достаточной информации для ответа на этот вопрос.
```

- Do not use external model knowledge to fill gaps.
- Do not make unsupported assumptions.
- Do not hide that information is missing.
- Validate that generated answers include citations before returning `answered`.
- Treat prompt construction as security-sensitive code.

## UI Rules

- Keep the web UI practical and task-first: ask question, inspect answer, inspect sources.
- Do not add landing-page or marketing sections unless explicitly requested.
- Use clear loading, empty and error states.
- Keep citations easy to scan and expand.
- Admin UI should focus on source setup, connection testing, indexing status and source management.
- Do not expose implementation jargon unless it helps an administrator configure sources.

## Test Design Rules

- Tests should verify product behavior rather than implementation trivia.
- For behavior changes, include at least one happy-path test and one negative or edge-case test when applicable.
- Prefer focused backend tests for:
  - health and API contracts;
  - source connector behavior;
  - parser and chunk metadata;
  - retrieval filtering;
  - insufficient-context refusal;
  - citation formatting.
- Frontend checks should at minimum keep TypeScript compilation green.
- Do not require real Qdrant, PostgreSQL, LLM providers or embeddings providers in ordinary unit tests unless the test is explicitly integration-scoped.
- If integration tests are added later, keep them opt-in and document required services.
- Update docs when setup commands, source behavior, API contracts, indexing rules or answer policy changes.

## Review Rules

- For non-trivial code changes, perform a final review from the perspective of a fresh reader.
- Review only the user request, changed files and relevant tests.
- Check for:
  - missing negative tests;
  - behavior that is only partially tested;
  - unsupported answers without citations;
  - credentials or secrets leaking into logs, prompts, responses or UI;
  - connector, indexing or provider details leaking across module boundaries;
  - unused imports, dead code or speculative abstractions;
  - unclear user-facing errors.
- If using another AI pass or a new context window for review, provide it with the request, diff and test results, but not the full prior reasoning.
- Treat AI review as advisory; verify any suggested issue against the code before applying changes.

## Completion Criteria

A code change is complete only when:

- the requested behavior is implemented;
- relevant positive and negative tests are added or intentionally skipped with a clear reason;
- focused checks have been run when feasible;
- changed files are reviewed before the final response;
- remaining risks are mentioned, especially untested provider-backed LLM, embeddings, database or vector-search flows.

## Useful Commands

Start local infrastructure:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

Create and run the backend:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn wiki_ai_rag_api.main:app --reload
```

Run backend checks:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m compileall src tests
.\.venv\Scripts\python.exe -m pytest
```

Create and run the frontend:

```powershell
cd apps/web
npm install
npm run dev
```

Run frontend checks:

```powershell
cd apps/web
npm run lint
npm run build
```

## Commit Message Suggestions

- After each completed work chunk, include a suggested commit message in the final response.
- Use a lowercase prefix and a short lowercase summary.
- Keep the message in one line without a period at the end.
- Choose the prefix by intent:
  - `add:` for new user-visible features, adapters, tests or app flows.
  - `fix:` for bug fixes, broken behavior, failing checks or bad errors.
  - `upd:` for updates to existing features, docs, configs or expected behavior.
  - `refactor:` for internal restructuring without behavior changes.
  - `docs:` for documentation-only changes.
  - `test:` for test-only maintenance that does not add new coverage.
  - `chore:` for tooling, cleanup, dependency or repository maintenance.

Examples:

- `add: wiki ai rag project scaffold`
- `add: filesystem source indexing`
- `fix: refuse answers without retrieved context`
- `upd: document qdrant setup`
- `docs: add rag answer policy`

## Before Finishing Work

- Review changed files.
- Run the most focused relevant checks when feasible.
- For Python code changes, prefer:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m compileall src tests
.\.venv\Scripts\python.exe -m pytest
```

- For frontend code changes, prefer:

```powershell
cd apps/web
npm run lint
npm run build
```

- For docs-only changes, a syntax or test run is usually not required.
- If a required tool is unavailable, say so explicitly in the final response and mention the remaining risk.
- Mention any remaining risk, especially provider-backed LLM, embeddings, database or vector-search flows that were not executed.

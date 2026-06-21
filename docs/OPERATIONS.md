# Operations

## Runtime State

Wiki AI RAG has three runtime state layers:

- service metadata: sources, jobs and audit log in `STORAGE_PATH`;
- vector index: JSON vector store or Qdrant collection;
- service database: PostgreSQL when used by future persistent metadata or as an indexed source.

Do not commit runtime state, dumps, uploaded files, vector snapshots or credentials.

## Structured Logs

The API writes application logs as JSON records under the `wiki_ai_rag_api` logger.
Use `LOG_LEVEL=INFO` by default and raise it to `DEBUG` only for local debugging.

RAG events include:

- `rag.question.received` with `question_hash`, `question_length`, `top_k` and filter count;
- `rag.retrieval.completed` with retrieved chunk count, source ids and max score;
- `rag.answer.completed` with citation count;
- `rag.answer.insufficient_context` with refusal reason.

Indexing events include job start, completion and failure with source id, mode and
document/chunk counters. Credentials are not logged. Full question text is not logged
by default; set `LOG_QUESTION_TEXT=true` only in trusted local environments.

## Qdrant Connectivity

`VECTOR_STORE_PROVIDER=qdrant` uses the Qdrant client against `QDRANT_URL`.
On Windows with Docker Desktop, a local REST relay/proxy can return `503` to Python
`httpx` clients while browser, `curl` or PowerShell still show Qdrant as healthy.
The default `QDRANT_TRUST_ENV=false` bypasses environment proxy settings for this
client; set it to `true` only when Qdrant must be reached through a proxy.

## JSON Vector Store Backup

When `VECTOR_STORE_PROVIDER=json`, the local state file contains sources, jobs, audit log and chunks.

Backup:

```powershell
Copy-Item storage\wiki_ai_rag_state.json backups\wiki_ai_rag_state.json
```

Restore:

```powershell
Copy-Item backups\wiki_ai_rag_state.json storage\wiki_ai_rag_state.json
```

If `CREDENTIALS_ENCRYPTION_KEY` was used, restore with the same key.

## PostgreSQL Backup

For the local service database from `infra/docker-compose.yml`:

```powershell
docker compose -f infra/docker-compose.yml exec postgres pg_dump -U wiki_ai_rag wiki_ai_rag > backups\wiki_ai_rag.sql
```

Restore into an empty database:

```powershell
Get-Content backups\wiki_ai_rag.sql | docker compose -f infra/docker-compose.yml exec -T postgres psql -U wiki_ai_rag wiki_ai_rag
```

For indexed external PostgreSQL sources, use the owning system's backup policy. Wiki AI RAG should be able to rebuild its index from the source.

## Qdrant Backup

For local development, Docker volume backup is usually enough:

```powershell
docker compose -f infra/docker-compose.yml stop qdrant
docker run --rm -v wiki-ai-rag_qdrant_data:/data -v ${PWD}\backups:/backup alpine tar czf /backup/qdrant_data.tgz -C /data .
docker compose -f infra/docker-compose.yml start qdrant
```

Restore:

```powershell
docker compose -f infra/docker-compose.yml stop qdrant
docker run --rm -v wiki-ai-rag_qdrant_data:/data -v ${PWD}\backups:/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/qdrant_data.tgz -C /data"
docker compose -f infra/docker-compose.yml start qdrant
```

For production Qdrant, prefer managed snapshots and test restore regularly.

## Rebuild Strategy

The safest recovery path is often:

1. Restore source configurations and credentials.
2. Restore or recreate vector storage.
3. Run full indexing for each source.
4. Verify `/api/v1/metrics`, `/api/v1/audit`, `/api/v1/indexing/jobs` and representative `/api/v1/ask` queries.

## Secret Rotation

If `ADMIN_API_KEY`, `USER_API_KEY`, provider API keys or `CREDENTIALS_ENCRYPTION_KEY` are rotated:

- restart the API process after changing env;
- re-save source credentials if the encryption key changes;
- run source connection tests;
- run a full indexing job for affected sources.

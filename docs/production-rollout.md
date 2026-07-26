# Production rollout

## 1. Governance

Assign an owner, classification, allowed groups and freshness SLA to every source.
Prepare representative questions with expected documents before onboarding users.
Do not index a source until its owner approves access rules and retention.

## 2. Required production settings

Use `infra/.env.example` as the inventory, but keep actual secrets in a secret
manager. Production mode rejects unsafe defaults. At minimum configure:

```text
APP_ENV=production
AUTH_ENABLED=true
AUTH_PROVIDER=oidc
OIDC_ISSUER=...
OIDC_AUDIENCE=...
OIDC_JWKS_URL=...
CREDENTIALS_ENCRYPTION_KEY=...
METADATA_STORE_PROVIDER=postgres
VECTOR_STORE_PROVIDER=qdrant
QDRANT_USE_ALIAS=true
INDEXING_EXECUTION_MODE=celery
EMBEDDINGS_PROVIDER=openai_compatible
LLM_PROVIDER=openai_compatible
LLM_REQUIRE_STRUCTURED_OUTPUT=true
RATE_LIMIT_ENABLED=true
AGENTIC_RAG_ENABLED=false
```

Для первой миграции или полного переиндексирования создайте новую физическую
коллекцию и атомарно переключите alias только после успешной обработки всех
источников:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m wiki_ai_rag_api.services.index_migration
```

Если прежний deployment уже использует физическую коллекцию с именем из
`QDRANT_COLLECTION`, задайте для нового deployment другое логическое имя alias,
например `wiki_ai_rag_current`: alias Qdrant не может совпадать с именем
существующей физической коллекции.

Старую физическую коллекцию удаляйте отдельно только после проверки ответов,
цитат и метрик на новой версии.

Use service-specific database credentials and network policies. Do not put API keys
in variables prefixed with `VITE_`.

## 3. Deployment

```powershell
Copy-Item infra/.env.example .env
# Fill secret-manager references or local secrets.
docker compose -f infra/docker-compose.yml --profile app up -d --build
docker compose -f infra/docker-compose.yml ps
```

The compose stack contains API, Celery worker, web UI, PostgreSQL, Redis and Qdrant.
Terminate TLS at the company ingress or reverse proxy.

## 4. Acceptance gates

- Restore PostgreSQL and Qdrant from backups in a clean environment.
- Verify that users cannot retrieve chunks from another group.
- Run retrieval evaluation after every embedding, chunking, weight or reranker change.
- Red-team direct and document-borne prompt injection.
- Verify refusal precision on questions not covered by the corpus.
- Measure citation validity and claim coverage before expanding the pilot.

Start with a small group, review failed and low-confidence questions weekly, and only
then onboard additional sources and departments.

## 5. Index migrations

Incremental indexing reuses embeddings for unchanged chunk hashes. For an embedding
model or vector schema migration, build a separate Qdrant collection, evaluate it,
then atomically switch a collection alias. Keep the previous collection until the
rollback window closes.

Agentic RAG remains disabled by default. Enable tools only after ordinary retrieval,
ACL enforcement and audit have met their acceptance gates.

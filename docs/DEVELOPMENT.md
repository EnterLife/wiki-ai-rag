# Разработка

## Требования

- Python 3.11+
- Node.js 20+
- Docker Desktop или совместимый Docker runtime
- PostgreSQL 16+
- Qdrant

## Локальная инфраструктура

```bash
cp infra/.env.example .env
docker compose -f infra/docker-compose.yml up -d
```

Qdrant UI будет доступен на `http://localhost:6333/dashboard`.

## Backend

```bash
cd apps/api
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
uvicorn wiki_ai_rag_api.main:app --reload
```

Полезные команды:

```bash
pytest
ruff check .
ruff format .
```

Integration checks:

```powershell
docker compose -f ..\..\infra\docker-compose.yml up -d qdrant
$env:RUN_QDRANT_TESTS="true"
$env:QDRANT_URL="http://localhost:6333"
pytest tests/test_qdrant_integration.py
```

```powershell
docker compose -f ..\..\infra\docker-compose.yml up -d postgres
$env:RUN_POSTGRES_TESTS="true"
pytest tests/test_postgres_integration.py
```

## Frontend

```bash
cd apps/web
npm install
npm run dev
```

Полезные команды:

```bash
npm run lint
npm run build
```

## Environment variables

Основные переменные описаны в `infra/.env.example`.

Для локального режима допускается отключить реальную LLM-интеграцию и возвращать refusal/заглушку, пока retrieval не готов.

Дополнительно backend поддерживает:

```bash
STORAGE_PATH=storage/wiki_ai_rag_state.json
VECTOR_STORE_PROVIDER=json
QDRANT_URL=http://localhost:6333
QDRANT_TRUST_ENV=false
EMBEDDINGS_PROVIDER=hashing
EMBEDDINGS_BASE_URL=http://localhost:1234/v1
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=256
ENABLE_SCHEDULER=false
SCHEDULER_POLL_SECONDS=60
LLM_PROVIDER=extractive
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1
AUTH_ENABLED=false
# USER_API_KEY=
# CREDENTIALS_ENCRYPTION_KEY=
RATE_LIMIT_ENABLED=false
QUESTION_RATE_LIMIT_PER_MINUTE=60
LOG_LEVEL=INFO
LOG_QUESTION_TEXT=false
```

`STORAGE_PATH` задает локальное JSON-хранилище для sources, indexing jobs и JSON vector store. `VECTOR_STORE_PROVIDER=json` не требует Docker-сервисов. `VECTOR_STORE_PROVIDER=qdrant` использует Qdrant из `infra/docker-compose.yml`. `QDRANT_TRUST_ENV=false` защищает локальный Qdrant-клиент от системных proxy/relay настроек; включайте `true` только если Qdrant должен ходить через proxy. `EMBEDDINGS_PROVIDER=hashing` включает deterministic local embeddings без внешних сервисов. `EMBEDDINGS_PROVIDER=openai_compatible` вызывает `{EMBEDDINGS_BASE_URL}/embeddings`; `EMBEDDING_DIMENSION` должен совпадать с размерностью модели. `ENABLE_SCHEDULER=true` включает периодическую проверку scheduled sources. `LLM_PROVIDER=extractive` безопасно работает без внешней модели; `ollama` и `openai_compatible` включаются явно. `AUTH_ENABLED=true` требует `X-User-API-Key` для `/ask` и `X-Admin-API-Key` для source/indexing/audit endpoints. `CREDENTIALS_ENCRYPTION_KEY` включает Fernet-шифрование чувствительных source config полей. `RATE_LIMIT_ENABLED=true` ограничивает `/ask` по IP.
`LOG_LEVEL` управляет уровнем JSON-логов приложения. `LOG_QUESTION_TEXT=false` оставляет в логах только hash и длину вопроса; полный текст включайте только в доверенной локальной среде.

## Code conventions

- Backend modules name: `snake_case`.
- Frontend components: `PascalCase`.
- API response schemas должны быть явно описаны через Pydantic.
- Все ответы RAG должны возвращать `status`: `answered`, `insufficient_context` или `error`.
- Secrets не логировать и не возвращать клиенту.

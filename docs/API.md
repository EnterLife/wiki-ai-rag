# API Draft

Базовый prefix: `/api/v1`.

When `AUTH_ENABLED=true`, `/ask` requires `X-User-API-Key` or `X-Admin-API-Key`.
Admin endpoints under `/sources` and `/indexing` require `X-Admin-API-Key`.
`/audit` uses the same admin protection.

## Health

### `GET /health`

Проверяет доступность API.

Response:

```json
{
  "status": "ok",
  "service": "wiki-ai-rag-api"
}
```

## Metrics

### `GET /metrics`

Возвращает lightweight in-memory counters and duration summaries for the current API process.

Response:

```json
{
  "counters": {
    "ask.answered": 10,
    "ask.insufficient_context": 2,
    "indexing.completed": 3
  },
  "durations": {
    "ask.retrieval_ms": {
      "count": 12,
      "total_ms": 34.2,
      "avg_ms": 2.85,
      "max_ms": 8.4
    }
  }
}
```

## Questions

### `POST /ask`

Задает вопрос системе.
When `RATE_LIMIT_ENABLED=true`, this endpoint can return `429 Question rate limit exceeded`.

Request:

```json
{
  "question": "Что известно о продукте X?",
  "source_ids": ["src_123"],
  "top_k": 8
}
```

`source_ids` is optional. When present, retrieval is limited to those sources.

Insufficient-context response:

```json
{
  "answer": "В базе знаний нет достаточной информации для ответа на этот вопрос.",
  "citations": [],
  "status": "insufficient_context"
}
```

Answered response:

```json
{
  "answer": "Система поддерживает импорт из PostgreSQL и файловой системы [1].",
  "citations": [
    {
      "id": "1",
      "chunk_id": "chk_abc123",
      "document_id": "docs/product.md",
      "source_id": "src_123",
      "title": "Интеграции",
      "section": "Источники данных",
      "url": "https://wiki.example.local/integrations",
      "quote": "Система поддерживает PostgreSQL и файловую систему.",
      "timestamp": null,
      "score": 0.91
    }
  ],
  "status": "answered"
}
```

## Evidence

### `GET /chunks/{chunk_id}`

Возвращает индексированный фрагмент, на который ссылается citation.

Response:

```json
{
  "chunk_id": "chk_abc123",
  "document_id": "docs/product.md",
  "source_id": "src_123",
  "title": "Product X",
  "text": "Product X supports PostgreSQL imports.",
  "metadata": {
    "path": "/data/wiki/product.md"
  },
  "score": 1.0
}
```

Этот endpoint не возвращает credentials или source config.

## Sources

### `GET /sources`

Возвращает список источников без credentials.

### `POST /sources`

Создает источник.

Filesystem request:

```json
{
  "name": "Product Wiki",
  "type": "filesystem",
  "config": {
    "path": "/data/wiki"
  },
  "enabled": true,
  "schedule": {
    "mode": "manual"
  }
}
```

PostgreSQL request:

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

`dsn` can be used instead of host/port/database/username/password. Credentials are encrypted when `CREDENTIALS_ENCRYPTION_KEY` is configured.

SQLite request:

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

### `POST /sources/{source_id}/test`

Проверяет подключение. Для `filesystem` проверяет, что путь существует и является директорией.

### `PATCH /sources/{source_id}`

Updates source `name`, `enabled` or `schedule`.

Request:

```json
{
  "enabled": false
}
```

### `DELETE /sources/{source_id}`

Удаляет источник и связанные chunks.

## Indexing

### `POST /indexing/jobs`

Запускает индексацию. В текущем MVP job выполняется синхронно внутри запроса и сразу возвращает финальный статус.

Request:

```json
{
  "source_id": "src_123",
  "mode": "full"
}
```

### `GET /indexing/jobs`

Возвращает последние jobs. Поддерживает query parameters `source_id` и `limit`.

### `GET /indexing/jobs/{job_id}`

Возвращает статус job.

Response:

```json
{
  "job_id": "job_123",
  "source_id": "src_123",
  "status": "running",
  "processed_documents": 42,
  "failed_documents": 0,
  "started_at": "2026-06-21T10:00:00Z",
  "finished_at": null,
  "error": null
}
```

## Audit

### `GET /audit`

Возвращает последние administrative events. Query parameter `limit` ограничен диапазоном `1..500`.

Response:

```json
[
  {
    "id": "audit_abc123",
    "action": "source.create",
    "target_type": "source",
    "target_id": "src_123",
    "status": "success",
    "details": {
      "type": "filesystem",
      "name": "Product Wiki"
    },
    "created_at": "2026-06-21T10:00:00Z"
  }
]
```

Audit events must not include credentials or source config secrets.

## Current MVP Notes

- Sources и jobs хранятся в локальном JSON-файле, заданном через `STORAGE_PATH`.
- Chunks хранятся в выбранном vector store: `json` или `qdrant`.
- Реально поддержаны filesystem source и PostgreSQL source connector contract.
- Embeddings поддерживают local hashing provider и OpenAI-compatible provider.
- `POST /ask` использует retrieval и grounded LLM provider, поэтому не придумывает факты вне найденных chunks.
- Ошибки API возвращаются в JSON shape `{"status": "error", "detail": ...}`.

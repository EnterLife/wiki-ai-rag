# Архитектура

## Обзор

```text
Frontend
  -> Backend API
  -> RAG Orchestrator
  -> Retriever
  -> Vector Database
  -> LLM Service
```

Дополнительные компоненты:

- Data Connector Layer получает документы из источников.
- Indexing Service превращает документы в chunks и embeddings.
- Metadata Store хранит источники, статусы индексации, пользователей и аудит.
- Object/File Storage хранит оригиналы или извлеченный текст, если это нужно для повторной индексации.

## Слои репозитория

```text
apps/
  api/        FastAPI backend
  web/        React frontend
docs/         проектная документация
infra/        docker compose и env examples
packages/     будущие общие пакеты
```

## Backend API

Задачи:

- авторизация и роли;
- управление источниками;
- запуск и статус индексации;
- прием пользовательских вопросов;
- возврат ответа, источников и цитат;
- защита API от утечки credentials.

## Data Connector Layer

Каждый connector должен реализовать единый контракт:

- `test_connection`;
- `iter_documents`;
- `get_document`;
- `get_incremental_changes`, когда источник это поддерживает.

Минимальные connector-ы MVP:

- filesystem;
- PostgreSQL.

## Indexing Service

Pipeline:

1. Забрать документы из connector-а.
2. Распарсить формат.
3. Очистить текст.
4. Разбить на chunks.
5. Создать embeddings.
6. Сохранить chunks и metadata в Qdrant.
7. Обновить статус индексации.

## Retrieval Service

Retrieval должен возвращать не только текст, но и доказательную базу:

- `chunk_id`;
- `source_id`;
- `document_title`;
- `section`;
- `url` или локальный путь;
- `timestamp`, если есть;
- `quote`;
- score.

Для MVP достаточно vector search. После стабилизации можно добавить hybrid search и reranking.

## LLM Service

LLM получает только подготовленный context pack. В prompt запрещается использовать внешние знания. Если context pack пустой или недостаточный, сервис возвращает отказ без обращения к генерации или с жестко ограниченным refusal prompt.

## Хранилища

- PostgreSQL: пользователи, источники, jobs, audit log, настройки.
- Qdrant: embeddings, chunks, metadata для retrieval.
- Локальная файловая система или MinIO: оригиналы документов и артефакты парсинга при необходимости.

## Поток вопроса

```text
User question
  -> POST /api/v1/ask
  -> normalize question
  -> retrieve top-k chunks
  -> validate context sufficiency
  -> build grounded prompt
  -> call LLM
  -> validate answer sources
  -> return answer + citations
```

## Поток индексации

```text
Source config
  -> connector
  -> raw documents
  -> parser
  -> chunks
  -> embeddings
  -> Qdrant collection
  -> indexing status
```

## Безопасность

- Credentials хранятся зашифрованно.
- Secrets не возвращаются в API.
- Secrets не логируются.
- Secrets не передаются в LLM.
- Admin endpoints требуют роль `admin`.
- Все действия администратора пишутся в audit log.


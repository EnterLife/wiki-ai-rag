# Индексация

## Цель

Преобразовать документы из разных источников в единый набор chunks, пригодных для поиска и цитирования.

## Нормализованный документ

```json
{
  "id": "doc_123",
  "source_id": "src_123",
  "title": "Название документа",
  "body": "Полный извлеченный текст",
  "metadata": {
    "path": "/data/wiki/product.md",
    "section": "Описание продукта",
    "url": null,
    "record_id": null,
    "timestamp": null,
    "updated_at": "2026-06-21T10:00:00Z"
  }
}
```

## Chunk metadata

Каждый chunk должен содержать:

- `chunk_id`;
- `document_id`;
- `source_id`;
- `title`;
- `section`;
- `page`, если доступно;
- `url` или `path`;
- `timestamp`, если доступно;
- `record_id`, если доступно;
- `text`;
- `hash`;
- `embedding`;
- `created_at`;
- `updated_at`.

## Chunking

Рекомендуемые настройки MVP:

- целевой размер: 500-900 tokens;
- overlap: 80-150 tokens;
- разрывы по заголовкам и абзацам предпочтительнее механического разбиения;
- короткие фрагменты объединять с соседними, если это не ломает структуру;
- таблицы сохранять в markdown-like текст, чтобы не терять контекст.

## Incremental updates

Для каждого документа вычисляется hash нормализованного текста и метаданных. Если hash не изменился, embedding пересоздавать не нужно.

## MVP embeddings

Текущий локальный MVP использует deterministic hashing embeddings. Это позволяет хранить вектор в chunk и тестировать retrieval path без внешней модели или сети.

Vector store выбирается через `VECTOR_STORE_PROVIDER`:

- `json` - хранит chunks рядом с локальным state-файлом, удобно для тестов и быстрого запуска.
- `qdrant` - хранит chunks и embeddings в Qdrant collection из `QDRANT_COLLECTION`.

Для model-backed embeddings используйте `EMBEDDINGS_PROVIDER=openai_compatible`, `EMBEDDINGS_BASE_URL`, `EMBEDDINGS_MODEL`, optional `EMBEDDINGS_API_KEY` и корректный `EMBEDDING_DIMENSION`.

## Удаление устаревших chunks

При полной переиндексации:

1. Пометить старые chunks источника как stale.
2. Записать новые chunks.
3. Удалить stale chunks, которые не встретились в новом проходе.

Такой порядок снижает риск пустого индекса при ошибке в середине job.

## Ошибки парсинга

Ошибки одного документа не останавливают всю job. Job завершается со статусом `completed`, если источник доступен и остальные документы обработаны, а `failed_documents` отражает количество проблемных документов. Нужно сохранить:

- document id или path;
- тип ошибки;
- сообщение;
- stack trace в логах;
- счетчик failed documents в статусе job.

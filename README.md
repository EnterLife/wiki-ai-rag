# Wiki AI RAG

Wiki AI RAG is a universal retrieval-augmented generation service for grounded answers based on internal knowledge bases, databases, documents and transcripts.

Главный принцип проекта:

```text
Нет источника - нет ответа.
```

## Текущее состояние

- `apps/api` - backend на FastAPI с API источников, индексации, вопросов, audit, metrics и evidence.
- `apps/web` - frontend на React + TypeScript + Vite с chat UI и админским управлением sources.
- `infra` - локальная инфраструктура для PostgreSQL и Qdrant.
- `docs` - план разработки, архитектура, API, правила индексации и политика ответов LLM.
- Локальный MVP хранит sources и jobs в JSON-файле `storage/wiki_ai_rag_state.json`.
- Реализован ручной flow: добавить source, проверить подключение, запустить full indexing, задать вопрос.
- MVP file parsers покрывают Markdown, TXT, PDF, DOCX, HTML, CSV и JSON.
- Добавлены filesystem, PostgreSQL и SQLite connectors для таблиц с явными text и metadata fields.
- Индекс может работать через JSON vector store или Qdrant при `VECTOR_STORE_PROVIDER=qdrant`.
- Retrieval может использовать deterministic hashing embeddings или OpenAI-compatible embeddings provider. LLM слой строит grounded prompt и по умолчанию использует безопасный local `extractive` provider; `ollama` и `openai_compatible` можно включить через env.
- Citations включают `chunk_id` и `document_id`; фрагмент можно проверить через `GET /api/v1/chunks/{chunk_id}`.
- Пользовательский запрос можно ограничить выбранными источниками, а административный API можно защитить opt-in API keys.

## Целевой MVP

1. Подключение файловой директории, PostgreSQL и SQLite.
2. Индексация Markdown, TXT, PDF и DOCX.
3. Хранение embeddings и метаданных в Qdrant.
4. Чат-интерфейс с ответами только по найденному контексту.
5. Источники, цитаты и отказ от ответа при нехватке данных.
6. Ручная и плановая переиндексация.

## Поддержанный локальный flow

1. Запустите backend.
2. Запустите frontend.
3. В sidebar добавьте filesystem-, PostgreSQL- или SQLite-источник с нужными text fields.
4. Нажмите проверку источника.
5. Запустите индексацию.
6. Задайте вопрос в чате.

Для периодической переиндексации источников с `schedule.mode=scheduled` включите `ENABLE_SCHEDULER=true`.

Для шифрования чувствительных source credentials задайте `CREDENTIALS_ENCRYPTION_KEY` ключом Fernet.

Административные действия пишутся в audit log и доступны через `GET /api/v1/audit`.

Если релевантных chunks нет, API вернет:

```text
В базе знаний нет достаточной информации для ответа на этот вопрос.
```

## Быстрый старт разработки

```bash
cp infra/.env.example .env
docker compose -f infra/docker-compose.yml up -d
```

Для lightweight запуска без Qdrant оставьте `VECTOR_STORE_PROVIDER=json`. Для проверки Qdrant включите:

```bash
VECTOR_STORE_PROVIDER=qdrant
```

Backend:

```bash
cd apps/api
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
uvicorn wiki_ai_rag_api.main:app --reload
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

## Документация

- [План разработки](docs/PROJECT_PLAN.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Разработка](docs/DEVELOPMENT.md)
- [Индексация](docs/INDEXING.md)
- [Политика ответов LLM](docs/LLM_POLICY.md)
- [Эксплуатация](docs/OPERATIONS.md)

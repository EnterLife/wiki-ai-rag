# План разработки Wiki AI RAG

## Цель

Создать сервис, который подключает внутренние источники знаний, индексирует их и отвечает пользователю только на основе найденных фрагментов с обязательными источниками и цитатами.

## Принципы продукта

- Нет найденного источника - нет ответа.
- Каждое существенное утверждение должно быть связано с источником.
- Credentials никогда не попадают в LLM prompt.
- Индексация должна быть повторяемой, наблюдаемой и безопасной.
- MVP оптимизируется под русский и английский текст.

## Этап 0. Каркас и проектные решения

Статус: выполнен.

- Создать монорепозиторий.
- Зафиксировать архитектуру и API-контракты.
- Подготовить локальную инфраструктуру PostgreSQL + Qdrant.
- Описать pipeline индексации.
- Описать политику grounded answers.

Результат: разработчик может открыть репозиторий и понять, куда добавлять backend, frontend, connectors, indexing и RAG-логику.

## Этап 1. Базовый backend

Цель: получить рабочий API-скелет.

Статус: выполнен для MVP.

- FastAPI-приложение.
- Health endpoint.
- API для вопросов.
- API для источников.
- API для запуска индексации.
- Pydantic-схемы.
- Конфигурация через environment variables.
- Локальное JSON-хранилище для dev/MVP.
- Структурированные JSON-логи для RAG и indexing событий; текст вопроса скрыт по умолчанию.
- Базовые unit tests.

Критерий готовности: `GET /api/v1/health` возвращает статус, API-контракты доступны в OpenAPI.

## Этап 2. Источники данных

Цель: поддержать минимум один файловый источник и PostgreSQL.

Статус: выполнен для MVP.

- Filesystem connector реализован для обхода поддержанных файлов.
- PostgreSQL connector реализован через `asyncpg`; DB round-trip покрыт opt-in integration test.
- SQLite connector реализован и покрыт локальным indexing/ask тестом.
- Нормализованная модель `Document`.
- Извлечение метаданных: source id, title, path, section, page, record id, timestamps.
- Проверка подключения источника.
- Маскирование secrets в API-ответах и логах.

Критерий готовности: система получает документы из директории и PostgreSQL-таблицы по заданной конфигурации.
Примечание: PostgreSQL round-trip вынесен в opt-in integration test и требует запущенный Docker/PostgreSQL.

## Этап 3. Индексация

Цель: построить повторяемый pipeline подготовки данных.

Статус: выполнен для MVP.

- Парсеры Markdown, TXT, PDF и DOCX покрыты focused tests; CSV/JSON читаются через text reader, HTML подключен лениво.
- Очистка текста реализована базово.
- Chunking с сохранением привязки к источнику реализован.
- Embeddings реализованы через локальный deterministic hashing provider и OpenAI-compatible provider.
- Запись chunks реализована через vector store abstraction: JSON для lightweight local и Qdrant при `VECTOR_STORE_PROVIDER=qdrant`; Qdrant round-trip покрыт opt-in integration test.
- Статус индексации реализован для ручных jobs.
- Ручная переиндексация реализована как full replace по source.
- Плановая переиндексация реализована как opt-in scheduler при `ENABLE_SCHEDULER=true`.
- Ошибки отдельных документов не останавливают filesystem/PostgreSQL/SQLite indexing job.

Критерий готовности: документы появляются в Qdrant с текстом, embedding и метаданными.
Примечание: Qdrant round-trip реализован как opt-in integration test и требует запущенный Docker/Qdrant.

## Этап 4. Retrieval и RAG

Цель: отвечать только по найденному контексту.

Статус: выполнен для MVP.

- Vector search реализован через vector store abstraction: JSON для lightweight local и Qdrant при `VECTOR_STORE_PROVIDER=qdrant`.
- Фильтры по источникам.
- Frontend поддерживает выбор источников для пользовательского вопроса.
- Подготовка context pack для LLM реализована.
- Prompt с запретом внешних знаний реализован.
- Отказ от ответа при пустом или слабом контексте.
- Возврат источников и цитат.
- Тесты на отказ при отсутствии контекста и ответы без citation markers.

Критерий готовности: вопрос возвращает ответ с источниками или честный отказ.

## Этап 5. Frontend MVP

Цель: дать пользователю простой web chat.

Статус: выполнен для MVP.

- Chat UI.
- История сообщений.
- Состояния загрузки и ошибки.
- UI отображает structured API error details для auth, validation и rate-limit ошибок.
- Блок источников.
- Раскрытие цитат и просмотр chunk/document identifiers.
- Минимальный admin UI для источников.
- Admin UI поддерживает создание filesystem, PostgreSQL и SQLite sources.
- Admin UI поддерживает включение и отключение источников.
- Запуск индексации из UI.
- Просмотр последних indexing jobs в UI.
- Просмотр audit и metrics summary в UI.

Критерий готовности: пользователь задает вопрос и видит ответ, источники и цитаты.

## Этап 6. Безопасность и эксплуатация

Цель: подготовить сервис к пилоту.

Статус: выполнен для ограниченного пилота.

- Авторизация пользователей.
- Базовая opt-in защита admin API через `X-Admin-API-Key`.
- Роли user/admin реализованы как opt-in user/admin API keys.
- Шифрование credentials реализовано для чувствительных source config полей при наличии `CREDENTIALS_ENCRYPTION_KEY`.
- Audit log действий администратора реализован для source и indexing actions.
- Opt-in rate limits для question API реализованы через in-memory limiter.
- Метрики времени retrieval, LLM и indexing реализованы через lightweight `/metrics`.
- Backup/restore рекомендации для JSON state, PostgreSQL и Qdrant описаны в `docs/OPERATIONS.md`.

Критерий готовности: сервис можно безопасно отдать ограниченной группе пользователей.

## Приоритеты MVP

| Приоритет | Задача |
| --- | --- |
| P0 | FastAPI API, Qdrant, файловый источник, строгий grounded prompt |
| P0 | Источники и цитаты в ответе |
| P0 | Отказ при отсутствии данных |
| P1 | PostgreSQL connector |
| P1 | Плановая переиндексация |
| P1 | Admin UI |
| P2 | Hybrid search, reranker, wiki exports, S3/MinIO |

# ADR-0001: Monorepo and MVP Stack

## Status

Accepted.

## Context

Проект включает backend API, web UI, indexing pipeline, connectors и инфраструктуру для векторного поиска. Для MVP важна скорость разработки и понятная локальная среда.

## Decision

Используем монорепозиторий:

- `apps/api` для FastAPI backend;
- `apps/web` для React frontend;
- `infra` для локальных сервисов;
- `docs` для проектной документации.

MVP stack:

- Python + FastAPI;
- React + TypeScript + Vite;
- PostgreSQL как основная база сервиса;
- Qdrant как vector database;
- embeddings provider через абстракцию, чтобы можно было заменить OpenAI, bge-m3 или другой provider.

## Consequences

- Проще запускать проект локально.
- Контракты API и UI развиваются рядом.
- Нужно следить, чтобы frontend и backend не начали импортировать код напрямую друг из друга.


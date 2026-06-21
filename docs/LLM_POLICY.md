# Политика ответов LLM

## Основное правило

LLM отвечает только на основе retrieved context. Если релевантного контекста нет, ответ должен быть:

```text
В базе знаний нет достаточной информации для ответа на этот вопрос.
```

## Запрещено

- Использовать внешние знания модели.
- Додумывать факты.
- Делать предположения без источника.
- Отвечать без найденного контекста.
- Упоминать credentials, внутренние connection strings или secrets.

## Требования к ответу

- Каждое важное утверждение должно иметь ссылку вида `[1]`.
- В конце ответа возвращается структурированный список sources.
- Цитата должна быть короткой и достаточной для проверки утверждения.
- Если источники противоречат друг другу, ответ должен явно указать на противоречие.

## Context sufficiency

Перед генерацией нужно проверить:

- есть ли найденные chunks;
- достаточно ли высок score;
- покрывают ли chunks вопрос пользователя;
- можно ли процитировать утверждение.

Если проверка не пройдена, возвращается `insufficient_context`.

## Prompt skeleton

```text
Ты отвечаешь на вопрос пользователя только по контексту ниже.
Не используй внешние знания.
Если контекста недостаточно, ответь: "В базе знаний нет достаточной информации для ответа на этот вопрос."
Каждое существенное утверждение сопровождай ссылкой на источник в формате [n].

Вопрос:
{question}

Контекст:
{context}
```

## MVP providers

`LLM_PROVIDER=extractive` is the default local provider. It does not call an external model; it returns grounded quotes with citation markers and is useful for safe local testing.

Optional providers:

- `LLM_PROVIDER=ollama` calls `{LLM_BASE_URL}/api/chat` with `LLM_MODEL`.
- `LLM_PROVIDER=openai_compatible` calls `{LLM_BASE_URL}/chat/completions` with `LLM_MODEL` and optional `LLM_API_KEY`.

All providers use the same grounded prompt and answers without citation markers are rejected as insufficient context.

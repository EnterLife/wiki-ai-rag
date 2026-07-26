FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN addgroup --system rag && adduser --system --ingroup rag rag \
    && mkdir -p /app/storage \
    && chown -R rag:rag /app
USER rag

EXPOSE 8000
CMD ["uvicorn", "wiki_ai_rag_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

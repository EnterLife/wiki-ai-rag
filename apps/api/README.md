# Wiki AI RAG API

FastAPI backend for source management, indexing and grounded question answering.

## Run

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
uvicorn wiki_ai_rag_api.main:app --reload
```

OpenAPI: `http://localhost:8000/docs`.


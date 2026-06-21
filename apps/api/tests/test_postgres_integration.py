import os
from uuid import uuid4

import pytest

from wiki_ai_rag_api.connectors.postgres import PostgresConnector


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "true",
    reason="Set RUN_POSTGRES_TESTS=true to run PostgreSQL integration tests",
)
def test_postgres_connector_reads_configured_table() -> None:
    pytest.importorskip("asyncpg")
    import asyncio

    asyncio.run(_run_postgres_connector_round_trip())


async def _run_postgres_connector_round_trip() -> None:
    import asyncpg

    table_name = f"pages_{uuid4().hex[:12]}"
    connection = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "wiki_ai_rag"),
        user=os.getenv("POSTGRES_USER", "wiki_ai_rag"),
        password=os.getenv("POSTGRES_PASSWORD", "wiki_ai_rag"),
    )
    try:
        await connection.execute(
            f'CREATE TABLE "{table_name}" (id integer primary key, title text, body text, url text)'
        )
        await connection.execute(
            f'INSERT INTO "{table_name}" (id, title, body, url) VALUES ($1, $2, $3, $4)',
            1,
            "Product X",
            "Product X supports PostgreSQL imports.",
            "https://wiki.example/product-x",
        )

        connector = PostgresConnector(
            source_id="src_pg",
            config={
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "database": os.getenv("POSTGRES_DB", "wiki_ai_rag"),
                "username": os.getenv("POSTGRES_USER", "wiki_ai_rag"),
                "password": os.getenv("POSTGRES_PASSWORD", "wiki_ai_rag"),
                "tables": [
                    {
                        "name": table_name,
                        "id_field": "id",
                        "title_field": "title",
                        "text_fields": ["body"],
                        "metadata_fields": ["url"],
                    }
                ],
            },
        )

        documents = [document async for document in connector.iter_documents()]

        assert len(documents) == 1
        assert documents[0].id == f"{table_name}:1"
        assert documents[0].title == "Product X"
        assert "PostgreSQL" in documents[0].body
        assert documents[0].metadata["url"] == "https://wiki.example/product-x"
    finally:
        await connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        await connection.close()


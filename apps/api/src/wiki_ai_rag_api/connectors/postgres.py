from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

from wiki_ai_rag_api.connectors.base import DataConnector, SourceDocument

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PostgresConnector(DataConnector):
    def __init__(self, source_id: str, config: dict[str, Any]) -> None:
        self.source_id = source_id
        self.config = config

    async def test_connection(self) -> bool:
        try:
            connection = await self._connect()
            await connection.close()
            return True
        except Exception:
            return False

    async def iter_documents(self) -> AsyncIterator[SourceDocument]:
        connection = await self._connect()
        try:
            for table_config in self._table_configs():
                query, limit = build_select_query(table_config)
                rows = await connection.fetch(query, limit) if limit is not None else await connection.fetch(query)

                for row in rows:
                    row_data = dict(row)
                    row_id = str(row_data.get("__id") or "")
                    table_name = table_config["name"]
                    title = str(row_data.get("__title") or f"{table_name} / {row_id}".strip())
                    body = "\n\n".join(
                        str(row_data[field])
                        for field in table_config["text_fields"]
                        if row_data.get(field) is not None
                    )
                    metadata = {
                        "table": table_name,
                        "record_id": row_id,
                        **{
                            field: row_data.get(field)
                            for field in table_config.get("metadata_fields", [])
                            if field in row_data
                        },
                    }

                    yield SourceDocument(
                        id=f"{table_name}:{row_id}",
                        source_id=self.source_id,
                        title=title,
                        body=body,
                        metadata=metadata,
                    )
        finally:
            await connection.close()

    async def _connect(self):
        import asyncpg

        if self.config.get("dsn"):
            return await asyncpg.connect(dsn=self.config["dsn"])

        return await asyncpg.connect(
            host=self.config.get("host", "localhost"),
            port=int(self.config.get("port", 5432)),
            database=self.config["database"],
            user=self.config["username"],
            password=self.config["password"],
            ssl=self.config.get("ssl"),
        )

    def _table_configs(self) -> list[dict[str, Any]]:
        tables = self.config.get("tables")
        if not isinstance(tables, list) or not tables:
            raise ValueError("PostgreSQL source requires a non-empty 'tables' list")

        normalized: list[dict[str, Any]] = []
        for table in tables:
            if not isinstance(table, dict):
                raise ValueError("Each PostgreSQL table config must be an object")
            if not table.get("name"):
                raise ValueError("Each PostgreSQL table config requires 'name'")
            if not table.get("text_fields"):
                raise ValueError("Each PostgreSQL table config requires 'text_fields'")

            normalized.append(
                {
                    "name": table["name"],
                    "id_field": table.get("id_field", "id"),
                    "title_field": table.get("title_field"),
                    "text_fields": list(table["text_fields"]),
                    "metadata_fields": list(table.get("metadata_fields", [])),
                    "limit": table.get("limit"),
                }
            )
        return normalized


def build_select_query(table_config: dict[str, Any]) -> tuple[str, int | None]:
    table_name = quote_qualified_identifier(table_config["name"])
    id_field = quote_identifier(table_config["id_field"])
    title_field = table_config.get("title_field")
    text_fields = table_config["text_fields"]
    metadata_fields = table_config.get("metadata_fields", [])
    limit = table_config.get("limit")

    selected_fields = _unique_fields(
        [table_config["id_field"]]
        + ([title_field] if title_field else [])
        + text_fields
        + metadata_fields
    )

    select_parts = [f"{id_field} AS __id"]
    if title_field:
        select_parts.append(f"{quote_identifier(title_field)} AS __title")
    for field in selected_fields:
        if field == table_config["id_field"] or field == title_field:
            continue
        select_parts.append(quote_identifier(field))

    query = f"SELECT {', '.join(select_parts)} FROM {table_name}"
    if limit is not None:
        query = f"{query} LIMIT $1"
        return query, int(limit)
    return query, None


def quote_qualified_identifier(value: str) -> str:
    return ".".join(quote_identifier(part) for part in value.split("."))


def quote_identifier(value: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def _unique_fields(fields: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for field in fields:
        if not field or field in seen:
            continue
        seen.add(field)
        result.append(field)
    return result

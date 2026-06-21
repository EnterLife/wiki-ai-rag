import pytest

from wiki_ai_rag_api.connectors.postgres import build_select_query, quote_identifier


def test_build_select_query_quotes_identifiers_and_adds_limit() -> None:
    query, limit = build_select_query(
        {
            "name": "public.pages",
            "id_field": "id",
            "title_field": "title",
            "text_fields": ["body"],
            "metadata_fields": ["url", "section"],
            "limit": 100,
        }
    )

    assert query == (
        'SELECT "id" AS __id, "title" AS __title, "body", "url", "section" '
        'FROM "public"."pages" LIMIT $1'
    )
    assert limit == 100


def test_quote_identifier_rejects_unsafe_input() -> None:
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        quote_identifier("pages;DROP TABLE pages")


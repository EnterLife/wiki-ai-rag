from types import SimpleNamespace

from wiki_ai_rag_api.services.index_migration import _promote_alias


class FakeAliasClient:
    def __init__(self, aliases: list[str]) -> None:
        self.aliases = aliases
        self.operations = []

    def get_aliases(self):
        return SimpleNamespace(
            aliases=[SimpleNamespace(alias_name=alias) for alias in self.aliases]
        )

    def update_collection_aliases(self, operations) -> None:
        self.operations = operations


def test_promote_alias_replaces_existing_alias_atomically() -> None:
    client = FakeAliasClient(["wiki_ai_chunks"])
    vector_store = SimpleNamespace(client=client)

    _promote_alias(
        vector_store,
        alias_name="wiki_ai_chunks",
        collection_name="wiki_ai_chunks_v_20260726",
    )

    assert len(client.operations) == 2
    assert client.operations[0].delete_alias.alias_name == "wiki_ai_chunks"
    assert client.operations[1].create_alias.collection_name == (
        "wiki_ai_chunks_v_20260726"
    )


def test_promote_alias_creates_alias_when_missing() -> None:
    client = FakeAliasClient([])
    vector_store = SimpleNamespace(client=client)

    _promote_alias(
        vector_store,
        alias_name="wiki_ai_chunks",
        collection_name="wiki_ai_chunks_v_20260726",
    )

    assert len(client.operations) == 1
    assert client.operations[0].create_alias.alias_name == "wiki_ai_chunks"

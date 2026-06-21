from collections.abc import AsyncIterator
from pathlib import Path

from wiki_ai_rag_api.connectors.base import DataConnector, SourceDocument

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".html", ".csv", ".json"}


class FilesystemConnector(DataConnector):
    def __init__(self, source_id: str, root_path: str) -> None:
        self.source_id = source_id
        self.root_path = Path(root_path)

    async def test_connection(self) -> bool:
        return self.root_path.exists() and self.root_path.is_dir()

    async def iter_documents(self) -> AsyncIterator[SourceDocument]:
        for path in self.root_path.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            yield SourceDocument(
                id=str(path.relative_to(self.root_path)),
                source_id=self.source_id,
                title=path.stem,
                body="",
                metadata={
                    "path": str(path),
                    "relative_path": str(path.relative_to(self.root_path)),
                    "extension": path.suffix.lower(),
                },
            )

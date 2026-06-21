from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SourceDocument:
    id: str
    source_id: str
    title: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


class DataConnector(ABC):
    @abstractmethod
    async def test_connection(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def iter_documents(self) -> AsyncIterator[SourceDocument]:
        raise NotImplementedError


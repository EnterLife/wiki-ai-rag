from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SourceType = Literal["filesystem", "postgresql", "sqlite"]


class SourceSchedule(BaseModel):
    mode: Literal["manual", "scheduled"] = "manual"
    interval_hours: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_interval(self) -> "SourceSchedule":
        if self.mode == "scheduled" and self.interval_hours is None:
            raise ValueError("interval_hours is required for scheduled sources")
        return self


class SourceCreate(BaseModel):
    name: str = Field(min_length=1)
    type: SourceType
    config: dict[str, Any]
    enabled: bool = True
    access_groups: list[str] = Field(default_factory=list)
    schedule: SourceSchedule = Field(default_factory=SourceSchedule)

    @field_validator("access_groups")
    @classmethod
    def normalize_access_groups(cls, groups: list[str]) -> list[str]:
        normalized = sorted({group.strip() for group in groups if group.strip()})
        if len(normalized) != len(groups):
            raise ValueError("access_groups must contain unique non-empty values")
        return normalized

    @model_validator(mode="after")
    def validate_connector_config(self) -> "SourceCreate":
        if self.type == "filesystem" and not str(self.config.get("path", "")).strip():
            raise ValueError("filesystem source requires config.path")
        if self.type == "sqlite" and not str(self.config.get("database_path", "")).strip():
            raise ValueError("sqlite source requires config.database_path")
        if self.type == "postgresql":
            has_dsn = bool(str(self.config.get("dsn", "")).strip())
            required = ("database", "username", "password")
            if not has_dsn and any(not self.config.get(field) for field in required):
                raise ValueError(
                    "postgresql source requires config.dsn or database, username and password"
                )
        if self.type in {"postgresql", "sqlite"}:
            tables = self.config.get("tables")
            if not isinstance(tables, list) or not tables:
                raise ValueError(f"{self.type} source requires a non-empty config.tables list")
        return self


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    access_groups: list[str] | None = None
    schedule: SourceSchedule | None = None

    @field_validator("access_groups")
    @classmethod
    def normalize_access_groups(cls, groups: list[str] | None) -> list[str] | None:
        if groups is None:
            return None
        normalized = sorted({group.strip() for group in groups if group.strip()})
        if len(normalized) != len(groups):
            raise ValueError("access_groups must contain unique non-empty values")
        return normalized


class SourceRead(BaseModel):
    id: str
    name: str
    type: SourceType
    enabled: bool
    access_groups: list[str]
    document_count: int
    last_indexed_at: datetime | None


class SourceTestResponse(BaseModel):
    source_id: str
    ok: bool
    message: str

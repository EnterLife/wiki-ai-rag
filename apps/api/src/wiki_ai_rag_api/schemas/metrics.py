from pydantic import BaseModel, Field


class MetricsSnapshot(BaseModel):
    counters: dict[str, int] = Field(default_factory=dict)
    durations: dict[str, dict] = Field(default_factory=dict)


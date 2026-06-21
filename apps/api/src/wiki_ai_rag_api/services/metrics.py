from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Iterator


@dataclass
class DurationMetric:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def observe(self, elapsed_ms: float) -> None:
        self.count += 1
        self.total_ms += elapsed_ms
        self.max_ms = max(self.max_ms, elapsed_ms)

    def snapshot(self) -> dict:
        avg_ms = self.total_ms / self.count if self.count else 0.0
        return {
            "count": self.count,
            "total_ms": round(self.total_ms, 3),
            "avg_ms": round(avg_ms, 3),
            "max_ms": round(self.max_ms, 3),
        }


@dataclass
class MetricsRegistry:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    durations: dict[str, DurationMetric] = field(default_factory=lambda: defaultdict(DurationMetric))
    lock: Lock = field(default_factory=Lock)

    def increment(self, name: str, value: int = 1) -> None:
        with self.lock:
            self.counters[name] += value

    def observe_duration(self, name: str, elapsed_ms: float) -> None:
        with self.lock:
            self.durations[name].observe(elapsed_ms)

    @contextmanager
    def time_block(self, name: str) -> Iterator[None]:
        started_at = time.perf_counter()
        try:
            yield
        finally:
            self.observe_duration(name, (time.perf_counter() - started_at) * 1000)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "counters": dict(self.counters),
                "durations": {
                    name: metric.snapshot()
                    for name, metric in self.durations.items()
                },
            }

    def reset(self) -> None:
        with self.lock:
            self.counters.clear()
            self.durations.clear()


metrics_registry = MetricsRegistry()


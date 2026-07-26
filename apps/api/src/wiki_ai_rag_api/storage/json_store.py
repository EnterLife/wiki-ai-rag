from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_state()

        with self.path.open("r", encoding="utf-8") as state_file:
            return self._normalize_state(json.load(state_file))

    def write(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=self.path.parent,
            suffix=".tmp",
        ) as temp_file:
            json.dump(state, temp_file, ensure_ascii=False, indent=2)
            temp_path = Path(temp_file.name)

        temp_path.replace(self.path)

    def list_sources(self) -> list[dict[str, Any]]:
        return deepcopy(self.read()["sources"])

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        return next((source for source in self.read()["sources"] if source["id"] == source_id), None)

    def save_source(self, source: dict[str, Any]) -> dict[str, Any]:
        state = self.read()
        state["sources"].append(source)
        self.write(state)
        return deepcopy(source)

    def update_source(self, source_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        state = self.read()
        for source in state["sources"]:
            if source["id"] == source_id:
                source.update(updates)
                self.write(state)
                return deepcopy(source)
        return None

    def delete_source(self, source_id: str) -> bool:
        state = self.read()
        initial_count = len(state["sources"])
        state["sources"] = [source for source in state["sources"] if source["id"] != source_id]
        state["chunks"] = [chunk for chunk in state["chunks"] if chunk["source_id"] != source_id]
        if len(state["sources"]) == initial_count:
            return False
        self.write(state)
        return True

    def save_job(self, job: dict[str, Any]) -> dict[str, Any]:
        state = self.read()
        state["jobs"].append(job)
        self.write(state)
        return deepcopy(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return next((job for job in self.read()["jobs"] if job["job_id"] == job_id), None)

    def list_jobs(self, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        jobs = self.read()["jobs"]
        if source_id:
            jobs = [job for job in jobs if job["source_id"] == source_id]
        return deepcopy(jobs[-limit:])

    def update_job(self, job_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        state = self.read()
        for job in state["jobs"]:
            if job["job_id"] == job_id:
                job.update(updates)
                self.write(state)
                return deepcopy(job)
        return None

    def replace_chunks_for_source(self, source_id: str, chunks: list[dict[str, Any]]) -> None:
        state = self.read()
        state["chunks"] = [chunk for chunk in state["chunks"] if chunk["source_id"] != source_id]
        state["chunks"].extend(chunks)
        self.write(state)

    def list_chunks(self) -> list[dict[str, Any]]:
        return deepcopy(self.read()["chunks"])

    def append_audit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        state = self.read()
        state["audit_log"].append(event)
        self.write(state)
        return deepcopy(event)

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        events = self.read()["audit_log"]
        return deepcopy(events[-limit:])

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {"sources": [], "jobs": [], "chunks": [], "audit_log": []}

    @classmethod
    def _normalize_state(cls, state: dict[str, Any]) -> dict[str, Any]:
        empty_state = cls._empty_state()
        for key, value in empty_state.items():
            state.setdefault(key, value)
        return state

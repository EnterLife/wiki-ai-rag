from pathlib import Path

from sqlalchemy import create_engine

from wiki_ai_rag_api.storage.postgres_store import PostgresMetadataStore


def test_sql_metadata_store_persists_sources_jobs_and_audit(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.db'}")
    store = PostgresMetadataStore("sqlite://", engine=engine)
    source = {"id": "src_1", "name": "Wiki", "enabled": True}
    job = {
        "job_id": "job_1",
        "source_id": "src_1",
        "started_at": "2026-01-01T00:00:00+00:00",
        "status": "running",
    }
    event = {
        "id": "audit_1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "action": "source.create",
    }

    store.save_source(source)
    store.save_job(job)
    store.append_audit_event(event)
    updated_source = store.update_source("src_1", {"enabled": False})
    updated_job = store.update_job("job_1", {"status": "completed"})

    assert updated_source is not None and updated_source["enabled"] is False
    assert updated_job is not None and updated_job["status"] == "completed"
    assert store.list_sources()[0]["name"] == "Wiki"
    assert store.list_jobs(source_id="src_1")[0]["job_id"] == "job_1"
    assert store.list_audit_events()[0]["id"] == "audit_1"
    assert store.delete_source("src_1") is True
    assert store.get_source("src_1") is None

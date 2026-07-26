CREATE TABLE IF NOT EXISTS rag_sources (
    id VARCHAR(64) PRIMARY KEY,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_indexing_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL,
    started_at VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_rag_indexing_jobs_source_id
    ON rag_indexing_jobs (source_id);
CREATE INDEX IF NOT EXISTS ix_rag_indexing_jobs_started_at
    ON rag_indexing_jobs (started_at);

CREATE TABLE IF NOT EXISTS rag_audit_events (
    id VARCHAR(64) PRIMARY KEY,
    created_at VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_rag_audit_events_created_at
    ON rag_audit_events (created_at);

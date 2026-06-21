export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type Citation = {
  id: string;
  chunk_id: string;
  document_id: string;
  source_id: string;
  title: string;
  section?: string | null;
  url?: string | null;
  quote: string;
  timestamp?: string | null;
  score?: number | null;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  status: "answered" | "insufficient_context" | "error";
  confidence?: number | null;
  insufficient_context_reason?: string | null;
};

export type Source = {
  id: string;
  name: string;
  type: "filesystem" | "postgresql" | "mysql" | "sqlite" | "wiki" | "transcript";
  enabled: boolean;
  document_count: number;
  last_indexed_at?: string | null;
};

export type SourceTestResponse = {
  source_id: string;
  ok: boolean;
  message: string;
};

export type IndexingJob = {
  job_id: string;
  source_id: string;
  status: string;
  processed_documents: number;
  failed_documents: number;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
};

export type AuditEvent = {
  id: string;
  action: string;
  target_type: string;
  target_id: string;
  status: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type MetricsSnapshot = {
  counters: Record<string, number>;
  durations: Record<string, { count: number; total_ms: number; avg_ms: number; max_ms: number }>;
};

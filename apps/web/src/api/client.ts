import type { AskResponse, AuditEvent, IndexingJob, MetricsSnapshot, Source, SourceTestResponse } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function ensureOk(response: Response): Promise<void> {
  if (response.ok) return;

  let message = `API request failed: ${response.status}`;
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      message = payload.detail;
    } else if (Array.isArray(payload.detail)) {
      message = payload.detail.map((item: { msg?: string }) => item.msg ?? "Validation error").join("; ");
    }
  } catch {
    // Keep the default message for non-JSON errors.
  }

  throw new ApiError(message, response.status);
}

function authHeaders(): HeadersInit {
  const token = sessionStorage.getItem("wiki-ai-rag-access-token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function askQuestion(
  question: string,
  sourceIds?: string[],
  sessionId?: string,
): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      question,
      source_ids: sourceIds?.length ? sourceIds : undefined,
      session_id: sessionId,
      top_k: 8,
    }),
  });

  await ensureOk(response);

  return response.json() as Promise<AskResponse>;
}

export async function listSources(): Promise<Source[]> {
  const response = await fetch(`${API_BASE_URL}/sources/available`, {
    headers: authHeaders(),
  });
  await ensureOk(response);
  return response.json() as Promise<Source[]>;
}

export async function createFilesystemSource(
  name: string,
  path: string,
  schedule: { mode: "manual" } | { mode: "scheduled"; interval_hours: number },
  accessGroups: string[] = [],
): Promise<Source> {
  const response = await fetch(`${API_BASE_URL}/sources`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      name,
      type: "filesystem",
      config: { path },
      enabled: true,
      access_groups: accessGroups,
      schedule,
    }),
  });

  await ensureOk(response);

  return response.json() as Promise<Source>;
}

export async function createPostgresSource(
  payload: {
    name: string;
    host: string;
    port: number;
    database: string;
    username: string;
    password: string;
    tableName: string;
    idField: string;
    titleField?: string;
    textFields: string[];
    metadataFields: string[];
    limit?: number;
  },
  schedule: { mode: "manual" } | { mode: "scheduled"; interval_hours: number },
  accessGroups: string[] = [],
): Promise<Source> {
  const tableConfig: Record<string, unknown> = {
    name: payload.tableName,
    id_field: payload.idField,
    text_fields: payload.textFields,
    metadata_fields: payload.metadataFields,
  };
  if (payload.titleField) tableConfig.title_field = payload.titleField;
  if (payload.limit) tableConfig.limit = payload.limit;

  const response = await fetch(`${API_BASE_URL}/sources`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      name: payload.name,
      type: "postgresql",
      config: {
        host: payload.host,
        port: payload.port,
        database: payload.database,
        username: payload.username,
        password: payload.password,
        tables: [tableConfig],
      },
      enabled: true,
      access_groups: accessGroups,
      schedule,
    }),
  });

  await ensureOk(response);

  return response.json() as Promise<Source>;
}

export async function createSQLiteSource(
  payload: {
    name: string;
    databasePath: string;
    tableName: string;
    idField: string;
    titleField?: string;
    textFields: string[];
    metadataFields: string[];
    limit?: number;
  },
  schedule: { mode: "manual" } | { mode: "scheduled"; interval_hours: number },
  accessGroups: string[] = [],
): Promise<Source> {
  const tableConfig: Record<string, unknown> = {
    name: payload.tableName,
    id_field: payload.idField,
    text_fields: payload.textFields,
    metadata_fields: payload.metadataFields,
  };
  if (payload.titleField) tableConfig.title_field = payload.titleField;
  if (payload.limit) tableConfig.limit = payload.limit;

  const response = await fetch(`${API_BASE_URL}/sources`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      name: payload.name,
      type: "sqlite",
      config: {
        database_path: payload.databasePath,
        tables: [tableConfig],
      },
      enabled: true,
      access_groups: accessGroups,
      schedule,
    }),
  });

  await ensureOk(response);

  return response.json() as Promise<Source>;
}

export async function testSource(sourceId: string): Promise<SourceTestResponse> {
  const response = await fetch(`${API_BASE_URL}/sources/${sourceId}/test`, {
    method: "POST",
    headers: authHeaders(),
  });

  await ensureOk(response);

  return response.json() as Promise<SourceTestResponse>;
}

export async function updateSource(sourceId: string, payload: Partial<Pick<Source, "enabled" | "name">>): Promise<Source> {
  const response = await fetch(`${API_BASE_URL}/sources/${sourceId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });

  await ensureOk(response);

  return response.json() as Promise<Source>;
}

export async function runIndexing(sourceId: string): Promise<IndexingJob> {
  const response = await fetch(`${API_BASE_URL}/indexing/jobs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ source_id: sourceId, mode: "full" }),
  });

  await ensureOk(response);

  return response.json() as Promise<IndexingJob>;
}

export async function listIndexingJobs(): Promise<IndexingJob[]> {
  const response = await fetch(`${API_BASE_URL}/indexing/jobs`, {
    headers: authHeaders(),
  });

  await ensureOk(response);

  return response.json() as Promise<IndexingJob[]>;
}

export async function deleteSource(sourceId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sources/${sourceId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  await ensureOk(response);
}

export async function listAuditEvents(): Promise<AuditEvent[]> {
  const response = await fetch(`${API_BASE_URL}/audit?limit=5`, {
    headers: authHeaders(),
  });
  await ensureOk(response);
  return response.json() as Promise<AuditEvent[]>;
}

export async function getMetrics(): Promise<MetricsSnapshot> {
  const response = await fetch(`${API_BASE_URL}/metrics`, {
    headers: authHeaders(),
  });
  await ensureOk(response);
  return response.json() as Promise<MetricsSnapshot>;
}

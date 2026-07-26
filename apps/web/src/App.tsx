import { CheckCircle2, Database, FileText, LogIn, LogOut, Play, Plus, RefreshCw, Send, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  ApiError,
  askQuestion,
  createFilesystemSource,
  createPostgresSource,
  createSQLiteSource,
  deleteSource,
  getMetrics,
  listAuditEvents,
  listIndexingJobs,
  listSources,
  runIndexing,
  testSource,
  updateSource,
} from "./api/client";
import type { AskResponse, AuditEvent, ChatMessage, IndexingJob, MetricsSnapshot, Source } from "./types";
import { oidcIsConfigured, signIn, signOut } from "./auth";

const initialMessages: ChatMessage[] = [
  {
    role: "assistant",
    content: "Задайте вопрос по подключенной базе знаний. Я отвечу только при наличии источников.",
  },
];

export function App() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<AskResponse | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [jobs, setJobs] = useState<IndexingJob[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [sourceType, setSourceType] = useState<"filesystem" | "postgresql" | "sqlite">("filesystem");
  const [sourceName, setSourceName] = useState("Local Wiki");
  const [sourceAccessGroups, setSourceAccessGroups] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [pgHost, setPgHost] = useState("localhost");
  const [pgPort, setPgPort] = useState(5432);
  const [pgDatabase, setPgDatabase] = useState("");
  const [pgUsername, setPgUsername] = useState("");
  const [pgPassword, setPgPassword] = useState("");
  const [pgTable, setPgTable] = useState("public.pages");
  const [pgIdField, setPgIdField] = useState("id");
  const [pgTitleField, setPgTitleField] = useState("title");
  const [pgTextFields, setPgTextFields] = useState("body");
  const [pgMetadataFields, setPgMetadataFields] = useState("url,section,updated_at");
  const [pgLimit, setPgLimit] = useState(1000);
  const [sqlitePath, setSqlitePath] = useState("");
  const [sqliteTable, setSqliteTable] = useState("pages");
  const [sqliteIdField, setSqliteIdField] = useState("id");
  const [sqliteTitleField, setSqliteTitleField] = useState("title");
  const [sqliteTextFields, setSqliteTextFields] = useState("body");
  const [sqliteMetadataFields, setSqliteMetadataFields] = useState("url,section,updated_at");
  const [sqliteLimit, setSqliteLimit] = useState(1000);
  const [isScheduled, setIsScheduled] = useState(false);
  const [intervalHours, setIntervalHours] = useState(6);
  const [sourceStatus, setSourceStatus] = useState("Источники не загружены");
  const [isAuthenticated] = useState(
    () => sessionStorage.getItem("wiki-ai-rag-access-token") !== null,
  );

  useEffect(() => {
    void refreshSources();
  }, []);

  async function refreshSources() {
    try {
      const nextSources = await listSources();
      const [jobsResult, auditResult, metricsResult] = await Promise.allSettled([
        listIndexingJobs(),
        listAuditEvents(),
        getMetrics(),
      ]);
      setSources(nextSources);
      if (jobsResult.status === "fulfilled") {
        setJobs(jobsResult.value.slice(-5).reverse());
      }
      if (auditResult.status === "fulfilled") {
        setAuditEvents(auditResult.value.slice(-5).reverse());
      }
      if (metricsResult.status === "fulfilled") {
        setMetrics(metricsResult.value);
      }
      setSourceStatus(nextSources.length ? "Источники загружены" : "Источники пока не добавлены");
    } catch (error) {
      setSourceStatus(errorMessage(error, "API источников недоступен"));
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) return;

    setMessages((current) => [...current, { role: "user", content: trimmedQuestion }]);
    setQuestion("");
    setIsLoading(true);

    try {
      const response = await askQuestion(trimmedQuestion, selectedSourceIds, sessionId);
      setLastResponse(response);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } catch (error) {
      const fallback = errorMessage(error, "Не удалось получить ответ от API.");
      setLastResponse(null);
      setMessages((current) => [...current, { role: "assistant", content: fallback }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sourceName.trim()) return;

    setSourceStatus("Добавляю источник...");
    try {
      const schedule = isScheduled
        ? { mode: "scheduled" as const, interval_hours: intervalHours }
        : { mode: "manual" as const };
      if (sourceType === "filesystem") {
        if (!sourcePath.trim()) return;
        await createFilesystemSource(
          sourceName.trim(),
          sourcePath.trim(),
          schedule,
          splitCsv(sourceAccessGroups),
        );
        setSourcePath("");
      } else if (sourceType === "postgresql") {
        await createPostgresSource(
          {
            name: sourceName.trim(),
            host: pgHost.trim(),
            port: pgPort,
            database: pgDatabase.trim(),
            username: pgUsername.trim(),
            password: pgPassword,
            tableName: pgTable.trim(),
            idField: pgIdField.trim(),
            titleField: pgTitleField.trim() || undefined,
            textFields: splitCsv(pgTextFields),
            metadataFields: splitCsv(pgMetadataFields),
            limit: pgLimit || undefined,
          },
          schedule,
          splitCsv(sourceAccessGroups),
        );
        setPgPassword("");
      } else {
        await createSQLiteSource(
          {
            name: sourceName.trim(),
            databasePath: sqlitePath.trim(),
            tableName: sqliteTable.trim(),
            idField: sqliteIdField.trim(),
            titleField: sqliteTitleField.trim() || undefined,
            textFields: splitCsv(sqliteTextFields),
            metadataFields: splitCsv(sqliteMetadataFields),
            limit: sqliteLimit || undefined,
          },
          schedule,
          splitCsv(sourceAccessGroups),
        );
      }
      await refreshSources();
    } catch (error) {
      setSourceStatus(errorMessage(error, "Не удалось добавить источник"));
    }
  }

  async function handleTestSource(sourceId: string) {
    setSourceStatus("Проверяю подключение...");
    try {
      const result = await testSource(sourceId);
      setSourceStatus(result.ok ? "Подключение работает" : result.message);
    } catch (error) {
      setSourceStatus(errorMessage(error, "Не удалось проверить источник"));
    }
  }

  async function handleRunIndexing(sourceId: string) {
    setSourceStatus("Индексирую источник...");
    try {
      const job = await runIndexing(sourceId);
      setSourceStatus(
        job.status === "completed" || job.status === "completed_with_errors"
          ? `Индексация завершена: ${job.processed_documents}, ошибок: ${job.failed_documents}`
          : `Индексация: ${job.status}`,
      );
      await refreshSources();
    } catch (error) {
      setSourceStatus(errorMessage(error, "Не удалось запустить индексацию"));
    }
  }

  async function handleDeleteSource(sourceId: string) {
    setSourceStatus("Удаляю источник...");
    try {
      await deleteSource(sourceId);
      await refreshSources();
    } catch (error) {
      setSourceStatus(errorMessage(error, "Не удалось удалить источник"));
    }
  }

  async function handleToggleSource(source: Source) {
    setSourceStatus(source.enabled ? "Отключаю источник..." : "Включаю источник...");
    try {
      await updateSource(source.id, { enabled: !source.enabled });
      await refreshSources();
    } catch (error) {
      setSourceStatus(errorMessage(error, "Не удалось изменить источник"));
    }
  }

  function handleFilterSource(sourceId: string) {
    setSelectedSourceIds((current) =>
      current.includes(sourceId)
        ? current.filter((currentSourceId) => currentSourceId !== sourceId)
        : [...current, sourceId],
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Источники и индексация">
        <div className="brand">
          <Database size={22} />
          <span>Wiki AI RAG</span>
          {oidcIsConfigured() ? (
            <button
              className="auth-button"
              onClick={() => void (isAuthenticated ? signOut() : signIn())}
              title={isAuthenticated ? "Выйти" : "Войти"}
              type="button"
            >
              {isAuthenticated ? <LogOut size={16} /> : <LogIn size={16} />}
            </button>
          ) : null}
        </div>

        <section className="source-panel">
          <div className="panel-title">
            <FileText size={18} />
            <h2>Источники</h2>
          </div>

          <form className="source-form" onSubmit={handleCreateSource}>
            <select
              aria-label="Тип источника"
              value={sourceType}
              onChange={(event) =>
                setSourceType(event.target.value as "filesystem" | "postgresql" | "sqlite")
              }
            >
              <option value="filesystem">Filesystem</option>
              <option value="postgresql">PostgreSQL</option>
              <option value="sqlite">SQLite</option>
            </select>
            <input
              aria-label="Название источника"
              value={sourceName}
              onChange={(event) => setSourceName(event.target.value)}
            />
            <input
              aria-label="Группы доступа"
              placeholder="engineering,finance (пусто — все пользователи)"
              value={sourceAccessGroups}
              onChange={(event) => setSourceAccessGroups(event.target.value)}
            />
            {sourceType === "filesystem" ? (
              <input
                aria-label="Путь к директории"
                placeholder="C:\\data\\wiki"
                value={sourcePath}
                onChange={(event) => setSourcePath(event.target.value)}
              />
            ) : sourceType === "postgresql" ? (
              <div className="postgres-fields">
                <input
                  aria-label="PostgreSQL host"
                  placeholder="host"
                  value={pgHost}
                  onChange={(event) => setPgHost(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL port"
                  min={1}
                  type="number"
                  value={pgPort}
                  onChange={(event) => setPgPort(Number(event.target.value))}
                />
                <input
                  aria-label="PostgreSQL database"
                  placeholder="database"
                  value={pgDatabase}
                  onChange={(event) => setPgDatabase(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL username"
                  placeholder="username"
                  value={pgUsername}
                  onChange={(event) => setPgUsername(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL password"
                  placeholder="password"
                  type="password"
                  value={pgPassword}
                  onChange={(event) => setPgPassword(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL table"
                  placeholder="public.pages"
                  value={pgTable}
                  onChange={(event) => setPgTable(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL id field"
                  placeholder="id field"
                  value={pgIdField}
                  onChange={(event) => setPgIdField(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL title field"
                  placeholder="title field"
                  value={pgTitleField}
                  onChange={(event) => setPgTitleField(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL text fields"
                  placeholder="body,content"
                  value={pgTextFields}
                  onChange={(event) => setPgTextFields(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL metadata fields"
                  placeholder="url,section,updated_at"
                  value={pgMetadataFields}
                  onChange={(event) => setPgMetadataFields(event.target.value)}
                />
                <input
                  aria-label="PostgreSQL row limit"
                  min={1}
                  type="number"
                  value={pgLimit}
                  onChange={(event) => setPgLimit(Number(event.target.value))}
                />
              </div>
            ) : (
              <div className="postgres-fields">
                <input
                  aria-label="SQLite database path"
                  placeholder="C:\\data\\wiki.sqlite"
                  value={sqlitePath}
                  onChange={(event) => setSqlitePath(event.target.value)}
                />
                <input
                  aria-label="SQLite table"
                  placeholder="pages"
                  value={sqliteTable}
                  onChange={(event) => setSqliteTable(event.target.value)}
                />
                <input
                  aria-label="SQLite id field"
                  placeholder="id field"
                  value={sqliteIdField}
                  onChange={(event) => setSqliteIdField(event.target.value)}
                />
                <input
                  aria-label="SQLite title field"
                  placeholder="title field"
                  value={sqliteTitleField}
                  onChange={(event) => setSqliteTitleField(event.target.value)}
                />
                <input
                  aria-label="SQLite text fields"
                  placeholder="body,content"
                  value={sqliteTextFields}
                  onChange={(event) => setSqliteTextFields(event.target.value)}
                />
                <input
                  aria-label="SQLite metadata fields"
                  placeholder="url,section,updated_at"
                  value={sqliteMetadataFields}
                  onChange={(event) => setSqliteMetadataFields(event.target.value)}
                />
                <input
                  aria-label="SQLite row limit"
                  min={1}
                  type="number"
                  value={sqliteLimit}
                  onChange={(event) => setSqliteLimit(Number(event.target.value))}
                />
              </div>
            )}
            <label className="schedule-toggle">
              <input
                checked={isScheduled}
                type="checkbox"
                onChange={(event) => setIsScheduled(event.target.checked)}
              />
              <span>По расписанию</span>
            </label>
            {isScheduled ? (
              <input
                aria-label="Интервал обновления в часах"
                min={1}
                type="number"
                value={intervalHours}
                onChange={(event) => setIntervalHours(Number(event.target.value))}
              />
            ) : null}
            <button className="secondary-button" type="submit">
              <Plus size={16} />
              Добавить
            </button>
          </form>

          <div className="source-status">{sourceStatus}</div>

          <div className="source-list">
            {sources.length ? (
              sources.map((source) => (
                <article className="source-item" key={source.id}>
                  <div>
                    <strong>{source.name}</strong>
                    <span>
                      {source.type} · {source.document_count} · {source.enabled ? "on" : "off"}
                    </span>
                    {source.last_indexed_at ? <span>{formatDate(source.last_indexed_at)}</span> : null}
                  </div>
                  <div className="source-actions">
                    <button
                      aria-label={`Проверить ${source.name}`}
                      className="icon-button"
                      type="button"
                      disabled={!source.enabled}
                      onClick={() => void handleTestSource(source.id)}
                    >
                      <CheckCircle2 size={16} />
                    </button>
                    <button
                      aria-label={`Индексировать ${source.name}`}
                      className="icon-button"
                      type="button"
                      disabled={!source.enabled}
                      onClick={() => void handleRunIndexing(source.id)}
                    >
                      <Play size={16} />
                    </button>
                    <button
                      aria-label={source.enabled ? `Отключить ${source.name}` : `Включить ${source.name}`}
                      className="icon-button"
                      type="button"
                      onClick={() => void handleToggleSource(source)}
                    >
                      {source.enabled ? "On" : "Off"}
                    </button>
                    <button
                      aria-label={`Удалить ${source.name}`}
                      className="icon-button icon-button-danger"
                      type="button"
                      onClick={() => void handleDeleteSource(source.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <div className="empty-state">Добавьте директорию с Markdown или TXT файлами.</div>
            )}
          </div>

          <button className="secondary-button" type="button" onClick={() => void refreshSources()}>
            <RefreshCw size={16} />
            Обновить
          </button>

          {jobs.length ? (
            <section className="jobs-panel" aria-label="История индексации">
              <h2>Индексация</h2>
              {jobs.map((job) => (
                <article className="job-item" key={job.job_id}>
                  <strong>{job.status}</strong>
                  <span>{job.source_id}</span>
                  <span>
                    {job.processed_documents} / {job.failed_documents}
                  </span>
                </article>
              ))}
            </section>
          ) : null}

          {metrics ? (
            <section className="jobs-panel" aria-label="Метрики">
              <h2>Метрики</h2>
              {Object.entries(metrics.counters)
                .slice(0, 5)
                .map(([name, value]) => (
                  <article className="job-item" key={name}>
                    <strong>{name}</strong>
                    <span>{value}</span>
                  </article>
                ))}
            </section>
          ) : null}

          {auditEvents.length ? (
            <section className="jobs-panel" aria-label="Audit log">
              <h2>Audit</h2>
              {auditEvents.map((event) => (
                <article className="job-item" key={event.id}>
                  <strong>{event.action}</strong>
                  <span>{event.status}</span>
                  <span>{event.target_id}</span>
                </article>
              ))}
            </section>
          ) : null}
        </section>
      </aside>

      <section className="chat-layout" aria-label="Чат">
        {sources.some((source) => source.enabled) ? (
          <section className="source-filter" aria-label="Фильтр источников">
            {sources
              .filter((source) => source.enabled)
              .map((source) => (
                <label key={source.id}>
                  <input
                    checked={selectedSourceIds.includes(source.id)}
                    type="checkbox"
                    onChange={() => handleFilterSource(source.id)}
                  />
                  <span>{source.name}</span>
                </label>
              ))}
          </section>
        ) : null}

        <div className="message-list">
          {messages.map((message, index) => (
            <article className={`message message-${message.role}`} key={`${message.role}-${index}`}>
              <div className="message-author">
                {message.role === "user" ? "Пользователь" : "Wiki AI RAG"}
              </div>
              <p>{message.content}</p>
            </article>
          ))}
          {isLoading && (
            <article className="message message-assistant">
              <div className="message-author">Wiki AI RAG</div>
              <p>Ищу релевантные фрагменты...</p>
            </article>
          )}
        </div>

        {lastResponse?.citations.length ? (
          <section className="citations" aria-label="Источники">
            <h2>Источники</h2>
            {lastResponse.citations.map((citation) => (
              <details key={citation.id}>
                <summary>
                  [{citation.id}] {citation.title}
                </summary>
                <div className="citation-meta">
                  <span>{citation.document_id}</span>
                  <span>{citation.chunk_id}</span>
                  {citation.section ? <span>{citation.section}</span> : null}
                  {citation.page ? <span>Страница {citation.page}</span> : null}
                  {citation.url ? (
                    <a href={citation.url} rel="noreferrer" target="_blank">
                      Открыть
                    </a>
                  ) : null}
                </div>
                <blockquote>{citation.quote}</blockquote>
              </details>
            ))}
          </section>
        ) : null}

        <form className="composer" onSubmit={handleSubmit}>
          <input
            aria-label="Введите вопрос"
            placeholder="Введите вопрос..."
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button aria-label="Отправить" disabled={isLoading} type="submit">
            <Send size={18} />
          </button>
        </form>
      </section>
    </main>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback;
}

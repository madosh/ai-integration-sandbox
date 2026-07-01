import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, streamRun, streamSearch } from "./api";
import { extractApprovalSpec, sendAguiInput, streamAgui, type AguiEvent } from "./agui";
import { A2uiApprovalCard, A2uiMetricCard } from "./A2uiRenderer";
import type { RunSummary } from "./types";

function formatDuration(run: RunSummary): string {
  const sec = Math.max(0, run.updated_at - run.created_at);
  return `${sec.toFixed(1)}s`;
}

// ── Metrics row ──────────────────────────────────────────────────────────────

function MetricsHeader() {
  const { data, error } = useQuery({
    queryKey: ["metrics"],
    queryFn: api.metrics,
    refetchInterval: 3000,
  });

  if (error) return <p className="error">Metrics unavailable</p>;
  if (!data) return null;

  const cards: Array<{ label: string; value: string }> = [
    { label: "Total runs",       value: String(data.total_runs) },
    { label: "Success rate",     value: `${(data.success_rate * 100).toFixed(0)}%` },
    { label: "Records synced",   value: String(data.records_synced) },
    { label: "Creatives pushed", value: String(data.creatives_pushed) },
    { label: "Est. value",       value: `$${data.estimated_value_usd.toFixed(2)}` },
    { label: "Avg duration",     value: `${data.avg_duration_sec.toFixed(1)}s` },
  ];

  return (
    <div className="metrics">
      {cards.map((c) => (
        <div className="metric-card" key={c.label}>
          <div className="label">{c.label}</div>
          <div className="value">{c.value}</div>
        </div>
      ))}
    </div>
  );
}

// ── Registry panel ───────────────────────────────────────────────────────────

function RegistryPanel() {
  const connectors = useQuery({ queryKey: ["connectors"], queryFn: api.connectors });
  const skills     = useQuery({ queryKey: ["skills"],     queryFn: api.skills });

  return (
    <div className="panel registry" style={{ marginTop: "1rem" }}>
      <div className="registry-section">
        <h2>Connectors</h2>
        <ul>
          {(connectors.data ?? []).map((c) => (
            <li key={c.name}>
              <span className="item-name">{c.name}</span>
            </li>
          ))}
          {connectors.data?.length === 0 && (
            <li><span className="text-muted">No connectors registered</span></li>
          )}
        </ul>
      </div>
      <div className="registry-section">
        <h2>Skills</h2>
        <ul>
          {(skills.data ?? []).map((s) => (
            <li key={s.name}>
              <span className="item-name">{s.name}</span>
              {s.side_effect && <span className="side-effect-badge">side-effect</span>}
            </li>
          ))}
          {skills.data?.length === 0 && (
            <li><span className="text-muted">No skills registered</span></li>
          )}
        </ul>
      </div>
    </div>
  );
}

// ── Run detail ───────────────────────────────────────────────────────────────

function RunDetail({
  run,
  onRefresh,
}: {
  run: RunSummary | null;
  onRefresh: () => void;
}) {
  const approve = useMutation({
    mutationFn: ({ id, ok }: { id: string; ok: boolean }) =>
      sendAguiInput(id, ok ? "approve" : "deny").catch(() => api.approveRun(id, ok)),
    onSuccess: () => onRefresh(),
  });

  const [aguiEvents, setAguiEvents] = useState<AguiEvent[]>([]);
  const approvalSpec = extractApprovalSpec(aguiEvents);

  useEffect(() => {
    if (!run) return;
    setAguiEvents([]);
    return streamAgui(run.run_id, (ev) => setAguiEvents((prev) => [...prev, ev]));
  }, [run?.run_id]);

  if (!run) {
    return (
      <div className="empty-state">
        <div className="empty-icon">↖</div>
        <p>Select a run to inspect the trace.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="run-detail-header">
        <p className="run-detail-id">run / {run.run_id}</p>
        <p className="run-detail-goal">{run.goal}</p>
        <div className="run-detail-meta">
          <span className={`status ${run.status}`}>{run.status}</span>
          <span>·</span>
          <span>{formatDuration(run)}</span>
          <span>·</span>
          <span>{run.steps.length} steps</span>
        </div>
      </div>

      {run.pending_approval && approvalSpec ? (
        <A2uiApprovalCard
          spec={approvalSpec}
          busy={approve.isPending}
          onApprove={() => approve.mutate({ id: run.run_id, ok: true })}
          onDeny={() => approve.mutate({ id: run.run_id, ok: false })}
        />
      ) : run.pending_approval ? (
        <div className="approval-box">
          <strong>Pending approval</strong>
          <p>A side-effecting step requires human sign-off before it can proceed.</p>
          <div className="actions">
            <button
              className="primary"
              disabled={approve.isPending}
              onClick={() => approve.mutate({ id: run.run_id, ok: true })}
            >
              Approve
            </button>
            <button
              className="danger"
              disabled={approve.isPending}
              onClick={() => approve.mutate({ id: run.run_id, ok: false })}
            >
              Deny
            </button>
          </div>
        </div>
      ) : null}

      {aguiEvents
        .filter(
          (e) =>
            e.type === "CUSTOM" &&
            (e.payload.component as { component?: string })?.component === "MetricCard",
        )
        .map((e, i) => (
          <A2uiMetricCard
            key={i}
            spec={e.payload.component as import("./agui").A2uiSpec}
          />
        ))}

      {run.steps.length > 0 && (
        <>
          <p className="step-header">Trace</p>
          <ul className="steps">
            {run.steps.map((s) => (
              <li key={s.index} data-kind={s.kind}>
                <div className="step-dot" />
                <div className="step-body">
                  <div className="step-kind">{s.kind}</div>
                  <div className="step-message">
                    {s.skill && <strong>{s.skill} — </strong>}
                    {s.message}
                    {s.decision && (
                      <em className={s.decision.approved ? " text-success" : " text-danger"}>
                        {" "}
                        {s.decision.approved ? "(approved)" : "(denied)"}
                      </em>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

// ── Search panel ─────────────────────────────────────────────────────────────

function SearchPanel() {
  const [query,    setQuery]   = useState("What is our retry policy for HTTP 429?");
  const [streamed, setStreamed] = useState("");
  const [meta,     setMeta]    = useState("");

  const runSearch = () => {
    setStreamed("");
    setMeta("Searching…");
    streamSearch(
      query,
      (t) => setStreamed((s) => s + t),
      (m) => setMeta(`${String(m.chunks)} chunk${String(m.chunks) === "1" ? "" : "s"} retrieved`),
      () => setMeta((m) => m + " · done"),
    );
  };

  return (
    <div className="panel" style={{ marginTop: "1rem" }}>
      <h2>RAG search (streaming preview)</h2>
      <div className="new-run">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask something…"
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
        />
        <button className="primary" onClick={runSearch}>
          Search
        </button>
      </div>
      {meta && <p className="search-meta">{meta}</p>}
      {streamed && <div className="search-result">{streamed}</div>}
    </div>
  );
}

// ── App root ─────────────────────────────────────────────────────────────────

export function App() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [goal, setGoal]             = useState("publish the new creative to creativebox");
  const [liveRun, setLiveRun]       = useState<RunSummary | null>(null);

  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: api.listRuns,
    refetchInterval: 2000,
  });

  const startRun = useMutation({
    mutationFn: (g: string) => api.startRun(g),
    onSuccess: (data) => {
      setSelectedId(data.run_id);
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
    },
  });

  const selected =
    liveRun?.run_id === selectedId
      ? liveRun
      : (runs.data?.find((r) => r.run_id === selectedId) ?? null);

  useEffect(() => {
    if (!selectedId) return;
    const unsub = streamRun(selectedId, (updated) => {
      setLiveRun(updated);
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
    });
    return unsub;
  }, [selectedId, queryClient]);

  return (
    <div className="app">
      <header>
        <div className="header-brand">
          <h1>AI Integration Hub</h1>
          <p>Agent runs · approvals · RAG search · live metrics</p>
        </div>
        <div className="header-actions">
          <span className="live-indicator">
            <span className="live-dot" />
            live
          </span>
          <a
            className="header-link"
            href="https://github.com/madosh/ai-integration-sandbox"
            target="_blank"
            rel="noreferrer"
          >
            GitHub ↗
          </a>
        </div>
      </header>

      <div className="main-content">
        <MetricsHeader />

        <div className="layout">
          {/* Left: run list */}
          <div className="panel">
            <h2>Runs</h2>
            <div className="new-run">
              <input
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Agent goal…"
                onKeyDown={(e) => e.key === "Enter" && !startRun.isPending && startRun.mutate(goal)}
              />
              <button
                className="primary"
                disabled={startRun.isPending}
                onClick={() => startRun.mutate(goal)}
              >
                {startRun.isPending ? "Starting…" : "Start run"}
              </button>
            </div>

            {runs.error && <p className="error">Failed to load runs</p>}

            {runs.data?.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">▷</div>
                <p>No runs yet. Enter a goal above and click Start run.</p>
              </div>
            )}

            {(runs.data?.length ?? 0) > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>Goal</th>
                    <th>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {(runs.data ?? []).map((r) => (
                    <tr
                      key={r.run_id}
                      className={r.run_id === selectedId ? "selected" : ""}
                      onClick={() => {
                        setSelectedId(r.run_id);
                        setLiveRun(null);
                      }}
                    >
                      <td className="run-id-cell">{r.run_id}</td>
                      <td>
                        <span className={`status ${r.status}`}>{r.status}</span>
                      </td>
                      <td>{r.goal.length > 52 ? r.goal.slice(0, 52) + "…" : r.goal}</td>
                      <td className="text-muted">{formatDuration(r)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Right: run detail */}
          <div className="panel">
            <h2>Run detail</h2>
            <RunDetail
              run={selected}
              onRefresh={() => {
                queryClient.invalidateQueries({ queryKey: ["runs"] });
                queryClient.invalidateQueries({ queryKey: ["metrics"] });
              }}
            />
          </div>
        </div>

        <RegistryPanel />
        <SearchPanel />
      </div>

      <footer className="site-footer">
        AI Integration Sandbox — offline-first, spec-driven, no API keys needed.{" "}
        <a
          href="https://github.com/madosh/ai-integration-sandbox"
          target="_blank"
          rel="noreferrer"
        >
          View on GitHub
        </a>
      </footer>
    </div>
  );
}

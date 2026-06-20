import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, streamRun, streamSearch } from "./api";
import type { RunSummary } from "./types";

function formatDuration(run: RunSummary): string {
  const sec = Math.max(0, run.updated_at - run.created_at);
  return `${sec.toFixed(1)}s`;
}

function MetricsHeader() {
  const { data, error } = useQuery({
    queryKey: ["metrics"],
    queryFn: api.metrics,
    refetchInterval: 3000,
  });

  if (error) return <p className="error">Metrics unavailable</p>;
  if (!data) return null;

  return (
    <div className="metrics">
      <div className="metric-card">
        <div className="label">Total runs</div>
        <div className="value">{data.total_runs}</div>
      </div>
      <div className="metric-card">
        <div className="label">Success rate</div>
        <div className="value">{(data.success_rate * 100).toFixed(0)}%</div>
      </div>
      <div className="metric-card">
        <div className="label">Records synced</div>
        <div className="value">{data.records_synced}</div>
      </div>
      <div className="metric-card">
        <div className="label">Creatives pushed</div>
        <div className="value">{data.creatives_pushed}</div>
      </div>
      <div className="metric-card">
        <div className="label">Est. value (USD)</div>
        <div className="value">${data.estimated_value_usd.toFixed(1)}</div>
      </div>
    </div>
  );
}

function RegistryPanel() {
  const connectors = useQuery({ queryKey: ["connectors"], queryFn: api.connectors });
  const skills = useQuery({ queryKey: ["skills"], queryFn: api.skills });

  return (
    <div className="panel registry">
      <h2>Connectors</h2>
      <ul>
        {(connectors.data ?? []).map((c) => (
          <li key={c.name}>{c.name}</li>
        ))}
      </ul>
      <h2>Skills</h2>
      <ul>
        {(skills.data ?? []).map((s) => (
          <li key={s.name}>
            <strong>{s.name}</strong>
            {s.side_effect ? " (side-effect)" : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RunDetail({
  run,
  onRefresh,
}: {
  run: RunSummary | null;
  onRefresh: () => void;
}) {
  const approve = useMutation({
    mutationFn: ({ id, ok }: { id: string; ok: boolean }) => api.approveRun(id, ok),
    onSuccess: () => onRefresh(),
  });

  if (!run) return <p>Select a run to inspect the trace.</p>;

  return (
    <div>
      <h2>Run {run.run_id}</h2>
      <p><strong>Goal:</strong> {run.goal}</p>
      <p>
        <span className={`status ${run.status}`}>{run.status}</span>
        · {formatDuration(run)} · {run.steps.length} steps
      </p>

      {run.pending_approval && (
        <div className="approval-box">
          <strong>Pending approval</strong>
          <p>A side-effecting step requires human sign-off.</p>
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
      )}

      <ul className="steps">
        {run.steps.map((s) => (
          <li key={s.index}>
            <strong>[{s.kind}]</strong> {s.skill ?? ""} — {s.message}
            {s.decision && (
              <em> ({s.decision.approved ? "approved" : "denied"})</em>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SearchPanel() {
  const [query, setQuery] = useState("What is our retry policy for HTTP 429?");
  const [streamed, setStreamed] = useState("");
  const [meta, setMeta] = useState<string>("");

  const runSearch = () => {
    setStreamed("");
    setMeta("");
    streamSearch(
      query,
      (t) => setStreamed((s) => s + t),
      (m) => setMeta(`hits: ${String(m.chunks)}`),
      () => setMeta((m) => m + " · done"),
    );
  };

  return (
    <div className="panel" style={{ marginTop: "1rem" }}>
      <h2>RAG search (streaming preview)</h2>
      <div className="new-run">
        <input value={query} onChange={(e) => setQuery(e.target.value)} />
        <button className="primary" onClick={runSearch}>Search</button>
      </div>
      {meta && <p className="lead">{meta}</p>}
      {streamed && <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>{streamed}</pre>}
    </div>
  );
}

export function App() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [goal, setGoal] = useState("publish the new creative to creativebox");
  const [liveRun, setLiveRun] = useState<RunSummary | null>(null);

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
      : runs.data?.find((r) => r.run_id === selectedId) ?? null;

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
        <h1>AI Integration Hub</h1>
        <p>Monitoring — runs, approvals, metrics</p>
      </header>

      <MetricsHeader />

      <div className="layout">
        <div className="panel">
          <h2>Runs</h2>
          <div className="new-run">
            <input
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Agent goal…"
            />
            <button
              className="primary"
              disabled={startRun.isPending}
              onClick={() => startRun.mutate(goal)}
            >
              Start run
            </button>
          </div>
          {runs.error && <p className="error">Failed to load runs</p>}
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
                  <td>{r.run_id}</td>
                  <td>
                    <span className={`status ${r.status}`}>{r.status}</span>
                  </td>
                  <td>{r.goal.slice(0, 48)}</td>
                  <td>{formatDuration(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel">
          <RunDetail
            run={selected}
            onRefresh={() => {
              queryClient.invalidateQueries({ queryKey: ["runs"] });
              queryClient.invalidateQueries({ queryKey: ["metrics"] });
            }}
          />
        </div>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <RegistryPanel />
      </div>
      <SearchPanel />
    </div>
  );
}

import type {
  ConnectorInfo,
  Metrics,
  RunSummary,
  SearchResponse,
  SkillInfo,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  healthz: () => request<{ status: string }>("/healthz"),
  metrics: () => request<Metrics>("/metrics"),
  connectors: () => request<ConnectorInfo[]>("/connectors"),
  skills: () => request<SkillInfo[]>("/skills"),
  listRuns: () => request<RunSummary[]>("/runs"),
  getRun: (id: string) => request<RunSummary>(`/runs/${id}`),
  startRun: (goal: string) =>
    request<{ run_id: string; status: string }>("/runs", {
      method: "POST",
      body: JSON.stringify({ goal }),
    }),
  approveRun: (id: string, approved: boolean) =>
    request<{ run_id: string; approved: boolean; status: string }>(
      `/runs/${id}/approve`,
      { method: "POST", body: JSON.stringify({ approved }) },
    ),
  search: (query: string) =>
    request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ query, k: 5 }),
    }),
};

export function streamRun(
  runId: string,
  onUpdate: (run: RunSummary) => void,
): () => void {
  const es = new EventSource(`${BASE}/runs/${runId}/stream`);
  es.addEventListener("update", (ev) => {
    const data = JSON.parse((ev as MessageEvent).data) as RunSummary;
    onUpdate(data);
  });
  return () => es.close();
}

export function streamSearch(
  query: string,
  onToken: (token: string) => void,
  onMeta: (meta: Record<string, unknown>) => void,
  onDone: () => void,
): () => void {
  void fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, k: 5 }),
  })
    .then((r) => r.json())
    .then((data: SearchResponse) => {
      onMeta({ chunks: data.chunks.length, query: data.query });
      const text = data.chunks[0]?.text ?? "";
      const words = text.split(/\s+/);
      let i = 0;
      const tick = () => {
        if (i >= words.length) {
          onDone();
          return;
        }
        onToken(words[i] + " ");
        i += 1;
        setTimeout(tick, 30);
      };
      tick();
    });
  return () => undefined;
}

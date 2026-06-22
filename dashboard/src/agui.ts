import type { RunSummary } from "./types";

const BASE = "/api";

export type AguiEvent = {
  type: string;
  run_id: string;
  timestamp?: number;
  payload: Record<string, unknown>;
};

export type A2uiSpec = {
  component: string;
  action?: string;
  payload_preview?: Record<string, unknown>;
  reversibility?: string;
  approve_label?: string;
  deny_label?: string;
  description?: string;
  title?: string;
  metrics?: Record<string, unknown>;
};

export function streamAgui(
  runId: string,
  onEvent: (ev: AguiEvent) => void,
): () => void {
  const es = new EventSource(`${BASE}/agui/runs/${runId}/stream`);
  const handler = (ev: Event) => {
    try {
      const data = JSON.parse((ev as MessageEvent).data) as AguiEvent;
      onEvent(data);
    } catch {
      /* ignore malformed */
    }
  };
  [
    "RUN_STARTED",
    "RUN_FINISHED",
    "RUN_ERROR",
    "STEP_STARTED",
    "STEP_FINISHED",
    "INPUT_REQUEST",
    "STATE_SNAPSHOT",
    "STATE_DELTA",
    "CUSTOM",
    "ping",
  ].forEach((name) => es.addEventListener(name, handler));
  return () => es.close();
}

export async function sendAguiInput(
  runId: string,
  action: "approve" | "deny" | "cancel",
): Promise<{ run_id: string; status: string }> {
  const res = await fetch(`${BASE}/agui/runs/${runId}/input`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, decided_by: "dashboard" }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ run_id: string; status: string }>;
}

export function extractApprovalSpec(events: AguiEvent[]): A2uiSpec | null {
  for (const ev of events) {
    if (ev.type === "CUSTOM" && ev.payload.channel === "a2ui") {
      const comp = ev.payload.component as A2uiSpec;
      if (comp?.component === "ApprovalCard") return comp;
    }
  }
  return null;
}

export type { RunSummary };

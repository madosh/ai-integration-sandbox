export interface RunStep {
  index: number;
  kind: string;
  message: string;
  skill?: string | null;
  args?: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  approval?: Record<string, unknown> | null;
  decision?: { approved: boolean; decided_by?: string } | null;
  ts: number;
}

export interface RunSummary {
  run_id: string;
  goal: string;
  status: string;
  steps: RunStep[];
  value_summary: Record<string, number>;
  created_at: number;
  updated_at: number;
  pending_approval: boolean;
}

export interface Metrics {
  total_runs: number;
  success_rate: number;
  records_synced: number;
  creatives_pushed: number;
  estimated_value_usd: number;
  avg_duration_sec: number;
}

export interface ConnectorInfo {
  name: string;
}

export interface SkillInfo {
  name: string;
  description: string;
  side_effect: boolean;
}

export interface SearchChunk {
  text: string;
  score: number;
  doc_id?: string | null;
  chunk_id?: string | null;
  source?: string | null;
}

export interface SearchResponse {
  query: string;
  chunks: SearchChunk[];
  deterministic?: Record<string, string> | null;
}

export interface ConnectorHealth {
  name: string;
  status: "healthy" | "degraded" | "circuit_open" | "unknown";
  upstream_ok?: boolean;
  circuit?: { open: boolean; failure_count: number; threshold: number };
  error?: string | null;
}

export interface ChatCitation {
  source: string;
  doc_id?: string | null;
  chunk_id?: string | null;
  score?: number | null;
}

export interface ChatResponse {
  thread_id: string;
  answer: string;
  citations: ChatCitation[];
  deterministic?: Record<string, string> | null;
  turns: number;
}

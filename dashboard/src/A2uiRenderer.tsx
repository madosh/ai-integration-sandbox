import type { A2uiSpec } from "./agui";

type Props = {
  spec: A2uiSpec;
  onApprove: () => void;
  onDeny: () => void;
  busy?: boolean;
};

/** Generic A2UI renderer — ApprovalCard only for now; driven by agent-emitted spec. */
export function A2uiApprovalCard({ spec, onApprove, onDeny, busy }: Props) {
  return (
    <div className="approval-box a2ui-card">
      <strong>{spec.component}</strong>
      <p>{spec.description ?? `Action: ${spec.action}`}</p>
      {spec.payload_preview && (
        <pre className="a2ui-preview">{JSON.stringify(spec.payload_preview, null, 2)}</pre>
      )}
      <p className="muted">Reversibility: {spec.reversibility ?? "unknown"}</p>
      <div className="actions">
        <button className="primary" disabled={busy} onClick={onApprove}>
          {spec.approve_label ?? "Approve"}
        </button>
        <button className="danger" disabled={busy} onClick={onDeny}>
          {spec.deny_label ?? "Deny"}
        </button>
      </div>
    </div>
  );
}

export function A2uiMetricCard({ spec }: { spec: A2uiSpec }) {
  return (
    <div className="metric-card a2ui-card">
      <div className="label">{spec.title ?? "Metrics"}</div>
      <pre className="a2ui-preview">{JSON.stringify(spec.metrics ?? {}, null, 2)}</pre>
    </div>
  );
}

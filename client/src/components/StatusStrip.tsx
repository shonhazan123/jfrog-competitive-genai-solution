import type { RunStatus } from "../api/types";

interface StatusStripProps {
  data: RunStatus;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    day: "numeric",
    month: "short",
  });
}

export function StatusStrip({ data }: StatusStripProps) {
  const lastRunAt = data.finished_at ?? data.started_at;

  const handleRunNow = () => {
    // POST /runs has no fixture — safe no-op in fixture mode
  };

  return (
    <div
      className="status-strip-content"
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "var(--sp-3)",
        fontSize: "var(--fs-meta)",
        lineHeight: "var(--lh-meta)",
        color: "var(--ink-secondary)",
      }}
    >
      <span>
        Last run: {formatTimestamp(lastRunAt)} · {data.sources_count} sources
        {data.live ? " · live" : ""}
      </span>
      <span>Next run: {formatTimestamp(data.next_run_at)}</span>
      <button
        type="button"
        onClick={handleRunNow}
        style={{
          padding: "var(--sp-1) var(--sp-3)",
          fontSize: "var(--fs-meta)",
          fontWeight: 500,
          color: "var(--accent)",
          background: "var(--accent-wash)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-sm)",
          cursor: "pointer",
        }}
      >
        Run now
      </button>
    </div>
  );
}

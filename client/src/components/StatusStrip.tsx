import { useState } from "react";
import type { RunStatus } from "../api/types";
import { useRunStore } from "../state/runStore";

interface StatusStripProps {
  data?: RunStatus;
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
  const store = useRunStore();
  const [error, setError] = useState<string | null>(null);
  const running = store.active && !store.allResolved;

  const handleRunNow = async () => {
    if (running) return;
    setError(null);
    try {
      await store.startAll();
    } catch {
      setError("Couldn't start the run — is the API reachable?");
    }
  };

  const lastRunAt = data ? (data.finished_at ?? data.started_at) : null;

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
      {data ? (
        <>
          <span>
            Last run: {formatTimestamp(lastRunAt!)} · {data.sources_count} sources
            {data.live ? " · live" : ""}
          </span>
          <span>Next run: {formatTimestamp(data.next_run_at)}</span>
        </>
      ) : null}
      {error ? (
        <span
          data-testid="run-error"
          role="alert"
          style={{ color: "var(--interrupt)" }}
        >
          {error}
        </span>
      ) : null}
      <button
        type="button"
        onClick={() => void handleRunNow()}
        disabled={running}
        aria-busy={running}
        style={{
          padding: "var(--sp-1) var(--sp-3)",
          fontSize: "var(--fs-meta)",
          fontWeight: 500,
          color: running ? "var(--ink-muted)" : "var(--accent)",
          background: running ? "var(--surface-sunk)" : "var(--accent-wash)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-sm)",
          cursor: running ? "not-allowed" : "pointer",
          opacity: running ? 0.7 : 1,
        }}
      >
        {running ? "Running…" : "Run now"}
      </button>
    </div>
  );
}

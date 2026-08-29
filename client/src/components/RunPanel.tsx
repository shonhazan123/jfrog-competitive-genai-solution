import { useState } from "react";
import type { RunStatus } from "../api/types";
import { useRunStore } from "../state/runStore";
import "./RunPanel.css";

interface RunPanelProps {
  data?: RunStatus;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RunPanel({ data }: RunPanelProps) {
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
    <section className="run-panel">
      <span className="run-panel__eyebrow">On-demand</span>
      <h2 className="run-panel__title">Run the investigation</h2>
      <p className="run-panel__lede">
        Kick off a fresh sweep across every source right now — competitors,
        signals and industry — instead of waiting for the next scheduled run.
      </p>
      <button
        type="button"
        className="run-panel__btn"
        onClick={() => void handleRunNow()}
        disabled={running}
        aria-busy={running}
      >
        {running ? "Running…" : "▶ Run now"}
      </button>
      {error ? (
        <span className="run-panel__error" data-testid="run-error" role="alert">
          {error}
        </span>
      ) : null}
      {data ? (
        <span className="run-panel__meta">
          {lastRunAt ? <>Last run {formatTimestamp(lastRunAt)} · </> : null}
          {data.sources_count} sources
          {data.live ? (
            <>
              {" "}
              · <span className="run-panel__live">live</span>
            </>
          ) : null}
          {"  ·  "}Next run {formatTimestamp(data.next_run_at)}
        </span>
      ) : null}
    </section>
  );
}

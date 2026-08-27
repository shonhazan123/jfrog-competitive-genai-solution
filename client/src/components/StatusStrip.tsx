import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { RunProgress as RunProgressData, RunStatus } from "../api/types";
import { RUN_POLL_INTERVAL_MS } from "../config/runPolling";
import { RunProgress } from "./RunProgress";

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

function invalidateDailyQueries(
  queryClient: ReturnType<typeof useQueryClient>,
): void {
  void queryClient.invalidateQueries({ queryKey: ["kits"] });
  void queryClient.invalidateQueries({ queryKey: ["signals"] });
  void queryClient.invalidateQueries({ queryKey: ["run-status"] });
  void queryClient.invalidateQueries({ queryKey: ["industry"] });
  void queryClient.invalidateQueries({ queryKey: ["comparison"] });
}

export function StatusStrip({ data }: StatusStripProps) {
  const queryClient = useQueryClient();
  const [activeRun, setActiveRun] = useState<RunProgressData | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeRunIdRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const pollRun = useCallback(
    async (runId: string) => {
      let progress: RunProgressData;
      try {
        progress = await api.getRun(runId);
      } catch {
        stopPolling();
        activeRunIdRef.current = null;
        setIsRunning(false);
        setActiveRun(null);
        setError("Lost contact with the server while the run was in progress.");
        return;
      }
      setActiveRun(progress);

      if (progress.status === "done") {
        stopPolling();
        activeRunIdRef.current = null;
        setIsRunning(false);
        invalidateDailyQueries(queryClient);
      } else if (progress.status === "failed") {
        stopPolling();
        activeRunIdRef.current = null;
        setIsRunning(false);
      }
    },
    [queryClient, stopPolling],
  );

  const handleRunNow = async () => {
    if (isRunning) {
      return;
    }
    stopPolling();
    setError(null);
    setActiveRun(null);
    setIsRunning(true);

    let run_id: string;
    try {
      ({ run_id } = await api.startRun());
    } catch {
      setIsRunning(false);
      setError("Couldn't start the run — is the API reachable?");
      return;
    }
    activeRunIdRef.current = run_id;

    const poll = () => {
      void pollRun(run_id);
    };

    poll();
    pollIntervalRef.current = setInterval(poll, RUN_POLL_INTERVAL_MS);
  };

  const lastRunAt = data
    ? (data.finished_at ?? data.started_at)
    : null;

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
            Last run: {formatTimestamp(lastRunAt!)} · {data.sources_count}{" "}
            sources
            {data.live ? " · live" : ""}
          </span>
          <span>Next run: {formatTimestamp(data.next_run_at)}</span>
        </>
      ) : null}
      {isRunning && !activeRun ? (
        <span data-testid="run-progress" role="status" aria-live="polite">
          Starting…
        </span>
      ) : null}
      {activeRun ? <RunProgress progress={activeRun} /> : null}
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
        disabled={isRunning}
        aria-busy={isRunning}
        style={{
          padding: "var(--sp-1) var(--sp-3)",
          fontSize: "var(--fs-meta)",
          fontWeight: 500,
          color: isRunning ? "var(--ink-muted)" : "var(--accent)",
          background: isRunning ? "var(--surface-sunk)" : "var(--accent-wash)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r-sm)",
          cursor: isRunning ? "not-allowed" : "pointer",
          opacity: isRunning ? 0.7 : 1,
        }}
      >
        {isRunning ? "Running…" : "Run now"}
      </button>
    </div>
  );
}

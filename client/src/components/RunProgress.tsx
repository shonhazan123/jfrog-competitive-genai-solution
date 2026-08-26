import type { RunProgress as RunProgressData } from "../api/types";

interface RunProgressProps {
  progress: RunProgressData;
}

export function RunProgress({ progress }: RunProgressProps) {
  if (progress.status === "failed") {
    return (
      <div
        data-testid="run-progress"
        role="status"
        style={{
          color: "var(--ink-secondary)",
          fontSize: "var(--fs-meta)",
        }}
      >
        {progress.message}
      </div>
    );
  }

  if (progress.status === "done") {
    return (
      <div
        data-testid="run-progress"
        role="status"
        style={{
          color: "var(--ink-secondary)",
          fontSize: "var(--fs-meta)",
          fontWeight: 500,
        }}
      >
        {progress.new_items} new items
      </div>
    );
  }

  return (
    <div
      data-testid="run-progress"
      role="status"
      aria-live="polite"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--sp-2)",
        color: "var(--ink-secondary)",
        fontSize: "var(--fs-meta)",
      }}
    >
      <span>{progress.stage_label}</span>
      <span aria-label="Stage progress">
        {progress.progress.current}/{progress.progress.total}
      </span>
    </div>
  );
}

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, isFixtureMode } from "../api/client";
import type { ComparisonMatrix } from "../api/types";
import { ComparisonGrid } from "../components/ComparisonGrid";
import { EmptyState } from "../components/EmptyState";
import { RunNowButton } from "../components/RunNowButton";
import comparisonMatrixFixture from "../fixtures/comparison_matrix.json";
import "./Comparison.css";

export function Comparison() {
  const queryClient = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const fixtureMode = isFixtureMode();
  const { data, isLoading } = useQuery({
    queryKey: ["comparison-matrix"],
    queryFn: () => api.getComparisonMatrix(),
    initialData: fixtureMode ? (comparisonMatrixFixture as ComparisonMatrix) : undefined,
  });
  // Competitors and dimensions come from config, so the matrix is scaffolded
  // (every cell stance "none", no evidence) even before any collection. Treat
  // "no cell has a real stance or any evidence" as the first-run empty state.
  const hasIntel =
    !!data &&
    data.dimensions.some((dimension) =>
      dimension.cells.some(
        (cell) => cell.stance !== "none" || cell.evidence.length > 0,
      ),
    );
  const isEmpty = !hasIntel;

  const handleRunThisPage = async () => {
    if (isRunning) return;
    setRunError(null);
    setIsRunning(true);
    try {
      const result = await api.runSurface("comparison");
      if (result.status === "done") {
        void queryClient.invalidateQueries({ queryKey: ["comparison-matrix"] });
        void queryClient.invalidateQueries({ queryKey: ["comparison"] });
      } else if (result.status === "failed") {
        setRunError(result.message || "The comparison run could not complete.");
      }
    } catch {
      setRunError("Couldn't start the run — is the API reachable?");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="comparison-page">
      <header>
        <span className="mono-label" style={{ marginBottom: "var(--sp-3)" }}>
          Positional Map
        </span>
        <h1 className="page-heading font-display">Competitor Landscape</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          Where each rival stands versus JFrog across capability dimensions. Click
          any row to view the full assessment.
        </p>
        <button
          type="button"
          data-testid="run-this-page"
          onClick={() => void handleRunThisPage()}
          disabled={isRunning}
          aria-busy={isRunning}
          style={{
            marginTop: "var(--sp-3)",
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
          {isRunning ? "Running…" : "Run this page"}
        </button>
        {runError ? (
          <p data-testid="run-error" role="alert" className="comparison-page__run-error">
            {runError}
          </p>
        ) : null}
      </header>

      {isEmpty ? (
        isLoading ? (
          <p className="mono-label" style={{ color: "var(--ink-muted)" }}>
            Loading…
          </p>
        ) : (
          <EmptyState
            eyebrow="First run"
            title="No competitor landscape yet"
            action={<RunNowButton />}
            testId="comparison-empty"
          >
            <p>
              This grid shows where each rival stands versus JFrog across the
              buyer-facing capability dimensions. No competitors have been
              assessed yet.
            </p>
            <p className="empty-state__note">
              Click <strong>Run now</strong> to build the matrix. This also fills
              the Today, Signals and Industry rooms.
            </p>
          </EmptyState>
        )
      ) : data ? (
        <ComparisonGrid matrix={data} />
      ) : null}
    </div>
  );
}

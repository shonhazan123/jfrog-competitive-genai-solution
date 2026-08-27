import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ComparisonMatrix } from "../api/types";
import { ComparisonGrid } from "../components/ComparisonGrid";
import comparisonMatrixFixture from "../fixtures/comparison_matrix.json";
import "./Comparison.css";

export function Comparison() {
  const queryClient = useQueryClient();
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["comparison-matrix"],
    queryFn: () => api.getComparisonMatrix(),
    initialData: comparisonMatrixFixture as ComparisonMatrix,
  });

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

      <ComparisonGrid matrix={data} />
    </div>
  );
}

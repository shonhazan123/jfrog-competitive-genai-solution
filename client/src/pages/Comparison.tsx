import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ComparisonMatrix } from "../api/types";
import { ComparisonGrid } from "../components/ComparisonGrid";
import comparisonMatrixFixture from "../fixtures/comparison_matrix.json";
import "./Comparison.css";

export function Comparison() {
  const { data } = useQuery({
    queryKey: ["comparison-matrix"],
    queryFn: () => api.getComparisonMatrix(),
    initialData: comparisonMatrixFixture as ComparisonMatrix,
  });

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
      </header>

      <ComparisonGrid matrix={data} />
    </div>
  );
}

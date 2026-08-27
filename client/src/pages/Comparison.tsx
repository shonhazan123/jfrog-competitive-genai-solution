import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ComparisonMatrix } from "../api/types";
import { ComparisonGrid } from "../components/ComparisonGrid";
import { Panel } from "../components/primitives/Panel";
import comparisonMatrixFixture from "../fixtures/comparison_matrix.json";

export function Comparison() {
  const { data } = useQuery({
    queryKey: ["comparison-matrix"],
    queryFn: () => api.getComparisonMatrix(),
    initialData: comparisonMatrixFixture as ComparisonMatrix,
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-5)",
        maxWidth: "var(--content-max)",
      }}
    >
      <header>
        <h1 className="page-heading">Competitors</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          JFrog product line mapped against rival public claims. Click a cell for
          sourced evidence.
        </p>
      </header>

      <Panel>
        <ComparisonGrid matrix={data} />
      </Panel>
    </div>
  );
}

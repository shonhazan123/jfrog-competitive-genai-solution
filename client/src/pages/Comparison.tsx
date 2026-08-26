import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { BattlecardRow, ListResponse } from "../api/types";
import { ComparisonTable } from "../components/ComparisonTable";
import { Panel } from "../components/primitives/Panel";
import comparisonFixture from "../fixtures/comparison_sonatype.json";

export function Comparison() {
  const { data } = useQuery({
    queryKey: ["comparison"],
    queryFn: () => api.getComparison(),
    initialData: comparisonFixture as ListResponse<BattlecardRow>,
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
        <h1 className="page-heading">Comparison — JFrog vs Sonatype</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          Derived from the claim ledger. ⚠ marks a dimension whose claim changed
          recently.
        </p>
      </header>

      <Panel>
        <ComparisonTable rows={data.items} />
      </Panel>
    </div>
  );
}

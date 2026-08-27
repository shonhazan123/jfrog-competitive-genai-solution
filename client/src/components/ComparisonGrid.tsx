import { useState } from "react";
import type {
  ComparisonMatrix,
  ComparisonMatrixCell,
  Evidence,
} from "../api/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function cellKey(componentKey: string, competitorSlug: string): string {
  return `${componentKey}:${competitorSlug}`;
}

interface ComparisonGridProps {
  matrix: ComparisonMatrix;
}

export function ComparisonGrid({ matrix }: ComparisonGridProps) {
  const [expandedComponent, setExpandedComponent] = useState<string | null>(
    null,
  );
  const [expandedCell, setExpandedCell] = useState<string | null>(null);

  const findCell = (
    componentKey: string,
    competitorSlug: string,
  ): ComparisonMatrixCell | undefined => {
    const component = matrix.components.find((row) => row.key === componentKey);
    return component?.cells.find((cell) => cell.competitor === competitorSlug);
  };

  const toggleComponent = (key: string) => {
    setExpandedComponent((current) => (current === key ? null : key));
  };

  const toggleCell = (key: string) => {
    setExpandedCell((current) => (current === key ? null : key));
  };

  return (
    <div data-testid="table-scroll" style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "var(--fs-body)",
          lineHeight: "var(--lh-body)",
        }}
      >
        <thead>
          <tr>
            <th
              style={{
                textAlign: "left",
                padding: "var(--sp-2) var(--sp-3)",
                borderBottom: "1px solid var(--border)",
                fontSize: "var(--fs-meta)",
                color: "var(--ink-muted)",
              }}
            >
              JFrog component
            </th>
            {matrix.competitors.map((competitor) => (
              <th
                key={competitor.slug}
                data-testid={`competitor-column-${competitor.slug}`}
                style={{
                  textAlign: "left",
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontSize: "var(--fs-meta)",
                  color: "var(--ink-muted)",
                }}
              >
                {competitor.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.components.map((component) => {
            const primaryCell = component.cells[0];
            const jfrogPosition =
              primaryCell?.jfrog_position ?? "";

            return (
              <tr key={component.key} data-testid={`component-row-${component.key}`}>
                <td
                  style={{
                    padding: "var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    verticalAlign: "top",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => toggleComponent(component.key)}
                    data-testid={`component-name-${component.key}`}
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      font: "inherit",
                      color: "inherit",
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    {component.name}
                  </button>
                  {expandedComponent === component.key && jfrogPosition ? (
                    <div
                      data-testid={`jfrog-position-${component.key}`}
                      style={{
                        marginTop: "var(--sp-2)",
                        fontSize: "var(--fs-meta)",
                        color: "var(--ink-secondary)",
                      }}
                    >
                      {jfrogPosition}
                    </div>
                  ) : null}
                </td>
                {matrix.competitors.map((competitor) => {
                  const cell = findCell(component.key, competitor.slug);
                  if (!cell) {
                    return (
                      <td
                        key={competitor.slug}
                        style={{
                          padding: "var(--sp-3)",
                          borderBottom: "1px solid var(--border)",
                          verticalAlign: "top",
                        }}
                      />
                    );
                  }

                  const key = cellKey(component.key, competitor.slug);
                  const isExpanded = expandedCell === key;
                  const primaryEvidence =
                    cell.evidence.find((item) => item.is_primary) ??
                    cell.evidence[0];

                  return (
                    <td
                      key={competitor.slug}
                      style={{
                        padding: "var(--sp-3)",
                        borderBottom: "1px solid var(--border)",
                        verticalAlign: "top",
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => toggleCell(key)}
                        data-testid={`matrix-cell-${component.key}-${competitor.slug}`}
                        style={{
                          background: "none",
                          border: "none",
                          padding: 0,
                          font: "inherit",
                          color: "inherit",
                          cursor: "pointer",
                          textAlign: "left",
                          width: "100%",
                        }}
                      >
                        <span data-testid="cell-stance">{cell.stance}</span>
                        <div
                          style={{
                            marginTop: "var(--sp-1)",
                            color: "var(--ink-secondary)",
                          }}
                        >
                          {cell.summary}
                        </div>
                      </button>
                      {isExpanded && primaryEvidence ? (
                        <div
                          data-testid={`cell-evidence-${component.key}-${competitor.slug}`}
                          style={{ marginTop: "var(--sp-2)" }}
                        >
                          <p style={{ margin: "0 0 var(--sp-1)" }}>
                            {primaryEvidence.quote}
                          </p>
                          <EvidenceLink evidence={primaryEvidence} />
                        </div>
                      ) : null}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EvidenceLink({ evidence }: { evidence: Evidence }) {
  return (
    <span style={{ fontSize: "var(--fs-meta)", color: "var(--ink-muted)" }}>
      <a href={evidence.source_url} target="_blank" rel="noreferrer">
        {evidence.source_name}
      </a>
      {" · "}
      <span>{formatDate(evidence.captured_at)}</span>
    </span>
  );
}

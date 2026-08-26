import type { BattlecardRow } from "../api/types";
import { GradeChip } from "./primitives/GradeChip";

function toDimKey(dimension: string): string {
  return dimension.toLowerCase().replace(/ /g, "_");
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

interface ComparisonTableProps {
  rows: BattlecardRow[];
}

export function ComparisonTable({ rows }: ComparisonTableProps) {
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
              Dimension
            </th>
            <th
              style={{
                textAlign: "left",
                padding: "var(--sp-2) var(--sp-3)",
                borderBottom: "1px solid var(--border)",
                fontSize: "var(--fs-meta)",
                color: "var(--ink-muted)",
              }}
            >
              JFrog position
            </th>
            <th
              style={{
                textAlign: "left",
                padding: "var(--sp-2) var(--sp-3)",
                borderBottom: "1px solid var(--border)",
                fontSize: "var(--fs-meta)",
                color: "var(--ink-muted)",
              }}
            >
              Competitor position
            </th>
            <th
              style={{
                textAlign: "left",
                padding: "var(--sp-2) var(--sp-3)",
                borderBottom: "1px solid var(--border)",
                fontSize: "var(--fs-meta)",
                color: "var(--ink-muted)",
              }}
            >
              Last changed
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const dimKey = toDimKey(row.dimension);
            const primaryEvidence = row.evidence.find((e) => e.is_primary) ?? row.evidence[0];

            return (
              <tr key={row.id}>
                <td
                  style={{
                    padding: "var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    verticalAlign: "top",
                  }}
                >
                  {row.dimension}
                  {row.changed_recently ? (
                    <span
                      data-testid="changed-flag"
                      title="Supporting claim changed recently"
                      style={{ marginLeft: "var(--sp-1)" }}
                    >
                      ⚠
                    </span>
                  ) : null}
                </td>
                <td
                  style={{
                    padding: "var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    verticalAlign: "top",
                  }}
                >
                  <div data-testid="jfrog-cell" data-origin="authored">
                    {row.jfrog_position}
                  </div>
                </td>
                <td
                  style={{
                    padding: "var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    verticalAlign: "top",
                  }}
                >
                  <div data-testid="competitor-cell">
                    <div data-testid={`competitor-cell-${dimKey}`}>
                      {row.no_claim_on_record ? (
                        <span>No public claim</span>
                      ) : (
                        <>
                          <span>{row.competitor_position}</span>
                          {row.reliability_grade ? (
                            <span
                              data-testid="grade-chip"
                              style={{ marginLeft: "var(--sp-2)" }}
                            >
                              <GradeChip grade={row.reliability_grade} />
                            </span>
                          ) : null}
                          {primaryEvidence ? (
                            <div style={{ marginTop: "var(--sp-1)" }}>
                              <a
                                href={primaryEvidence.source_url}
                                style={{
                                  fontSize: "var(--fs-meta)",
                                  color: "var(--accent)",
                                  textDecoration: "underline",
                                }}
                              >
                                {primaryEvidence.source_name}
                              </a>
                            </div>
                          ) : null}
                        </>
                      )}
                    </div>
                  </div>
                </td>
                <td
                  style={{
                    padding: "var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    verticalAlign: "top",
                    fontSize: "var(--fs-meta)",
                    color: "var(--ink-secondary)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {formatDate(row.last_changed_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

import type { Source } from "../api/types";
import { GradeChip } from "./primitives/GradeChip";

interface SourceTableProps {
  sources: Source[];
}

export function SourceTable({ sources }: SourceTableProps) {
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
            {["Source", "Entity", "Mode", "Grade", "Cadence", "Robots", "Last checked", "Status"].map(
              (heading) => (
                <th
                  key={heading}
                  style={{
                    textAlign: "left",
                    padding: "var(--sp-2) var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    fontSize: "var(--fs-meta)",
                    color: "var(--ink-muted)",
                  }}
                >
                  {heading}
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {sources.map((source) => (
            <tr
              key={source.id}
              style={{
                opacity: source.excluded ? 0.75 : 1,
                backgroundColor: source.excluded
                  ? "var(--surface-sunk)"
                  : undefined,
              }}
            >
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                }}
              >
                {source.name}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                }}
              >
                {source.entity}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--fs-mono)",
                }}
              >
                {source.mode}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                }}
              >
                {source.reliability_grade ? (
                  <span data-testid="grade-chip">
                    <GradeChip grade={source.reliability_grade} />
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--fs-mono)",
                }}
              >
                {source.check_frequency ?? "—"}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--fs-mono)",
                  color: source.robots_allowed ? "var(--ink)" : "var(--interrupt)",
                }}
              >
                {source.robots_allowed ? "✓" : "✗"}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontSize: "var(--fs-meta)",
                  color: "var(--ink-muted)",
                }}
              >
                {source.last_checked
                  ? new Date(source.last_checked).toLocaleString("en-GB", {
                      hour: "2-digit",
                      minute: "2-digit",
                      day: "numeric",
                      month: "short",
                    })
                  : "—"}
              </td>
              <td
                style={{
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontSize: "var(--fs-meta)",
                  color: source.excluded ? "var(--interrupt)" : "var(--ink-secondary)",
                }}
              >
                {source.excluded && source.exclusion_reason
                  ? source.exclusion_reason
                  : source.enabled
                    ? "active"
                    : "disabled"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

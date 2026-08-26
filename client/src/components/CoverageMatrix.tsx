import type { CoverageMatrix as CoverageMatrixData } from "../api/types";

const STATUS_SYMBOL: Record<string, string> = {
  multiple: "✓✓",
  one: "✓",
  gap: "✗",
  not_applicable: "—",
};

interface CoverageMatrixProps {
  data: CoverageMatrixData;
}

export function CoverageMatrix({ data }: CoverageMatrixProps) {
  return (
    <div>
      <p
        style={{
          marginBottom: "var(--sp-4)",
          fontSize: "var(--fs-body)",
          lineHeight: "var(--lh-body)",
          color: "var(--ink-secondary)",
        }}
      >
        {data.caption}
      </p>

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
                data-testid="coverage-col"
                style={{
                  textAlign: "left",
                  padding: "var(--sp-2) var(--sp-3)",
                  borderBottom: "1px solid var(--border)",
                  fontSize: "var(--fs-meta)",
                  color: "var(--ink-muted)",
                }}
              >
                Entity
              </th>
              {data.columns.map((col) => (
                <th
                  key={col}
                  data-testid="coverage-col"
                  style={{
                    textAlign: "center",
                    padding: "var(--sp-2) var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    fontSize: "var(--fs-meta)",
                    color: "var(--ink-muted)",
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.entity}>
                <td
                  style={{
                    padding: "var(--sp-2) var(--sp-3)",
                    borderBottom: "1px solid var(--border)",
                    fontWeight: 500,
                  }}
                >
                  {row.entity}
                  {row.tier != null ? (
                    <span
                      style={{
                        marginLeft: "var(--sp-2)",
                        fontSize: "var(--fs-meta)",
                        color: "var(--ink-muted)",
                      }}
                    >
                      tier {row.tier}
                    </span>
                  ) : null}
                </td>
                {row.cells.map((cell) => (
                  <td
                    key={cell.signal_type}
                    data-testid={cell.status === "gap" ? "coverage-gap" : undefined}
                    style={{
                      textAlign: "center",
                      padding: "var(--sp-2) var(--sp-3)",
                      borderBottom: "1px solid var(--border)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--fs-mono)",
                      color:
                        cell.status === "gap"
                          ? "var(--interrupt)"
                          : "var(--ink-secondary)",
                      backgroundColor:
                        cell.status === "gap"
                          ? "var(--interrupt-wash)"
                          : undefined,
                    }}
                    title={
                      cell.status === "gap"
                        ? "configured gap — no source yet"
                        : undefined
                    }
                  >
                    {STATUS_SYMBOL[cell.status]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--sp-3)",
          marginTop: "var(--sp-4)",
          padding: 0,
          listStyle: "none",
          fontSize: "var(--fs-meta)",
          lineHeight: "var(--lh-meta)",
          color: "var(--ink-muted)",
        }}
      >
        {data.legend.map(([symbol, label]) => (
          <li key={symbol}>
            <span style={{ fontFamily: "var(--font-mono)" }}>{symbol}</span>{" "}
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}

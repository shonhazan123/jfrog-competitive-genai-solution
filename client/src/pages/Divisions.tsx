import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ExecWeekly, ListResponse, Persona, Signal } from "../api/types";
import { SignalCard } from "../components/SignalCard";
import { TrendCard } from "../components/TrendCard";
import digestExecWeeklyFixture from "../fixtures/digest_exec_weekly.json";
import signalsProductFixture from "../fixtures/signals_product.json";
import signalsSalesFixture from "../fixtures/signals_sales.json";

type DivisionTab = "sales" | "product" | "executive";

const TAB_PERSONA: Record<"sales" | "product", Persona> = {
  sales: "sales",
  product: "product",
};

const GRID_BREAKPOINT = 1000;

function useGridColumns(): string {
  const [columns, setColumns] = useState(() =>
    typeof window !== "undefined" && window.innerWidth < GRID_BREAKPOINT
      ? "1"
      : "auto",
  );

  useEffect(() => {
    const handleResize = () => {
      setColumns(window.innerWidth < GRID_BREAKPOINT ? "1" : "auto");
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return columns;
}

export function Divisions() {
  const [tab, setTab] = useState<DivisionTab>("sales");
  const gridColumns = useGridColumns();

  const { data: salesSignals } = useQuery({
    queryKey: ["signals", "sales"],
    queryFn: () => api.getSignals({ persona: "sales" }),
    initialData: signalsSalesFixture as ListResponse<Signal>,
  });

  const { data: productSignals } = useQuery({
    queryKey: ["signals", "product"],
    queryFn: () => api.getSignals({ persona: "product" }),
    initialData: signalsProductFixture as ListResponse<Signal>,
  });

  const { data: execWeekly } = useQuery({
    queryKey: ["exec-weekly"],
    queryFn: () => api.getExecWeekly(),
    initialData: digestExecWeeklyFixture as ExecWeekly,
  });

  const activeSignals =
    tab === "product" ? productSignals.items : salesSignals.items;
  const activePersona: Persona = tab === "product" ? "product" : "sales";

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
        <h1 className="page-heading">Divisions</h1>
      </header>

      <div role="tablist" aria-label="Persona views" style={{ display: "flex", gap: "var(--sp-2)" }}>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "sales"}
          onClick={() => setTab("sales")}
          style={{
            padding: "var(--sp-2) var(--sp-4)",
            fontSize: "var(--fs-meta)",
            fontWeight: tab === "sales" ? 600 : 400,
            color: tab === "sales" ? "var(--accent)" : "var(--ink-secondary)",
            background: tab === "sales" ? "var(--accent-wash)" : "transparent",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            cursor: "pointer",
          }}
        >
          Sales
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "product"}
          onClick={() => setTab("product")}
          style={{
            padding: "var(--sp-2) var(--sp-4)",
            fontSize: "var(--fs-meta)",
            fontWeight: tab === "product" ? 600 : 400,
            color: tab === "product" ? "var(--accent)" : "var(--ink-secondary)",
            background: tab === "product" ? "var(--accent-wash)" : "transparent",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            cursor: "pointer",
          }}
        >
          Product
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "executive"}
          onClick={() => setTab("executive")}
          style={{
            padding: "var(--sp-2) var(--sp-4)",
            fontSize: "var(--fs-meta)",
            fontWeight: tab === "executive" ? 600 : 400,
            color: tab === "executive" ? "var(--accent)" : "var(--ink-secondary)",
            background: tab === "executive" ? "var(--accent-wash)" : "transparent",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            cursor: "pointer",
          }}
        >
          Executive
        </button>
      </div>

      {tab === "executive" ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--sp-4)",
          }}
        >
          <p
            style={{
              fontSize: "var(--fs-body)",
              lineHeight: "var(--lh-body)",
              color: "var(--ink-secondary)",
            }}
          >
            {execWeekly.lead}
          </p>
          {execWeekly.trends.map((trend) => (
            <TrendCard key={trend.id} trend={trend} />
          ))}
          {execWeekly.stability.map((statement) => (
            <div
              key={statement.title}
              style={{
                padding: "var(--sp-4)",
                background: "var(--surface-sunk)",
                border: "1px solid var(--border)",
                borderRadius: "var(--r-lg)",
                fontSize: "var(--fs-body)",
                lineHeight: "var(--lh-body)",
                color: "var(--ink-secondary)",
              }}
            >
              <p style={{ fontWeight: 600, color: "var(--ink)", marginBottom: "var(--sp-2)" }}>
                {statement.title}
              </p>
              <p>{statement.detail}</p>
            </div>
          ))}
        </div>
      ) : (
        <div
          data-testid="card-grid"
          data-columns={gridColumns}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))",
            gap: "var(--sp-4)",
          }}
        >
          {activeSignals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              persona={TAB_PERSONA[tab as "sales" | "product"] ?? activePersona}
            />
          ))}
        </div>
      )}
    </div>
  );
}

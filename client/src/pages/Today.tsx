import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Persona, TodayBrief } from "../api/types";
import { SignalCard } from "../components/SignalCard";
import todayFixture from "../fixtures/today.json";

export function Today() {
  const { data } = useQuery({
    queryKey: ["today"],
    queryFn: () => api.getToday(),
    initialData: todayFixture as TodayBrief,
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
        <h1 className="page-heading">Today</h1>
      </header>

      <p
        data-testid="today-headline"
        style={{
          margin: 0,
          padding: "var(--sp-4)",
          fontSize: "var(--fs-lead)",
          lineHeight: "var(--lh-lead)",
          fontWeight: 500,
          color: "var(--ink-primary)",
          background: "var(--surface-raised)",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {data.headline}
      </p>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-4)",
        }}
      >
        {data.cards.map((signal) => (
          <SignalCard
            key={signal.id}
            signal={signal}
            persona={(signal.primary_stakeholder ?? "sales") as Persona}
          />
        ))}
      </div>
    </div>
  );
}

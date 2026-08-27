import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ListResponse, Persona, Signal } from "../api/types";
import { SignalCard } from "../components/SignalCard";
import { SectionLabel } from "../components/primitives/SectionLabel";
import signalsTodayFixture from "../fixtures/signals_today.json";

type LabeledSignal = Signal & { signal_type_label: string };

interface SignalGroup {
  signalType: Signal["signal_type"];
  label: string;
  items: LabeledSignal[];
}

function groupSignalsByType(items: LabeledSignal[]): SignalGroup[] {
  const groups = new Map<Signal["signal_type"], SignalGroup>();

  for (const signal of items) {
    const existing = groups.get(signal.signal_type);
    if (existing) {
      existing.items.push(signal);
    } else {
      groups.set(signal.signal_type, {
        signalType: signal.signal_type,
        label: signal.signal_type_label,
        items: [signal],
      });
    }
  }

  return [...groups.values()];
}

export function Signals() {
  const { data } = useQuery({
    queryKey: ["signals", "all"],
    queryFn: () => api.getSignals({}),
    initialData: signalsTodayFixture as ListResponse<LabeledSignal>,
  });

  const groups = groupSignalsByType(data.items);

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
        <h1 className="page-heading">Signals</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          Public moves read as intent — a job posting, a pricing page, or a
          changelog points to where a competitor is investing. This room is for
          digging in on that direction, not for tracking what changed since your
          last visit.
        </p>
      </header>

      {groups.map((group) => (
        <section
          key={group.signalType}
          data-testid={`signal-group-${group.signalType}`}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--sp-4)",
          }}
        >
          <SectionLabel>{group.label}</SectionLabel>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))",
              gap: "var(--sp-4)",
            }}
          >
            {group.items.map((signal) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                persona={(signal.persona ?? "sales") as Persona}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

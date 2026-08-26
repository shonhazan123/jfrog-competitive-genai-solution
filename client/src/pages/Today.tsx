import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ListResponse, RunStatus, SignalDetail, SinceLastVisit } from "../api/types";
import { InterruptCard } from "../components/InterruptCard";
import { SinceLastVisit as SinceLastVisitBanner } from "../components/SinceLastVisit";
import { SignalCard } from "../components/SignalCard";
import { StatusStrip } from "../components/StatusStrip";
import runStatusFixture from "../fixtures/run_status.json";
import signalTraceFixture from "../fixtures/signal_trace.json";
import signalsTodayFixture from "../fixtures/signals_today.json";
import sinceLastVisitFixture from "../fixtures/since_last_visit.json";

export function Today() {
  const { data: runStatus } = useQuery({
    queryKey: ["run-status"],
    queryFn: () => api.getRunStatus(),
    initialData: runStatusFixture as RunStatus,
  });

  const { data: sinceLastVisit } = useQuery({
    queryKey: ["since-last-visit"],
    queryFn: () => api.getSinceLastVisit(),
    initialData: sinceLastVisitFixture as SinceLastVisit,
  });

  const { data: signals } = useQuery({
    queryKey: ["signals", "today"],
    queryFn: () => api.getSignals({ view: "today" }),
    initialData: signalsTodayFixture as ListResponse<import("../api/types").Signal>,
  });

  const interrupt =
    signals.items.find((s) => s.interrupt_tier === "critical") ??
    signals.items.find((s) => s.interrupt_tier);

  const { data: interruptDetail } = useQuery({
    queryKey: ["signal", interrupt?.id],
    queryFn: () => api.getSignal(interrupt!.id),
    initialData: signalTraceFixture as SignalDetail,
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

      <StatusStrip data={runStatus} />
      <SinceLastVisitBanner data={sinceLastVisit} />

      {interruptDetail ? <InterruptCard signal={interruptDetail} /> : null}

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-4)",
        }}
      >
        {signals.items.map((signal) => (
          <SignalCard
            key={signal.id}
            signal={signal}
            persona={signal.persona ?? "sales"}
          />
        ))}
      </div>
    </div>
  );
}

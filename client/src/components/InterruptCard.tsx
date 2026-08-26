import type { SignalDetail } from "../api/types";
import { Chip } from "./primitives/Chip";
import { Disclosure } from "./primitives/Disclosure";
import { Quote } from "./primitives/Quote";
import { ScoreBadge } from "./primitives/ScoreBadge";
import { SectionLabel } from "./primitives/SectionLabel";
import { WasNow } from "./primitives/WasNow";

interface InterruptCardProps {
  signal: SignalDetail;
}

export function InterruptCard({ signal }: InterruptCardProps) {
  const evidence = signal.evidence[0];

  return (
    <article
      data-testid="interrupt-card"
      style={{
        padding: "var(--sp-4)",
        background: "var(--interrupt-wash)",
        border: "2px solid var(--interrupt)",
        borderRadius: "var(--r-lg)",
        boxShadow: "var(--shadow-2)",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "var(--sp-3)",
          marginBottom: "var(--sp-3)",
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "var(--sp-2)",
          }}
        >
          <span
            style={{
              fontSize: "var(--fs-meta)",
              fontWeight: 600,
              color: "var(--interrupt)",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Interrupt
          </span>
          <span style={{ fontWeight: 600, color: "var(--ink)" }}>
            {signal.entity.name}
          </span>
          <Chip signalType={signal.signal_type} />
        </div>
        <ScoreBadge value={signal.score} />
      </header>

      <h2
        style={{
          fontSize: "var(--fs-headline)",
          lineHeight: "var(--lh-headline)",
          fontWeight: 600,
          color: "var(--ink)",
          marginBottom: "var(--sp-3)",
        }}
      >
        {signal.headline}
      </h2>

      <section style={{ marginBottom: "var(--sp-3)" }}>
        <SectionLabel>SO WHAT</SectionLabel>
        <p
          style={{
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
            marginTop: "var(--sp-1)",
          }}
        >
          {signal.so_what}
        </p>
      </section>

      {evidence ? (
        <section style={{ marginBottom: "var(--sp-3)" }}>
          <SectionLabel>EVIDENCE</SectionLabel>
          <Quote>{evidence.quote}</Quote>
          {signal.change ? (
            <WasNow was={signal.change.was} now={signal.change.now} />
          ) : null}
        </section>
      ) : null}

      <Disclosure label="Why this score">
        {signal.score_breakdown?.parts.map(([label, value]) => (
          <div
            key={label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "var(--fs-mono)",
              padding: "var(--sp-1) 0",
            }}
          >
            <span>{label}</span>
            <span>{value >= 0 ? `+${value}` : value}</span>
          </div>
        ))}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontWeight: 600,
            fontSize: "var(--fs-mono)",
            marginTop: "var(--sp-2)",
          }}
        >
          <span>=</span>
          <span>{Math.round(signal.score)}</span>
        </div>
      </Disclosure>

      <Disclosure label="How this was produced">
        <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {signal.trace?.map((step) => (
            <li
              key={step.n}
              style={{
                fontSize: "var(--fs-meta)",
                lineHeight: "var(--lh-meta)",
                padding: "var(--sp-1) 0",
                color: "var(--ink-secondary)",
              }}
            >
              <span style={{ fontWeight: 600 }}>{step.node}</span>
              <span aria-hidden="true"> · </span>
              <span>{step.detail}</span>
            </li>
          ))}
        </ol>
      </Disclosure>
    </article>
  );
}

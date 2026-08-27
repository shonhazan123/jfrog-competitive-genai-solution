import type { SignalDetail } from "../api/types";
import { TierBadge } from "./TierBadge";
import { Chip } from "./primitives/Chip";
import { Disclosure } from "./primitives/Disclosure";
import { Quote } from "./primitives/Quote";
import { SectionLabel } from "./primitives/SectionLabel";

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
        <TierBadge tier={signal.tier} label={signal.tier_label} />
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

      {signal.why_it_matters ? (
        <p
          style={{
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
            marginBottom: "var(--sp-3)",
          }}
        >
          {signal.why_it_matters}
        </p>
      ) : null}

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
        </section>
      ) : null}

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

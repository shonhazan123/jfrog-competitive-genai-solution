import type { CSSProperties } from "react";
import type { Persona, Signal, TraceStep } from "../api/types";
import { Chip } from "./primitives/Chip";
import { Disclosure } from "./primitives/Disclosure";
import { Quote } from "./primitives/Quote";
import { SectionLabel } from "./primitives/SectionLabel";
import { TierBadge } from "./TierBadge";
import "./SignalCard.css";

const HUE_TOKENS: Record<string, string> = {
  product_capability: "var(--sig-product)",
  positioning_messaging: "var(--sig-positioning)",
  pricing_packaging: "var(--sig-pricing)",
  security_trust: "var(--sig-security)",
  corporate_financial: "var(--sig-corporate)",
  partnership_ecosystem: "var(--sig-partnership)",
  customer_evidence: "var(--sig-customer)",
  market_regulatory: "var(--sig-regulatory)",
  talent_org: "var(--sig-talent)",
};

export type SignalAction = "confirm" | "reject" | "edit" | "mute";

export interface SignalCardSignal extends Signal {
  trace?: TraceStep[];
  so_what_exec?: string;
}

interface SignalCardProps {
  signal: SignalCardSignal;
  persona: Persona;
  onAction?: (action: SignalAction) => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function TraceContent({ trace }: { trace?: TraceStep[] }) {
  if (!trace || trace.length === 0) {
    return <p>Production trace not available for this signal.</p>;
  }

  return (
    <ol className="signal-card__trace">
      {trace.map((step) => (
        <li key={step.n} className="signal-card__trace-step">
          <span className="signal-card__trace-node">{step.node}</span>
          <span className="signal-card__trace-status" data-status={step.status}>
            {step.status}
          </span>
          <span className="signal-card__trace-detail">{step.detail}</span>
        </li>
      ))}
    </ol>
  );
}

export function SignalCard({ signal, persona, onAction }: SignalCardProps) {
  const evidence = signal.evidence[0];
  const hue = HUE_TOKENS[signal.signal_type] ?? "var(--sig-product)";
  const cardStyle = { "--signal-hue": hue } as CSSProperties;

  return (
    <article
      className="signal-card"
      style={cardStyle}
      data-testid="signal-card"
      data-entity={signal.entity?.slug}
    >
      <header className="signal-card__header">
        <div className="signal-card__header-left">
          <span className="signal-card__entity">{signal.entity.name}</span>
          <span data-testid="signal-type">
            <Chip signalType={signal.signal_type} />
          </span>
        </div>
        <div className="signal-card__header-right">
          <TierBadge tier={signal.tier} label={signal.tier_label} />
          <span className="signal-card__persona">{persona.toUpperCase()}</span>
        </div>
      </header>

      <h3 className="signal-card__headline">{signal.headline}</h3>

      {signal.why_it_matters ? (
        <p className="signal-card__why-it-matters">{signal.why_it_matters}</p>
      ) : null}

      {signal.handling === "caution" ? (
        <p className="signal-card__handling" role="note">
          Caution — lead on posture, not on their specific CVE.
        </p>
      ) : null}

      <section className="signal-card__section">
        <SectionLabel>SO WHAT</SectionLabel>
        <p className="signal-card__so-what" data-testid="so-what">
          {signal.so_what}
        </p>
      </section>

      {evidence ? (
        <section className="signal-card__section">
          <SectionLabel>EVIDENCE</SectionLabel>
          <Quote>{evidence.quote}</Quote>
          <p className="signal-card__source-line">
            <a href={evidence.source_url} target="_blank" rel="noreferrer">
              {evidence.source_name}
            </a>
            <span aria-hidden="true"> · </span>
            <span>{formatDate(evidence.captured_at)}</span>
          </p>
        </section>
      ) : null}

      <Disclosure label="How this was produced">
        <TraceContent trace={signal.trace} />
      </Disclosure>

      <div className="signal-card__actions">
        <button
          type="button"
          className="signal-card__action"
          onClick={() => onAction?.("confirm")}
        >
          Confirm
        </button>
        <button
          type="button"
          className="signal-card__action"
          onClick={() => onAction?.("reject")}
        >
          Reject
        </button>
        <button
          type="button"
          className="signal-card__action"
          onClick={() => onAction?.("edit")}
        >
          Edit
        </button>
        <button
          type="button"
          className="signal-card__action"
          onClick={() => onAction?.("mute")}
        >
          Mute source
        </button>
      </div>
    </article>
  );
}

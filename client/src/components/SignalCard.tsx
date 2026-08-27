import type { CSSProperties } from "react";
import type { Persona, ScoreBreakdown, Signal, TraceStep } from "../api/types";
import { Chip } from "./primitives/Chip";
import { Disclosure } from "./primitives/Disclosure";
import { Quote } from "./primitives/Quote";
import { ScoreBadge } from "./primitives/ScoreBadge";
import { SectionLabel } from "./primitives/SectionLabel";
import { WasNow } from "./primitives/WasNow";
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

type NormalizedBreakdown = {
  total?: number;
  parts: [string, number][];
};

function normalizeBreakdown(
  breakdown: ScoreBreakdown | [string, number][] | null | undefined,
): NormalizedBreakdown | null {
  if (!breakdown) return null;
  if (Array.isArray(breakdown)) {
    return { parts: breakdown };
  }
  if ("parts" in breakdown && Array.isArray(breakdown.parts)) {
    return { total: breakdown.total, parts: breakdown.parts };
  }
  return null;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatScoreValue(label: string, value: number): string {
  if (label.toLowerCase().includes("jfrog") && value > 1 && value <= 3) {
    return `×${value}`;
  }
  if (value >= 0) return `+${value}`;
  return String(value);
}

function ScoreBreakdownContent({
  breakdown,
  score,
}: {
  breakdown: Signal["score_breakdown"];
  score: number;
}) {
  const normalized = normalizeBreakdown(breakdown);

  if (!normalized || normalized.parts.length === 0) {
    return <p>Score breakdown not available for this signal.</p>;
  }

  const displayTotal = normalized.total ?? score;

  return (
    <div className="signal-card__score-breakdown">
      {normalized.parts.map(([label, value]) => (
        <div key={label} className="signal-card__score-part">
          <span>{label}</span>
          <span className="signal-card__score-value">
            {formatScoreValue(label, value)}
          </span>
        </div>
      ))}
      <div className="signal-card__score-total">
        <span>=</span>
        <span>{Math.round(displayTotal)}</span>
      </div>
    </div>
  );
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
          <ScoreBadge value={signal.score} />
          <span className="signal-card__persona">{persona.toUpperCase()}</span>
        </div>
      </header>

      <h3 className="signal-card__headline">{signal.headline}</h3>

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
          {signal.change ? (
            <WasNow was={signal.change.was} now={signal.change.now} />
          ) : null}
        </section>
      ) : null}

      <Disclosure label="Why this score">
        <ScoreBreakdownContent
          breakdown={signal.score_breakdown}
          score={signal.score}
        />
      </Disclosure>

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

import type { CSSProperties } from "react";
import type { Signal } from "../api/types";
import { personaLabel, signalHue, TIER_HUE } from "../config/labels";
import { Quote } from "./primitives/Quote";
import "./SignalAccordionRow.css";

interface SignalAccordionRowProps {
  signal: Signal;
  expanded: boolean;
  onToggle: () => void;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function SignalAccordionRow({
  signal,
  expanded,
  onToggle,
}: SignalAccordionRowProps) {
  const evidence = signal.evidence[0];
  const rowStyle = {
    "--tier-hue": TIER_HUE[signal.tier],
    "--signal-hue": signalHue(signal.signal_type),
  } as CSSProperties;

  return (
    <article
      className={`signal-accordion-row${expanded ? " signal-accordion-row--expanded" : ""}`}
      style={rowStyle}
      data-testid="signal-accordion-row"
      data-signal-id={signal.id}
      data-entity={signal.entity?.slug}
    >
      <button
        type="button"
        className="signal-accordion-row__trigger"
        aria-expanded={expanded}
        onClick={onToggle}
        data-testid={`signal-row-trigger-${signal.id}`}
      >
        <div className="signal-accordion-row__trigger-main">
          <div className="signal-accordion-row__meta">
            <span className="signal-accordion-row__entity mono-label">
              {signal.entity.name}
            </span>
            <span
              className="signal-accordion-row__tier-dot"
              aria-hidden="true"
            />
            <span className="signal-accordion-row__tier-label mono-label">
              {signal.tier_label}
            </span>
          </div>
          <h3 className="signal-accordion-row__headline">{signal.headline}</h3>
        </div>
        <span
          className="signal-accordion-row__chevron"
          aria-hidden="true"
        />
      </button>

      {expanded ? (
        <div
          className="signal-accordion-row__body"
          data-testid={`signal-row-body-${signal.id}`}
        >
          <span className="mono-label signal-accordion-row__intent-label">
            Intent read
          </span>

          {signal.so_what ? (
            <p className="signal-accordion-row__intent-text" data-testid="so-what">
              {signal.so_what}
            </p>
          ) : null}

          {signal.why_it_matters ? (
            <p className="signal-accordion-row__tier-reason mono-label">
              ↳ {signal.why_it_matters}
            </p>
          ) : null}

          {signal.handling === "caution" ? (
            <p className="signal-accordion-row__handling" role="note">
              Caution — lead on posture, not on their specific CVE.
            </p>
          ) : null}

          <div className="signal-accordion-row__footer">
            <div className="signal-accordion-row__tags">
              {signal.primary_stakeholder ? (
                <span className="signal-accordion-row__tag signal-accordion-row__tag--audience mono-label">
                  {personaLabel(signal.primary_stakeholder)}
                </span>
              ) : null}
            </div>

            {evidence ? (
              <div className="signal-accordion-row__evidence">
                <Quote>{evidence.quote}</Quote>
                <p className="signal-accordion-row__source-line mono-label">
                  <a
                    href={evidence.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {evidence.source_name}
                  </a>
                  <span aria-hidden="true"> · </span>
                  <span>{formatDate(evidence.captured_at)}</span>
                </p>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </article>
  );
}

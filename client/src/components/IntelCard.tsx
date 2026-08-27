import type { CSSProperties } from "react";
import type { Signal } from "../api/types";
import { personaLabel, TIER_HUE } from "../config/labels";
import "./IntelCard.css";

export type IntelCardSignal = Signal & {
  jfrog_areas?: string[];
};

export interface IntelCardProps {
  signal: IntelCardSignal;
  rank: number;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function IntelCard({ signal, rank }: IntelCardProps) {
  const evidence = signal.evidence[0];
  const tierHue = TIER_HUE[signal.tier];
  const areas = signal.jfrog_areas ?? [];
  const cardStyle = { "--intel-tier-hue": tierHue } as CSSProperties;

  return (
    <article
      className="intel-card"
      style={cardStyle}
      data-testid="signal-card"
      data-tier={signal.tier}
      data-entity={signal.entity?.slug}
    >
      <div className="intel-card__top">
        <div className="intel-card__rank-row">
          <span className="intel-card__rank mono-label">#{rank}</span>
          <div className="intel-card__tier">
            <span className="intel-card__tier-dot" aria-hidden="true" />
            <span className="intel-card__tier-label mono-label">
              {signal.tier_label}
            </span>
          </div>
        </div>
        {evidence ? (
          <time className="mono-label" dateTime={evidence.captured_at}>
            {formatDate(evidence.captured_at)}
          </time>
        ) : null}
      </div>

      <span className="intel-card__entity mono-label">{signal.entity.name}</span>

      <h3 className="intel-card__headline">{signal.headline}</h3>

      <p className="intel-card__so-what" data-testid="so-what">
        {signal.so_what}
      </p>

      {signal.why_it_matters ? (
        <p className="intel-card__tier-reason mono-label">
          ↳ {signal.why_it_matters}
        </p>
      ) : null}

      <footer className="intel-card__footer">
        <div className="intel-card__tags">
          {signal.primary_stakeholder ? (
            <span className="intel-card__tag intel-card__tag--audience">
              {personaLabel(signal.primary_stakeholder)}
            </span>
          ) : null}
          {areas.length > 0 ? (
            <>
              <span className="intel-card__tag-sep" aria-hidden="true">·</span>
              {areas.map((area) => (
                <span key={area} className="intel-card__tag intel-card__tag--area">
                  {area}
                </span>
              ))}
            </>
          ) : null}
        </div>
        {evidence ? (
          <p className="intel-card__source">
            <a href={evidence.source_url} target="_blank" rel="noreferrer">
              {evidence.source_name}
            </a>
            <span aria-hidden="true"> · </span>
            <time dateTime={evidence.captured_at}>
              {formatDate(evidence.captured_at)}
            </time>
          </p>
        ) : null}
      </footer>
    </article>
  );
}

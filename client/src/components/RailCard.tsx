import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { RailCardData } from "../config/railCopy";

interface RailCardProps {
  card: RailCardData;
  /** css var string for the group accent, e.g. "var(--sig-talent)" */
  accent: string;
  roomPath: string;
  /** index of this card's group, used by the scroll-sync logic */
  groupIndex: number;
  /** marks the first card of a group so the rail can find group offsets */
  isFirst?: boolean;
}

/** Derive the matching wash token from the accent var (naming convention). */
function washFor(accent: string): string {
  const m = accent.match(/^var\((--[a-z-]+)\)$/);
  if (m) return `var(${m[1]}-wash)`;
  return "var(--accent-wash)";
}

export function RailCard({
  card,
  accent,
  roomPath,
  groupIndex,
  isFirst,
}: RailCardProps) {
  const style = {
    "--c-accent": accent,
    "--c-wash": washFor(accent),
  } as CSSProperties;

  return (
    <Link
      to={roomPath}
      className="rail-card"
      style={style}
      data-testid="signal-card"
      data-gi={groupIndex}
      {...(isFirst ? { "data-first": "true" } : {})}
    >
      <div className="rail-card__top">
        <span className="rail-card__chip">{card.chip}</span>
        {card.date ? <time className="rail-card__date">{card.date}</time> : null}
      </div>
      <span className="rail-card__entity">{card.entity}</span>
      <h3 className="rail-card__headline">{card.headline}</h3>
      <p className="rail-card__summary">{card.summary}</p>
      <div className="rail-card__foot">
        {card.sourceName ? (
          <span className="rail-card__src">{card.sourceName}</span>
        ) : (
          <span />
        )}
        {card.persona ? (
          <span className="rail-card__persona">{card.persona}</span>
        ) : null}
      </div>
    </Link>
  );
}

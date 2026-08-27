import type { CSSProperties } from "react";
import type { Tier } from "../api/types";
import { TIER_HUE } from "../config/labels";
import "./TierBadge.css";

interface TierBadgeProps {
  tier: Tier;
  label: string;
}

export function TierBadge({ tier, label }: TierBadgeProps) {
  const hue = TIER_HUE[tier];
  const style = { "--tier-hue": hue } as CSSProperties;

  return (
    <span className="tier-badge" data-tier={tier} style={style}>
      {label}
    </span>
  );
}

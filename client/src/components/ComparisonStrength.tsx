import type { Strength, ThreatLevel } from "../utils/comparisonPresentation";
import { STRENGTH_LABELS } from "../utils/comparisonPresentation";
import "./ComparisonGrid.css";

export function StrengthBar({ strength }: { strength: Strength }) {
  return (
    <div className="comparison-strength-bar" aria-hidden="true">
      <div className="comparison-strength-bar__fill" data-strength={strength} />
    </div>
  );
}

export function ThreatChip({
  level,
  derived,
}: {
  level: ThreatLevel;
  derived?: boolean;
}) {
  const short = level === "Medium" ? "Med" : level;
  const label = derived ? `${short} · derived` : short;

  return (
    <span
      className="threat-chip"
      data-level={level}
      title={derived ? "Derived from claim counts" : undefined}
    >
      {label} threat
    </span>
  );
}

export function StrengthLabel({ strength }: { strength: Strength }) {
  return (
    <span className="mono-label strength-label" data-strength={strength}>
      {STRENGTH_LABELS[strength]}
    </span>
  );
}

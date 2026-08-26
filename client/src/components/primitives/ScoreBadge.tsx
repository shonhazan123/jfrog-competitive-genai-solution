import "./ScoreBadge.css";

type Tier = "low" | "mid" | "high" | "peak";

function getTier(value: number): Tier {
  if (value < 40) return "low";
  if (value < 60) return "mid";
  if (value < 80) return "high";
  return "peak";
}

interface ScoreBadgeProps {
  value: number;
}

export function ScoreBadge({ value }: ScoreBadgeProps) {
  const tier = getTier(value);

  return (
    <span className="score-badge" data-tier={tier}>
      {value}
    </span>
  );
}

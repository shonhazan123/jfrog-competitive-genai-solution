import type { Trend } from "../api/types";
import { GradeChip } from "./primitives/GradeChip";
import { SectionLabel } from "./primitives/SectionLabel";

interface TrendCardProps {
  trend: Trend;
}

const DIRECTION_LABELS: Record<Trend["direction"], string> = {
  toward_us: "Toward us",
  against_us: "Against us",
  lateral: "Lateral",
};

const VELOCITY_LABELS: Record<Trend["velocity"], string> = {
  accelerating: "Accelerating",
  steady: "Steady",
  emerging: "Emerging",
};

export function TrendCard({ trend }: TrendCardProps) {
  return (
    <article
      data-testid="trend-card"
      style={{
        padding: "var(--sp-4)",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        boxShadow: "var(--shadow-1)",
      }}
    >
      <h3
        style={{
          fontSize: "var(--fs-headline)",
          lineHeight: "var(--lh-headline)",
          fontWeight: 600,
          color: "var(--ink)",
          marginBottom: "var(--sp-3)",
        }}
      >
        {trend.title}
      </h3>

      <p
        style={{
          fontSize: "var(--fs-body)",
          lineHeight: "var(--lh-body)",
          color: "var(--ink-secondary)",
          marginBottom: "var(--sp-4)",
        }}
      >
        {trend.body}
      </p>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--sp-4)",
        }}
      >
        <div>
          <SectionLabel>DIRECTION</SectionLabel>
          <p
            data-testid="trend-direction"
            style={{
              fontSize: "var(--fs-meta)",
              fontWeight: 500,
              color: "var(--ink)",
              marginTop: "var(--sp-1)",
            }}
          >
            {DIRECTION_LABELS[trend.direction]}
          </p>
        </div>
        <div>
          <SectionLabel>VELOCITY</SectionLabel>
          <p
            data-testid="trend-velocity"
            style={{
              fontSize: "var(--fs-meta)",
              fontWeight: 500,
              color: "var(--ink)",
              marginTop: "var(--sp-1)",
            }}
          >
            {VELOCITY_LABELS[trend.velocity]}
          </p>
        </div>
        <div>
          <SectionLabel>CONFIDENCE</SectionLabel>
          <p
            data-testid="trend-confidence"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--sp-2)",
              fontSize: "var(--fs-meta)",
              color: "var(--ink)",
              marginTop: "var(--sp-1)",
            }}
          >
            <GradeChip grade={trend.confidence_grade} />
            <span>{trend.confidence_note}</span>
          </p>
        </div>
      </div>
    </article>
  );
}

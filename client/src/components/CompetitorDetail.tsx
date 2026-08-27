import type { ComparisonMatrix } from "../api/types";
import { SectionLabel } from "./primitives/SectionLabel";
import { StrengthBar, StrengthLabel, ThreatChip } from "./ComparisonStrength";
import {
  buildCompetitorSummary,
  deriveThreat,
  dimensionLabel,
  getCellForCompetitor,
  primaryEvidence,
  stanceToStrength,
} from "../utils/comparisonPresentation";
import "./CompetitorDetail.css";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

interface CompetitorDetailProps {
  matrix: ComparisonMatrix;
  competitorSlug: string;
  onClose: () => void;
}

export function CompetitorDetail({
  matrix,
  competitorSlug,
  onClose,
}: CompetitorDetailProps) {
  const competitor = matrix.competitors.find((row) => row.slug === competitorSlug);
  const threat = deriveThreat(matrix, competitorSlug);
  const summary = buildCompetitorSummary(matrix, competitorSlug);

  if (!competitor) return null;

  return (
    <div className="competitor-detail" data-testid="competitor-detail">
      <button type="button" className="competitor-detail__back" onClick={onClose}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
          <path
            d="M9 2L4 7L9 12"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Back to Competitors
      </button>

      <div className="competitor-detail__header">
        <h1 className="competitor-detail__title">{competitor.name}</h1>
        {threat ? (
          <ThreatChip level={threat.level} derived={threat.derived} />
        ) : null}
      </div>

      <hr className="competitor-detail__divider" />

      <p className="competitor-detail__summary">{summary}</p>

      <div className="competitor-detail__section-label">
        <SectionLabel>Capability Assessment</SectionLabel>
      </div>

      <div className="competitor-detail__cards">
        {matrix.dimensions.map((dimension) => {
          const cell = getCellForCompetitor(matrix, dimension.key, competitorSlug);
          const strength = stanceToStrength(cell?.stance);
          const evidence = primaryEvidence(cell);
          const label = dimensionLabel(dimension.key, dimension.name);

          return (
            <article
              key={dimension.key}
              className="competitor-detail__card"
              data-testid={`dimension-card-${dimension.key}`}
            >
              <div className="competitor-detail__card-header">
                <h2 className="competitor-detail__card-title">{label}</h2>
                <div className="competitor-detail__card-strength">
                  <StrengthBar strength={strength} />
                  <StrengthLabel strength={strength} />
                </div>
              </div>

              {cell?.stance !== "none" && cell?.summary ? (
                <p className="competitor-detail__position">{cell.summary}</p>
              ) : null}

              {evidence ? (
                <p className="competitor-detail__evidence">
                  {evidence.quote}
                  {" "}
                  <span className="competitor-detail__evidence-meta">
                    <a
                      href={evidence.source_url}
                      target="_blank"
                      rel="noreferrer"
                      data-testid={`evidence-link-${dimension.key}`}
                    >
                      {evidence.source_name}
                    </a>
                    {" · "}
                    {formatDate(evidence.captured_at)}
                  </span>
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}

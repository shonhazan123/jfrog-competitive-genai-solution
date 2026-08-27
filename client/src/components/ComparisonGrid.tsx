import { useState } from "react";
import type { ComparisonMatrix } from "../api/types";
import type { Strength } from "../utils/comparisonPresentation";
import {
  deriveThreat,
  dimensionLabel,
  getCellForCompetitor,
  stanceToStrength,
  STRENGTH_LABELS,
} from "../utils/comparisonPresentation";
import { CompetitorDetail } from "./CompetitorDetail";
import { StrengthBar, StrengthLabel, ThreatChip } from "./ComparisonStrength";
import "./ComparisonGrid.css";

interface ComparisonGridProps {
  matrix: ComparisonMatrix;
}

function StrengthCell({
  strength,
  position,
}: {
  strength: Strength;
  position: string;
}) {
  return (
    <div className="comparison-grid__matrix-cell-inner">
      <div className="comparison-grid__strength-row">
        <span className="strength-dot" data-strength={strength} aria-hidden="true" />
        <StrengthLabel strength={strength} />
      </div>
      <StrengthBar strength={strength} />
      {position ? (
        <p className="comparison-grid__position">{position}</p>
      ) : null}
    </div>
  );
}

export function ComparisonGrid({ matrix }: ComparisonGridProps) {
  const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(null);
  const dimensionCount = matrix.components.length;

  if (selectedCompetitor) {
    return (
      <CompetitorDetail
        matrix={matrix}
        competitorSlug={selectedCompetitor}
        onClose={() => setSelectedCompetitor(null)}
      />
    );
  }

  return (
    <div
      data-testid="table-scroll"
      style={{
        overflowX: "auto",
        ["--dimension-count" as string]: String(dimensionCount),
      }}
    >
      <div className="comparison-grid">
        <div className="comparison-grid__header-row">
          <div className="comparison-grid__header-cell">
            <span className="mono-label">Competitor</span>
          </div>
          {matrix.components.map((component) => (
            <div key={component.key} className="comparison-grid__header-cell">
              <span className="mono-label">
                {dimensionLabel(component.key, component.name)}
              </span>
            </div>
          ))}
        </div>

        <div className="comparison-grid__rows">
          {matrix.competitors.map((competitor) => {
            const threat = deriveThreat(matrix, competitor.slug);

            return (
              <button
                key={competitor.slug}
                type="button"
                className="comparison-grid__row"
                data-testid={`competitor-row-${competitor.slug}`}
                onClick={() => setSelectedCompetitor(competitor.slug)}
              >
                <div className="comparison-grid__competitor-cell">
                  <div className="comparison-grid__competitor-inner">
                    <div className="comparison-grid__competitor-info">
                      <div className="comparison-grid__competitor-name-row">
                        <span className="comparison-grid__competitor-name">
                          {competitor.name}
                        </span>
                        {threat ? (
                          <ThreatChip level={threat.level} derived={threat.derived} />
                        ) : null}
                      </div>
                    </div>
                    <svg
                      className="comparison-grid__arrow"
                      width="12"
                      height="12"
                      viewBox="0 0 12 12"
                      fill="none"
                      aria-hidden="true"
                    >
                      <path
                        d="M2.5 6H9.5M6.5 3L9.5 6L6.5 9"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                </div>

                {matrix.components.map((component) => {
                  const cell = getCellForCompetitor(
                    matrix,
                    component.key,
                    competitor.slug,
                  );
                  const strength = stanceToStrength(cell?.stance ?? "no_claim");
                  const position =
                    cell?.summary && cell.summary !== "No public claim on record."
                      ? cell.summary
                      : "";

                  return (
                    <div
                      key={component.key}
                      className="comparison-grid__matrix-cell"
                      data-testid={`matrix-cell-${competitor.slug}-${component.key}`}
                    >
                      <StrengthCell strength={strength} position={position} />
                    </div>
                  );
                })}
              </button>
            );
          })}
        </div>

        <div className="comparison-grid__legend">
          {(Object.keys(STRENGTH_LABELS) as Strength[]).map((key) => (
            <div key={key} className="comparison-grid__legend-item">
              <span className="strength-dot" data-strength={key} aria-hidden="true" />
              <span className="mono-label comparison-grid__legend-label">
                {STRENGTH_LABELS[key]}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

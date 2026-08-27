import type { AskEvidence, Citation } from "../api/types";
import { Cited } from "./Cited";
import { SourceLink } from "./SourceLink";
import "./CitationCard.css";

interface CitationCardProps {
  evidence: AskEvidence;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function evidenceCitation(evidence: AskEvidence): Citation {
  if (evidence.citation) {
    return evidence.citation;
  }
  return {
    source_name: evidence.source_name,
    source_url: evidence.source_url,
    captured_at: evidence.captured_at,
    origin: "extracted",
    archived_url: null,
    grade: evidence.reliability_grade,
  };
}

export function CitationCard({ evidence }: CitationCardProps) {
  const citation = evidenceCitation(evidence);

  return (
    <Cited citation={citation}>
      <article
        className="citation-badge"
        data-testid="citation-card"
        title={evidence.quote}
      >
        <span className="citation-badge__icon" aria-hidden="true">
          <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
            <path
              d="M1 4h6M4 1v6"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <span className="citation-badge__label">
          <SourceLink citation={citation} variant="name" />
          {" · "}
          <time dateTime={evidence.captured_at}>{formatDate(evidence.captured_at)}</time>
        </span>
      </article>
    </Cited>
  );
}

import type { AskEvidence } from "../api/types";
import { GradeChip } from "./primitives/GradeChip";
import { Quote } from "./primitives/Quote";

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

export function CitationCard({ evidence }: CitationCardProps) {
  return (
    <article
      data-testid="citation-card"
      style={{
        padding: "var(--sp-4)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-md)",
        background: "var(--surface)",
      }}
    >
      <p
        style={{
          fontSize: "var(--fs-mono)",
          color: "var(--ink-muted)",
          marginBottom: "var(--sp-2)",
        }}
      >
        [{evidence.n}]
      </p>
      <Quote>{evidence.quote}</Quote>
      <p
        style={{
          marginTop: "var(--sp-2)",
          fontSize: "var(--fs-meta)",
          lineHeight: "var(--lh-meta)",
          color: "var(--ink-secondary)",
        }}
      >
        <span>{evidence.source_name}</span>
        {" · "}
        <time dateTime={evidence.captured_at}>{formatDate(evidence.captured_at)}</time>
        {" · "}
        <GradeChip grade={evidence.reliability_grade} />
      </p>
    </article>
  );
}

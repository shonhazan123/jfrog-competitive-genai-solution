import type { SinceLastVisit as SinceLastVisitData } from "../api/types";

interface SinceLastVisitProps {
  data: SinceLastVisitData;
}

function formatVisitDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function SinceLastVisit({ data }: SinceLastVisitProps) {
  return (
    <div
      data-testid="since-last-visit"
      style={{
        padding: "var(--sp-3) var(--sp-4)",
        background: "var(--accent-wash)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-md)",
        fontSize: "var(--fs-body)",
        lineHeight: "var(--lh-body)",
        color: "var(--ink-secondary)",
      }}
    >
      Since you last looked: {data.new_signals} new signals and{" "}
      {data.claim_changes} claim changes since your visit on{" "}
      {formatVisitDate(data.last_visit_at)}
    </div>
  );
}

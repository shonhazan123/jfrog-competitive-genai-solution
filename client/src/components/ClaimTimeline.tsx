import type { ArchiveTimeline, Claim } from "../api/types";
import { SectionLabel } from "./primitives/SectionLabel";
import { WasNow } from "./primitives/WasNow";

function formatYearMonth(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    month: "short",
    year: "numeric",
  });
}

interface ClaimTimelineProps {
  timeline: ArchiveTimeline;
  claims: Claim[];
}

export function ClaimTimeline({ timeline, claims }: ClaimTimelineProps) {
  const claimsWithChange = claims.filter((claim) => claim.change);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-4)",
      }}
    >
      <div>
        <h3
          style={{
            fontSize: "var(--fs-h2)",
            lineHeight: "var(--lh-h2)",
            fontWeight: 600,
            marginBottom: "var(--sp-2)",
          }}
        >
          Sonatype&apos;s JFrog comparison page, 2021 → 2026
        </h3>
        <p
          style={{
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
            marginBottom: "var(--sp-4)",
          }}
        >
          {timeline.total_versions} archived content versions
          {timeline.sampled ? ", sampled, not continuous" : ""}
        </p>
        <ol
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            display: "flex",
            flexDirection: "column",
            gap: "var(--sp-3)",
          }}
        >
          {timeline.versions.map((version) => (
            <li
              key={version.captured_at}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--sp-1)",
                paddingLeft: version.is_milestone ? "var(--sp-3)" : 0,
                borderLeft: version.is_milestone
                  ? "2px solid var(--accent)"
                  : "2px solid var(--border)",
              }}
            >
              <span
                style={{
                  fontSize: "var(--fs-meta)",
                  color: "var(--ink-muted)",
                }}
              >
                {formatYearMonth(version.captured_at)}
              </span>
              <span
                style={{
                  fontSize: "var(--fs-body)",
                  lineHeight: "var(--lh-body)",
                }}
              >
                {version.label}
              </span>
            </li>
          ))}
        </ol>
        <p
          style={{
            marginTop: "var(--sp-3)",
            fontSize: "var(--fs-meta)",
            color: "var(--ink-muted)",
          }}
        >
          {timeline.method} · {timeline.total_versions} distinct versions
        </p>
      </div>

      {claimsWithChange.length > 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--sp-3)",
          }}
        >
          <SectionLabel>Claim changes</SectionLabel>
          {claimsWithChange.map((claim) =>
            claim.change ? (
              <div key={claim.id}>
                <p
                  style={{
                    fontSize: "var(--fs-meta)",
                    color: "var(--ink-muted)",
                    marginBottom: "var(--sp-1)",
                  }}
                >
                  {claim.change.dimension}
                </p>
                <WasNow was={claim.change.was} now={claim.change.now} />
              </div>
            ) : null,
          )}
        </div>
      ) : null}
    </div>
  );
}

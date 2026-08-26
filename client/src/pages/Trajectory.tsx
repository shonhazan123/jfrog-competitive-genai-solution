import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ArchiveTimeline, ArchiveVersion, Citation } from "../api/types";
import { SourceLink } from "../components/SourceLink";
import { Panel } from "../components/primitives/Panel";
import timelineFixture from "../fixtures/claims_history_timeline.json";

const SOURCE_ID = "src_sonatype_comparison";

function formatYearMonth(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    month: "short",
    year: "numeric",
  });
}

function toArchiveStamp(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}`;
}

function buildArchiveCitation(
  timeline: ArchiveTimeline,
  version: ArchiveVersion,
): Citation {
  const stamp = toArchiveStamp(version.captured_at);
  return {
    source_name: "Sonatype comparison page",
    source_url: timeline.source_url,
    captured_at: version.captured_at,
    origin: "archive",
    archived_url: `https://web.archive.org/web/${stamp}id_/${timeline.source_url}`,
    grade: null,
  };
}

export function Trajectory() {
  const { data: timeline } = useQuery({
    queryKey: ["claimHistory", SOURCE_ID],
    queryFn: () => api.getClaimHistory(SOURCE_ID),
    initialData: timelineFixture as ArchiveTimeline,
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-5)",
        maxWidth: "var(--content-max)",
      }}
    >
      <header>
        <h1 className="page-heading">Trajectory</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          How a competitor&apos;s argument against us evolved over five years —
          archived captures of their public comparison page.
        </p>
      </header>

      <Panel>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--sp-4)",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: "var(--fs-h2)",
                lineHeight: "var(--lh-h2)",
                fontWeight: 600,
                marginBottom: "var(--sp-2)",
              }}
            >
              Sonatype&apos;s JFrog comparison page, 2021 → 2026
            </h2>
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
              {timeline.versions.map((version) => {
                const citation = buildArchiveCitation(timeline, version);
                return (
                  <li
                    key={version.captured_at}
                    data-testid="timeline-entry"
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
                    <time
                      dateTime={version.captured_at}
                      style={{
                        fontSize: "var(--fs-meta)",
                        color: "var(--ink-muted)",
                      }}
                    >
                      {formatYearMonth(version.captured_at)}
                    </time>
                    <span
                      style={{
                        fontSize: "var(--fs-body)",
                        lineHeight: "var(--lh-body)",
                      }}
                    >
                      {version.label}
                    </span>
                    <SourceLink citation={citation} />
                  </li>
                );
              })}
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
        </div>
      </Panel>
    </div>
  );
}

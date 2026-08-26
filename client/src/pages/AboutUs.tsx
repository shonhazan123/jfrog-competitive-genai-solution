import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ArchiveTimeline, Claim, ListResponse } from "../api/types";
import { ClaimTimeline } from "../components/ClaimTimeline";
import { GradeChip } from "../components/primitives/GradeChip";
import { Panel } from "../components/primitives/Panel";
import { Quote } from "../components/primitives/Quote";
import { SectionLabel } from "../components/primitives/SectionLabel";
import { WasNow } from "../components/primitives/WasNow";
import claimsFixture from "../fixtures/claims_about_jfrog.json";
import timelineFixture from "../fixtures/claims_history_timeline.json";

const SOURCE_ID = "src_sonatype_comparison";

export function AboutUs() {
  const { data: claimsData } = useQuery({
    queryKey: ["claims", { subject: "jfrog" }],
    queryFn: () => api.getClaims({ subject: "jfrog", include_history: true }),
    initialData: claimsFixture as ListResponse<Claim>,
  });

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
        <h1 className="page-heading">Competitors → Us</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          What competitors publicly claim about JFrog, with history.
        </p>
      </header>

      <Panel>
        <ClaimTimeline timeline={timeline} claims={claimsData.items} />
      </Panel>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-4)",
        }}
      >
        {claimsData.items.map((claim) => {
          const primaryEvidence =
            claim.evidence.find((e) => e.is_primary) ?? claim.evidence[0];

          return (
            <Panel key={claim.id}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--sp-3)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--sp-2)",
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontSize: "var(--fs-meta)",
                      fontWeight: 500,
                      color: "var(--ink-muted)",
                      textTransform: "uppercase",
                    }}
                  >
                    {claim.asserting_entity} → {claim.subject_entity}
                  </span>
                  <span data-testid="grade-chip">
                    <GradeChip grade={claim.reliability_grade} />
                  </span>
                </div>

                <h2
                  style={{
                    fontSize: "var(--fs-headline)",
                    lineHeight: "var(--lh-headline)",
                    fontWeight: 600,
                  }}
                >
                  {claim.claim_text}
                </h2>

                <div>
                  <SectionLabel>
                    {claim.change ? "Evidence · was → now" : "Evidence"}
                  </SectionLabel>
                  {claim.change ? (
                    <div style={{ marginTop: "var(--sp-2)" }}>
                      <WasNow was={claim.change.was} now={claim.change.now} />
                    </div>
                  ) : null}
                  {primaryEvidence ? (
                    <div style={{ marginTop: "var(--sp-3)" }}>
                      <Quote>{primaryEvidence.quote}</Quote>
                      <p
                        style={{
                          marginTop: "var(--sp-2)",
                          fontSize: "var(--fs-meta)",
                          color: "var(--ink-muted)",
                        }}
                      >
                        <a
                          href={primaryEvidence.source_url}
                          style={{ color: "var(--accent)" }}
                        >
                          {primaryEvidence.source_name}
                        </a>
                      </p>
                    </div>
                  ) : null}
                </div>
              </div>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}

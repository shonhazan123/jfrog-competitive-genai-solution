import { useState } from "react";
import { Chip, type SignalType } from "../components/primitives/Chip";
import { GradeChip } from "../components/primitives/GradeChip";
import { ScoreBadge } from "../components/primitives/ScoreBadge";
import { Panel } from "../components/primitives/Panel";
import { SectionLabel } from "../components/primitives/SectionLabel";
import { Disclosure } from "../components/primitives/Disclosure";
import { EmptyState } from "../components/primitives/EmptyState";
import { FilterChips } from "../components/primitives/FilterChips";
import { Quote } from "../components/primitives/Quote";
import { WasNow } from "../components/primitives/WasNow";

const guideLayout = {
  display: "flex",
  flexDirection: "column" as const,
  gap: "var(--sp-5)",
  maxWidth: "var(--content-max)",
};

const introStyle = {
  margin: "var(--sp-2) 0 0",
  fontSize: "var(--fs-body)",
  lineHeight: "var(--lh-body)",
  color: "var(--ink-secondary)",
};

const rowStyle = {
  display: "flex",
  flexWrap: "wrap" as const,
  gap: "var(--sp-2)",
  alignItems: "center",
};

const stackStyle = {
  display: "flex",
  flexDirection: "column" as const,
  gap: "var(--sp-3)",
};

const itemStyle = {
  display: "flex",
  flexDirection: "column" as const,
  alignItems: "center",
  gap: "var(--sp-1)",
};

const captionStyle = {
  fontSize: "var(--fs-meta)",
  lineHeight: "var(--lh-meta)",
  color: "var(--ink-muted)",
};

const SIGNAL_TYPES: SignalType[] = [
  "product_capability",
  "positioning_messaging",
  "pricing_packaging",
  "security_trust",
  "corporate_financial",
  "partnership_ecosystem",
  "customer_evidence",
  "market_regulatory",
  "talent_org",
];

const SCORE_TIERS = [
  { value: 22, label: "low (<40)" },
  { value: 48, label: "mid (40–59)" },
  { value: 71, label: "high (60–79)" },
  { value: 91, label: "peak (≥80)" },
];

const GRADES = ["A1", "A2", "B3", "C2", "D1", "E3", "F"];

const SECTION_LABELS = [
  "SO WHAT",
  "EVIDENCE",
  "WHY THIS SCORE",
  "HOW THIS WAS PRODUCED",
];

export function StyleGuide() {
  const [filter, setFilter] = useState("All");

  return (
    <div style={guideLayout}>
      <h1 className="page-heading">Style Guide</h1>
      <p style={introStyle}>
        Every primitive in every state — the design review surface.
      </p>

      <Panel title="Signal Chips (hue system)">
        <div style={rowStyle}>
          {SIGNAL_TYPES.map((type) => (
            <Chip key={type} signalType={type} />
          ))}
        </div>
      </Panel>

      <Panel title="Score Badges (weight system)">
        <div style={rowStyle}>
          {SCORE_TIERS.map(({ value, label }) => (
            <div key={value} style={itemStyle}>
              <ScoreBadge value={value} />
              <span style={captionStyle}>{label}</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Grade Chips (form system)">
        <div style={rowStyle}>
          {GRADES.map((grade) => (
            <GradeChip key={grade} grade={grade} />
          ))}
        </div>
      </Panel>

      <Panel title="Section Labels">
        <div style={stackStyle}>
          {SECTION_LABELS.map((label) => (
            <SectionLabel key={label}>{label}</SectionLabel>
          ))}
        </div>
      </Panel>

      <Panel title="Quote">
        <Quote>
          SBOM ingestion for CycloneDX 1.6 — export only is no longer the full
          story.
        </Quote>
      </Panel>

      <Panel title="Was / Now">
        <WasNow was="export only" now="ingestion + export" />
      </Panel>

      <Panel title="Disclosure">
        <Disclosure label="Why this score">
          <p>
            Base materiality 62 + recency bonus 8 + source grade A2 adjustment
            +5 − persona weight −3 = 72
          </p>
        </Disclosure>
        <Disclosure label="How this was produced">
          <p>
            Scraped Sonatype release notes at 06:00 UTC. Extracted via LLM,
            validated against two independent sources.
          </p>
        </Disclosure>
      </Panel>

      <Panel title="Empty State">
        <EmptyState
          headline="No pricing changes for Sonatype in 30 days."
          detail="Checked 14 times."
        />
      </Panel>

      <Panel title="Filter Chips">
        <FilterChips
          options={["All", "Product", "Security", "Pricing"]}
          selected={filter}
          onChange={setFilter}
        />
      </Panel>
    </div>
  );
}

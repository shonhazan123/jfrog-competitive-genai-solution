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
import "./StyleGuide.css";

const TYPE_FAMILIES = [
  {
    token: "--font-sans",
    label: "Outfit",
    role: "Sans — body & UI",
    className: "style-guide__type-sans",
    sample: "Capability landscape at 15px body scale",
  },
  {
    token: "--font-serif",
    label: "Fraunces",
    role: "Display serif",
    className: "style-guide__type-display font-display",
    sample: "Editorial verdict at display scale",
  },
  {
    token: "--font-mono",
    label: "DM Mono",
    role: "Mono — labels & meta",
    className: "mono-label",
    sample: "POSITIONAL MAP · AUG 27, 2026",
  },
];

const TIER_TOKENS = [
  { token: "--tier-act", wash: "--tier-act-wash", label: "Act on it" },
  { token: "--tier-worth", wash: "--tier-worth-wash", label: "Worth knowing" },
  { token: "--tier-bg", wash: "--tier-bg-wash", label: "Background" },
];

const BRAND_TOKENS = [
  { token: "--brand-jfrog", wash: "--brand-jfrog-wash", label: "JFrog brand" },
];

const SIG_TOKENS = [
  { token: "--sig-product", wash: "--sig-product-wash", label: "Product" },
  { token: "--sig-security", wash: "--sig-security-wash", label: "Security" },
  { token: "--sig-pricing", wash: "--sig-pricing-wash", label: "Pricing" },
  {
    token: "--sig-positioning",
    wash: "--sig-positioning-wash",
    label: "Positioning",
  },
  { token: "--sig-regulatory", wash: "--sig-regulatory-wash", label: "Regulatory" },
  {
    token: "--sig-partnership",
    wash: "--sig-partnership-wash",
    label: "Partnership",
  },
  { token: "--sig-customer", wash: "--sig-customer-wash", label: "Customer" },
  { token: "--sig-corporate", wash: "--sig-corporate-wash", label: "Corporate" },
  { token: "--sig-talent", wash: "--sig-talent-wash", label: "Talent" },
];

const SPACE_TOKENS = [
  { token: "--sp-2", px: 8 },
  { token: "--sp-3", px: 12 },
  { token: "--sp-4", px: 16 },
  { token: "--sp-5", px: 24 },
];

const RADIUS_TOKENS = [
  { token: "--r-sm", className: "style-guide__radius-demo" },
  { token: "--r-md", className: "style-guide__radius-demo" },
  { token: "--r-lg", className: "style-guide__radius-demo" },
];

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

interface ColourSwatchProps {
  token: string;
  wash: string;
  label: string;
}

function ColourSwatch({ token, wash, label }: ColourSwatchProps) {
  return (
    <div className="style-guide__swatch">
      <div className="style-guide__swatch-row">
        <div
          className="style-guide__swatch-fg"
          style={{ backgroundColor: `var(${token})` }}
          aria-hidden="true"
        />
        <div
          className="style-guide__swatch-wash"
          style={{ backgroundColor: `var(${wash})` }}
          aria-hidden="true"
        />
      </div>
      <span className="style-guide__swatch-label mono-label">{label}</span>
      <span className="style-guide__swatch-token">
        {token} · {wash}
      </span>
    </div>
  );
}

export function StyleGuide() {
  const [filter, setFilter] = useState("All");

  return (
    <div className="style-guide">
      <h1 className="page-heading font-display">Style Guide</h1>
      <p className="style-guide__intro">
        Token-driven design system — type, colour, spacing, and primitives in every
        state.
      </p>

      <Panel title="Typography">
        <div className="style-guide__type-stack">
          {TYPE_FAMILIES.map((family) => (
            <div key={family.token} className="style-guide__type-sample">
              <span className="mono-label">{family.role}</span>
              <p className={family.className}>{family.sample}</p>
              <span className="style-guide__type-token">
                {family.label} · {family.token}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Type helpers">
        <p className="style-guide__helper-sample font-display">
          .font-display — Fraunces for editorial headings &amp; verdicts
        </p>
        <p className="mono-label">
          .mono-label — uppercase tracked DM Mono eyebrow
        </p>
        <p className="style-guide__helper-note">
          Used on page eyebrows (Positional Map, Pull Layer, Landscape), tally
          strips, group headers, and source meta.
        </p>
      </Panel>

      <Panel title="Verdict tiers">
        <div className="style-guide__swatch-grid">
          {TIER_TOKENS.map((entry) => (
            <ColourSwatch key={entry.token} {...entry} />
          ))}
        </div>
      </Panel>

      <Panel title="JFrog brand">
        <div className="style-guide__swatch-grid">
          {BRAND_TOKENS.map((entry) => (
            <ColourSwatch key={entry.token} {...entry} />
          ))}
        </div>
      </Panel>

      <Panel title="Signal hues (type system)">
        <div className="style-guide__swatch-grid">
          {SIG_TOKENS.map((entry) => (
            <ColourSwatch key={entry.token} {...entry} />
          ))}
        </div>
      </Panel>

      <Panel title="Spacing tokens">
        <div className="style-guide__space-row">
          {SPACE_TOKENS.map(({ token, px }) => (
            <div key={token} className="style-guide__space-block">
              <div
                className="style-guide__space-demo"
                style={{
                  width: `var(${token})`,
                  height: `var(${token})`,
                }}
                aria-hidden="true"
              />
              <span className="style-guide__swatch-token">{token}</span>
              <span className="style-guide__caption">{px}px</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Radius tokens">
        <div className="style-guide__radius-row">
          {RADIUS_TOKENS.map(({ token }) => (
            <div key={token} className="style-guide__space-block">
              <div
                className="style-guide__radius-demo"
                style={{ borderRadius: `var(${token})` }}
                aria-hidden="true"
              />
              <span className="style-guide__swatch-token">{token}</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Signal Chips (hue system)">
        <div className="style-guide__primitive-row">
          {SIGNAL_TYPES.map((type) => (
            <Chip key={type} signalType={type} />
          ))}
        </div>
      </Panel>

      <Panel title="Score Badges (weight system)">
        <div className="style-guide__primitive-row">
          {SCORE_TIERS.map(({ value, label }) => (
            <div key={value} className="style-guide__primitive-item">
              <ScoreBadge value={value} />
              <span className="style-guide__caption">{label}</span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Grade Chips (form system)">
        <div className="style-guide__primitive-row">
          {GRADES.map((grade) => (
            <GradeChip key={grade} grade={grade} />
          ))}
        </div>
      </Panel>

      <Panel title="Section Labels">
        <div className="style-guide__primitive-stack">
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

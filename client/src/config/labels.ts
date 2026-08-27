import type { Persona, SignalType, Tier } from "../api/types";

/** Mirrors config/labels.yaml — human labels for every machine value. */
const SIGNAL_TYPE_LABELS: Record<SignalType, string> = {
  product_capability: "Product release",
  positioning_messaging: "Positioning",
  pricing_packaging: "Pricing & packaging",
  security_trust: "Security advisory",
  corporate_financial: "Corporate",
  partnership_ecosystem: "Partnership",
  customer_evidence: "Customer evidence",
  market_regulatory: "Industry & regulation",
  talent_org: "Hiring signal",
};

const PRIORITY_BANDS = [
  { max: 39, label: "Watch" },
  { max: 59, label: "Notable" },
  { max: 79, label: "High" },
  { max: 100, label: "Critical" },
] as const;

const STATE_LABELS = {
  interrupt: "Needs attention today",
  no_change: "No change in this run",
  caution: "Handle with care — lead on posture, not the advisory",
  authored: "Authored by the CI team",
  absent: "No public claim on record",
} as const;

const PERSONA_LABELS: Record<Persona, string> = {
  sales: "Sales",
  product: "Product",
  exec: "Executive",
};

const ORIGIN_LABELS = {
  extracted: "From the source",
  authored: "Authored by the CI team",
  archive: "From the web archive",
} as const;

export const TIER_HUE: Record<Tier, string> = {
  act_on_it: "var(--tier-act)",
  worth_knowing: "var(--tier-worth)",
  background: "var(--tier-bg)",
};

const HUE_TOKENS: Record<SignalType, string> = {
  product_capability: "var(--sig-product)",
  positioning_messaging: "var(--sig-positioning)",
  pricing_packaging: "var(--sig-pricing)",
  security_trust: "var(--sig-security)",
  corporate_financial: "var(--sig-corporate)",
  partnership_ecosystem: "var(--sig-partnership)",
  customer_evidence: "var(--sig-customer)",
  market_regulatory: "var(--sig-regulatory)",
  talent_org: "var(--sig-talent)",
};

export type StateKey = keyof typeof STATE_LABELS;
export type OriginKey = keyof typeof ORIGIN_LABELS;

/** Canonical display order for the nine signal types (keys of the label map). */
export const SIGNAL_TYPE_ORDER = Object.keys(SIGNAL_TYPE_LABELS) as SignalType[];

export function signalTypeLabel(type: SignalType): string {
  return SIGNAL_TYPE_LABELS[type];
}

export function priorityLabel(score: number): string {
  for (const band of PRIORITY_BANDS) {
    if (score <= band.max) return band.label;
  }
  return "Critical";
}

export function stateLabel(state: StateKey): string {
  return STATE_LABELS[state];
}

export function personaLabel(persona: Persona): string {
  return PERSONA_LABELS[persona];
}

export function originLabel(origin: OriginKey): string {
  return ORIGIN_LABELS[origin];
}

export function signalHue(type: SignalType): string {
  return HUE_TOKENS[type];
}

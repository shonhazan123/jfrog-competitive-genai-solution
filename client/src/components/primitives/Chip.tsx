import type { CSSProperties } from "react";
import "./Chip.css";

export type SignalType =
  | "product_capability"
  | "positioning_messaging"
  | "pricing_packaging"
  | "security_trust"
  | "corporate_financial"
  | "partnership_ecosystem"
  | "customer_evidence"
  | "market_regulatory"
  | "talent_org";

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

const LABELS: Record<SignalType, string> = {
  product_capability: "Product Release",
  positioning_messaging: "Positioning",
  pricing_packaging: "Pricing",
  security_trust: "Security",
  corporate_financial: "Corporate",
  partnership_ecosystem: "Partnership",
  customer_evidence: "Customer Evidence",
  market_regulatory: "Regulatory",
  talent_org: "Talent",
};

interface ChipProps {
  signalType: SignalType | string;
}

export function Chip({ signalType }: ChipProps) {
  const type = signalType as SignalType;
  const hue = HUE_TOKENS[type] ?? "var(--sig-product)";
  const label = LABELS[type] ?? signalType;

  const style = { "--chip-hue": hue } as CSSProperties;

  return (
    <span className="chip" style={style}>
      {label}
    </span>
  );
}

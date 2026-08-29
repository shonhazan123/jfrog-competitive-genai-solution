import type { ReactNode } from "react";
import type { IndustryRadarItem, Signal, SignalType } from "../api/types";
import {
  personaLabel,
  SIGNAL_TYPE_ORDER,
  signalHue,
  signalTypeLabel,
} from "./labels";

/** One card as the rail renders it — flattened from a Signal or an
 *  IndustryRadarItem so RailCard never has to know which source it came from. */
export interface RailCardData {
  id: string;
  chip: string;
  entity: string;
  headline: string;
  summary: string;
  persona: string | null;
  sourceName: string | null;
  sourceUrl: string | null;
  date: string;
}

export interface RailGroup {
  key: string;
  shortLabel: string;
  title: ReactNode;
  explain: string;
  /** css var string, e.g. "var(--sig-talent)" */
  accent: string;
  cards: RailCardData[];
}

/** Colour the type keyword in the group accent. */
function kw(word: string): ReactNode {
  return <span className="rail-kw">{word}</span>;
}

/** Expanded heading + one-line explainer per signal type (mockup copy). */
export const RAIL_COPY: Record<SignalType, { title: ReactNode; explain: string }> = {
  talent_org: {
    title: <>Recent {kw("Hiring")}</>,
    explain:
      "Open roles reveal where rivals are placing their bets — before any announcement does.",
  },
  pricing_packaging: {
    title: <>{kw("Pricing")} & Packaging</>,
    explain:
      "List-price and tier changes buyers will hold you to in the next deal.",
  },
  corporate_financial: {
    title: <>{kw("Corporate")} Moves</>,
    explain:
      "Funding, M&A and leadership shifts that change who you're really up against.",
  },
  product_capability: {
    title: <>{kw("Product")} Releases</>,
    explain: "What rivals just shipped, and the wedge each new capability opens.",
  },
  security_trust: {
    title: <>{kw("Security")} & Supply-Chain</>,
    explain:
      "Vulnerabilities and attacks moving through the software supply chain.",
  },
  market_regulatory: {
    title: <>{kw("Regulatory")} & Standards</>,
    explain: "Compliance mandates reshaping what buyers must require of you.",
  },
  positioning_messaging: {
    title: <>{kw("Positioning")} & Messaging</>,
    explain: "How rivals frame themselves — and where they aim claims at you.",
  },
  partnership_ecosystem: {
    title: <>{kw("Partnerships")} & Ecosystem</>,
    explain:
      "Alliances and integrations that extend a rival's reach into your accounts.",
  },
  customer_evidence: {
    title: <>{kw("Customer")} Evidence</>,
    explain: "Case studies and wins that show who's choosing whom, and why.",
  },
};

function copyFor(type: SignalType): { title: ReactNode; explain: string } {
  return (
    RAIL_COPY[type] ?? {
      title: <>{kw(signalTypeLabel(type))}</>,
      explain: "Recent moves worth keeping an eye on.",
    }
  );
}

function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function signalToCard(signal: Signal): RailCardData {
  const evidence = signal.evidence?.[0];
  return {
    id: signal.id,
    chip: signalTypeLabel(signal.signal_type),
    entity: signal.entity?.name ?? "",
    headline: signal.headline,
    summary: signal.so_what,
    persona: signal.primary_stakeholder
      ? personaLabel(signal.primary_stakeholder)
      : null,
    sourceName: evidence?.source_name ?? null,
    sourceUrl: evidence?.source_url ?? null,
    date: formatShortDate(evidence?.captured_at ?? signal.occurred_at),
  };
}

/** Group competitor signals by signal_type, Hiring first then canonical order. */
export function groupSignals(signals: Signal[]): RailGroup[] {
  const byType = new Map<SignalType, Signal[]>();
  for (const s of signals) {
    const list = byType.get(s.signal_type);
    if (list) list.push(s);
    else byType.set(s.signal_type, [s]);
  }

  const order: SignalType[] = [
    "talent_org",
    ...SIGNAL_TYPE_ORDER.filter((t) => t !== "talent_org"),
  ];

  const groups: RailGroup[] = [];
  for (const type of order) {
    const items = byType.get(type);
    if (!items || items.length === 0) continue;
    const { title, explain } = copyFor(type);
    groups.push({
      key: type,
      shortLabel: signalTypeLabel(type),
      title,
      explain,
      accent: signalHue(type),
      cards: items.map(signalToCard),
    });
  }
  return groups;
}

const SIGNAL_TYPES = new Set<string>(SIGNAL_TYPE_ORDER);

function asSignalType(raw: string): SignalType | null {
  return SIGNAL_TYPES.has(raw) ? (raw as SignalType) : null;
}

function industryToCard(item: IndustryRadarItem): RailCardData {
  const evidence = item.evidence?.[0];
  const mapped = asSignalType(item.signal_type);
  return {
    id: item.id,
    chip: mapped ? signalTypeLabel(mapped) : item.signal_type.replace(/_/g, " "),
    entity: "Industry",
    headline: item.headline,
    summary: item.summary,
    persona: null,
    sourceName: evidence?.source_name ?? null,
    sourceUrl: evidence?.source_url ?? null,
    date: formatShortDate(item.occurred_at ?? evidence?.captured_at),
  };
}

/** Group industry radar items by their signal_type string, mapped to the
 *  matching SignalType for hue/label/copy; unknown types fall back gracefully. */
export function groupIndustry(items: IndustryRadarItem[]): RailGroup[] {
  const byType = new Map<string, IndustryRadarItem[]>();
  for (const item of items) {
    const list = byType.get(item.signal_type);
    if (list) list.push(item);
    else byType.set(item.signal_type, [item]);
  }

  // Order known types by the canonical order; unknown ones keep insertion order.
  const keys = [...byType.keys()];
  keys.sort((a, b) => {
    const ia = SIGNAL_TYPE_ORDER.indexOf(a as SignalType);
    const ib = SIGNAL_TYPE_ORDER.indexOf(b as SignalType);
    const ra = ia === -1 ? Number.MAX_SAFE_INTEGER : ia;
    const rb = ib === -1 ? Number.MAX_SAFE_INTEGER : ib;
    return ra - rb;
  });

  const groups: RailGroup[] = [];
  for (const key of keys) {
    const items2 = byType.get(key)!;
    const mapped = asSignalType(key);
    if (mapped) {
      const { title, explain } = copyFor(mapped);
      groups.push({
        key,
        shortLabel: signalTypeLabel(mapped),
        title,
        explain,
        accent: signalHue(mapped),
        cards: items2.map(industryToCard),
      });
    } else {
      const label = key.replace(/_/g, " ");
      groups.push({
        key,
        shortLabel: label,
        title: <>{kw(label)}</>,
        explain: "Recent developments across the wider market.",
        accent: "var(--accent)",
        cards: items2.map(industryToCard),
      });
    }
  }
  return groups;
}

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  ExecWeekly,
  ListResponse,
  Signal,
  SignalType,
} from "../api/types";
import { SignalAccordionRow } from "../components/SignalAccordionRow";
import { TrendCard } from "../components/TrendCard";
import { FilterChips } from "../components/primitives/FilterChips";
import { SIGNAL_TYPE_ORDER, signalTypeLabel } from "../config/labels";
import digestExecWeeklyFixture from "../fixtures/digest_exec_weekly.json";
import signalsProductFixture from "../fixtures/signals_product.json";
import signalsSalesFixture from "../fixtures/signals_sales.json";
import "./Divisions.css";

type DivisionTab = "sales" | "product" | "executive";
type FilterValue = "all" | SignalType;

const PERSONA_TABS: { id: DivisionTab; label: string }[] = [
  { id: "sales", label: "Sales" },
  { id: "product", label: "Product" },
  { id: "executive", label: "Executive" },
];

interface CompanyGroup {
  slug: string;
  name: string;
  items: Signal[];
}

function countByType(items: Signal[]): Partial<Record<SignalType, number>> {
  const counts: Partial<Record<SignalType, number>> = {};
  for (const signal of items) {
    counts[signal.signal_type] = (counts[signal.signal_type] ?? 0) + 1;
  }
  return counts;
}

/** Group a persona's signals into clear per-company sections, ordered by
 *  first appearance in the (already tier-ranked) API list. */
function groupByCompany(items: Signal[]): CompanyGroup[] {
  const groups = new Map<string, CompanyGroup>();
  for (const signal of items) {
    const slug = signal.entity?.slug ?? "unknown";
    const existing = groups.get(slug);
    if (existing) {
      existing.items.push(signal);
    } else {
      groups.set(slug, {
        slug,
        name: signal.entity?.name ?? "Unknown",
        items: [signal],
      });
    }
  }
  return [...groups.values()];
}

export function Divisions() {
  const [tab, setTab] = useState<DivisionTab>("sales");
  const [selectedFilter, setSelectedFilter] = useState<FilterValue>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: salesSignals } = useQuery({
    queryKey: ["signals", "sales"],
    queryFn: () => api.getSignals({ persona: "sales" }),
    initialData: signalsSalesFixture as ListResponse<Signal>,
  });

  const { data: productSignals } = useQuery({
    queryKey: ["signals", "product"],
    queryFn: () => api.getSignals({ persona: "product" }),
    initialData: signalsProductFixture as ListResponse<Signal>,
  });

  const { data: execWeekly } = useQuery({
    queryKey: ["exec-weekly"],
    queryFn: () => api.getExecWeekly(),
    initialData: digestExecWeeklyFixture as ExecWeekly,
  });

  const activeItems =
    tab === "product" ? productSignals.items : salesSignals.items;

  const typeCounts = useMemo(() => countByType(activeItems), [activeItems]);
  const presentTypes = SIGNAL_TYPE_ORDER.filter(
    (type) => (typeCounts[type] ?? 0) > 0,
  );

  const filterChips = useMemo(() => {
    const entries: { value: FilterValue; label: string }[] = [
      { value: "all", label: `All (${activeItems.length})` },
    ];
    for (const type of presentTypes) {
      entries.push({
        value: type,
        label: `${signalTypeLabel(type)} (${typeCounts[type] ?? 0})`,
      });
    }
    return entries;
  }, [activeItems.length, presentTypes, typeCounts]);

  const selectedChipLabel =
    filterChips.find((entry) => entry.value === selectedFilter)?.label ??
    filterChips[0].label;

  const filteredItems = useMemo(() => {
    if (selectedFilter === "all") {
      return activeItems;
    }
    return activeItems.filter((signal) => signal.signal_type === selectedFilter);
  }, [activeItems, selectedFilter]);

  const companyGroups = useMemo(
    () => groupByCompany(filteredItems),
    [filteredItems],
  );

  const handleTab = (next: DivisionTab) => {
    setTab(next);
    setSelectedFilter("all");
    setExpandedId(null);
  };

  const handleFilterChange = (label: string) => {
    const entry = filterChips.find((chip) => chip.label === label);
    if (entry) {
      setSelectedFilter(entry.value);
      setExpandedId(null);
    }
  };

  const handleToggle = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="divisions-page">
      <header>
        <span className="mono-label divisions-page__eyebrow">Persona Lens</span>
        <h1 className="page-heading font-display">Divisions</h1>
        <p className="divisions-page__intro">
          The same intel, read through one team's priorities. Switch the persona
          lens, filter by signal type, and each competitor's moves are grouped
          together — expand a row for the intent read.
        </p>
      </header>

      <div
        role="tablist"
        aria-label="Persona views"
        className="divisions-page__tabs"
      >
        {PERSONA_TABS.map((persona) => (
          <button
            key={persona.id}
            type="button"
            role="tab"
            aria-selected={tab === persona.id}
            className={`divisions-page__tab${
              tab === persona.id ? " divisions-page__tab--active" : ""
            }`}
            onClick={() => handleTab(persona.id)}
          >
            {persona.label}
          </button>
        ))}
      </div>

      {tab === "executive" ? (
        <div className="divisions-page__exec">
          <p className="divisions-page__exec-lead">{execWeekly.lead}</p>
          {execWeekly.trends.map((trend) => (
            <TrendCard key={trend.id} trend={trend} />
          ))}
          {execWeekly.stability.map((statement) => (
            <div key={statement.title} className="divisions-page__stability">
              <p className="divisions-page__stability-title">
                {statement.title}
              </p>
              <p>{statement.detail}</p>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div
            className="divisions-page__filters"
            data-testid="division-type-filter"
          >
            <FilterChips
              options={filterChips.map((entry) => entry.label)}
              selected={selectedChipLabel}
              onChange={handleFilterChange}
            />
          </div>

          {companyGroups.map((group) => (
            <section
              key={group.slug}
              className="divisions-page__group"
              data-testid={`division-company-${group.slug}`}
            >
              <div className="divisions-page__group-header">
                <span className="mono-label divisions-page__group-label">
                  {group.name}
                </span>
                <div className="divisions-page__group-rule" />
                <span className="mono-label divisions-page__group-count">
                  {group.items.length}
                </span>
              </div>

              <div className="divisions-page__rows">
                {group.items.map((signal) => (
                  <SignalAccordionRow
                    key={signal.id}
                    signal={signal}
                    expanded={expandedId === signal.id}
                    onToggle={() => handleToggle(signal.id)}
                  />
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  );
}

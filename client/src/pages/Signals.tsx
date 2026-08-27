import { useMemo, useState, type CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ListResponse, Signal, SignalType } from "../api/types";
import { SignalAccordionRow } from "../components/SignalAccordionRow";
import { FilterChips } from "../components/primitives/FilterChips";
import { SIGNAL_TYPE_ORDER, signalHue, signalTypeLabel } from "../config/labels";
import signalsTodayFixture from "../fixtures/signals_today.json";
import "./Signals.css";

type LabeledSignal = Signal & { signal_type_label: string };

type FilterValue = "all" | SignalType;

function countByType(items: LabeledSignal[]): Partial<Record<SignalType, number>> {
  const counts: Partial<Record<SignalType, number>> = {};
  for (const signal of items) {
    counts[signal.signal_type] = (counts[signal.signal_type] ?? 0) + 1;
  }
  return counts;
}

function groupByType(
  items: LabeledSignal[],
  types: SignalType[],
): Map<SignalType, LabeledSignal[]> {
  const groups = new Map<SignalType, LabeledSignal[]>();
  for (const type of types) {
    const typeItems = items.filter((s) => s.signal_type === type);
    if (typeItems.length > 0) {
      groups.set(type, typeItems);
    }
  }
  return groups;
}

export function Signals() {
  const { data } = useQuery({
    queryKey: ["signals", "all"],
    queryFn: () => api.getSignals({}),
    initialData: signalsTodayFixture as ListResponse<LabeledSignal>,
  });

  const [selectedFilter, setSelectedFilter] = useState<FilterValue>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const typeCounts = useMemo(() => countByType(data.items), [data.items]);
  const presentTypes = SIGNAL_TYPE_ORDER.filter(
    (type) => (typeCounts[type] ?? 0) > 0,
  );

  const filterChips = useMemo(() => {
    const entries: { value: FilterValue; label: string }[] = [
      { value: "all", label: `All (${data.items.length})` },
    ];
    for (const type of presentTypes) {
      entries.push({
        value: type,
        label: `${signalTypeLabel(type)} (${typeCounts[type] ?? 0})`,
      });
    }
    return entries;
  }, [data.items.length, presentTypes, typeCounts]);

  const selectedChipLabel =
    filterChips.find((entry) => entry.value === selectedFilter)?.label ??
    filterChips[0].label;

  const filteredItems = useMemo(() => {
    if (selectedFilter === "all") {
      return data.items;
    }
    return data.items.filter((signal) => signal.signal_type === selectedFilter);
  }, [data.items, selectedFilter]);

  const visibleTypes =
    selectedFilter === "all" ? presentTypes : [selectedFilter as SignalType];

  const groups = groupByType(filteredItems, visibleTypes);

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
    <div className="signals-page">
      <header>
        <h1 className="page-heading font-display">Signals</h1>
        <p className="signals-page__intro">
          Public moves read as intent — a job posting, a pricing page, or a
          changelog points to where a competitor is investing. This room is for
          digging in on that direction, not for tracking what changed since your
          last visit.
        </p>
      </header>

      <div
        className="signals-page__filters"
        data-testid="signal-type-filter"
      >
        <FilterChips
          options={filterChips.map((entry) => entry.label)}
          selected={selectedChipLabel}
          onChange={handleFilterChange}
        />
      </div>

      {visibleTypes.map((signalType) => {
        const items = groups.get(signalType);
        if (!items || items.length === 0) {
          return null;
        }

        const groupStyle = {
          "--group-hue": signalHue(signalType),
        } as CSSProperties;

        return (
          <section
            key={signalType}
            className="signals-page__group"
            style={groupStyle}
            data-testid={`signal-group-${signalType}`}
          >
            <div
              className="signals-page__group-header"
              data-testid={`signal-group-header-${signalType}`}
            >
              <span className="mono-label signals-page__group-label">
                {signalTypeLabel(signalType)}
              </span>
              <div className="signals-page__group-rule" />
              <span className="mono-label signals-page__group-count">
                {items.length}
              </span>
            </div>

            <div className="signals-page__rows">
              {items.map((signal) => (
                <SignalAccordionRow
                  key={signal.id}
                  signal={signal}
                  expanded={expandedId === signal.id}
                  onToggle={() => handleToggle(signal.id)}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

import { useMemo, useState, type CSSProperties } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, isFixtureMode } from "../api/client";
import type { ListResponse, Signal, SignalType } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { RunNowButton } from "../components/RunNowButton";
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
  const queryClient = useQueryClient();
  const fixtureMode = isFixtureMode();
  const { data, isLoading } = useQuery({
    queryKey: ["signals", "all"],
    queryFn: () => api.getSignals({}),
    initialData: fixtureMode
      ? (signalsTodayFixture as ListResponse<LabeledSignal>)
      : undefined,
  });
  const items = useMemo<LabeledSignal[]>(
    () => (data?.items ?? []) as LabeledSignal[],
    [data],
  );

  const [selectedFilter, setSelectedFilter] = useState<FilterValue>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const handleRunThisPage = async () => {
    if (isRunning) return;
    setRunError(null);
    setIsRunning(true);
    try {
      const result = await api.runSurface("signals");
      if (result.status === "done") {
        void queryClient.invalidateQueries({ queryKey: ["signals"] });
      } else if (result.status === "failed") {
        setRunError(result.message || "The signals run could not complete.");
      }
    } catch {
      setRunError("Couldn't start the run — is the API reachable?");
    } finally {
      setIsRunning(false);
    }
  };

  const typeCounts = useMemo(() => countByType(items), [items]);
  const presentTypes = SIGNAL_TYPE_ORDER.filter(
    (type) => (typeCounts[type] ?? 0) > 0,
  );

  const filterChips = useMemo(() => {
    const entries: { value: FilterValue; label: string }[] = [
      { value: "all", label: `All (${items.length})` },
    ];
    for (const type of presentTypes) {
      entries.push({
        value: type,
        label: `${signalTypeLabel(type)} (${typeCounts[type] ?? 0})`,
      });
    }
    return entries;
  }, [items.length, presentTypes, typeCounts]);

  const selectedChipLabel =
    filterChips.find((entry) => entry.value === selectedFilter)?.label ??
    filterChips[0].label;

  const filteredItems = useMemo(() => {
    if (selectedFilter === "all") {
      return items;
    }
    return items.filter((signal) => signal.signal_type === selectedFilter);
  }, [items, selectedFilter]);

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
        <button
          type="button"
          data-testid="run-this-page"
          onClick={() => void handleRunThisPage()}
          disabled={isRunning}
          aria-busy={isRunning}
          style={{
            marginTop: "var(--sp-3)",
            padding: "var(--sp-1) var(--sp-3)",
            fontSize: "var(--fs-meta)",
            fontWeight: 500,
            color: isRunning ? "var(--ink-muted)" : "var(--accent)",
            background: isRunning ? "var(--surface-sunk)" : "var(--accent-wash)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            cursor: isRunning ? "not-allowed" : "pointer",
            opacity: isRunning ? 0.7 : 1,
          }}
        >
          {isRunning ? "Running…" : "Run this page"}
        </button>
        {runError ? (
          <p data-testid="run-error" role="alert" className="signals-page__run-error">
            {runError}
          </p>
        ) : null}
      </header>

      {items.length === 0 ? (
        isLoading ? (
          <p className="mono-label" style={{ color: "var(--ink-muted)" }}>
            Loading…
          </p>
        ) : (
          <EmptyState
            eyebrow="First run"
            title="No signals gathered yet"
            action={<RunNowButton />}
            testId="signals-empty"
          >
            <p>
              Signals are the public moves — job posts, pricing changes,
              changelog entries — that reveal where competitors are investing.
              None have been collected yet.
            </p>
            <p className="empty-state__note">
              Click <strong>Run now</strong> to gather them. This also fills the
              Today, Industry and Competitors rooms.
            </p>
          </EmptyState>
        )
      ) : (
      <>
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
      </>
      )}
    </div>
  );
}

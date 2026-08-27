import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { RunStatus, Signal, Tier, TodayBrief } from "../api/types";
import { IntelCard } from "../components/IntelCard";
import runStatusFixture from "../fixtures/run_status.json";
import todayFixture from "../fixtures/today.json";
import "./Today.css";

const GRID_BREAKPOINT = 1000;

function useGridColumns(): string {
  const [columns, setColumns] = useState(() =>
    typeof window !== "undefined" && window.innerWidth < GRID_BREAKPOINT
      ? "1"
      : "auto",
  );

  useEffect(() => {
    const handleResize = () => {
      setColumns(window.innerWidth < GRID_BREAKPOINT ? "1" : "auto");
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return columns;
}

function formatEyebrowDate(iso: string): { weekday: string; date: string } {
  const d = new Date(iso);
  return {
    weekday: d.toLocaleDateString("en-US", { weekday: "long" }),
    date: d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
  };
}

function countTiers(cards: Signal[]): Record<Tier, number> {
  const counts: Record<Tier, number> = {
    act_on_it: 0,
    worth_knowing: 0,
    background: 0,
  };
  for (const card of cards) {
    counts[card.tier] += 1;
  }
  return counts;
}

export function Today() {
  const gridColumns = useGridColumns();

  const { data } = useQuery({
    queryKey: ["today"],
    queryFn: () => api.getToday(),
    initialData: todayFixture as TodayBrief,
  });

  const { data: runStatus } = useQuery({
    queryKey: ["run-status"],
    queryFn: () => api.getRunStatus(),
    initialData: runStatusFixture as RunStatus,
  });

  const tierCounts = countTiers(data.cards);
  const runDateIso = runStatus?.finished_at ?? runStatus?.started_at;
  const eyebrow = runDateIso ? formatEyebrowDate(runDateIso) : null;
  const sourcesCount = runStatus?.sources_count;

  return (
    <div className="today-page">
      <header>
        <h1 className="page-heading">Today</h1>
      </header>

      {eyebrow ? (
        <div className="today-page__eyebrow mono-label">
          <span>{eyebrow.weekday}</span>
          <span className="today-page__eyebrow-sep" aria-hidden="true">·</span>
          <span>{eyebrow.date}</span>
          <span className="today-page__eyebrow-sep" aria-hidden="true">·</span>
          <span>Daily Brief</span>
        </div>
      ) : null}

      <section className="today-page__verdict">
        <div
          className="today-page__verdict-body"
          data-testid="today-headline"
        >
          <div className="today-page__verdict-rule" aria-hidden="true" />
          <blockquote className="today-page__verdict-text font-display">
            {data.headline}
          </blockquote>
        </div>

        <div className="today-page__tally">
          <div className="today-page__tally-item mono-label">
            <span
              className="today-page__tally-dot today-page__tally-dot--act"
              aria-hidden="true"
            />
            <span>{tierCounts.act_on_it} act on it</span>
          </div>
          <div className="today-page__tally-item mono-label">
            <span
              className="today-page__tally-dot today-page__tally-dot--worth"
              aria-hidden="true"
            />
            <span>{tierCounts.worth_knowing} worth knowing</span>
          </div>
          <div className="today-page__tally-item mono-label">
            <span
              className="today-page__tally-dot today-page__tally-dot--bg"
              aria-hidden="true"
            />
            <span>{tierCounts.background} background</span>
          </div>
          <span className="today-page__tally-meta mono-label">
            {data.cards.length} signals
            {sourcesCount != null ? ` · ${sourcesCount} sources` : ""}
          </span>
        </div>
      </section>

      <hr className="today-page__divider" />

      <div
        className="today-page__grid"
        data-testid="card-grid"
        data-columns={gridColumns}
        style={{ display: "grid" }}
      >
        {data.cards.map((signal, index) => (
          <IntelCard key={signal.id} signal={signal} rank={index + 1} />
        ))}
      </div>

      {data.industry && data.industry.length > 0 ? (
        <section className="today-page__industry" data-testid="today-industry">
          <div className="today-page__industry-head">
            <h2 className="mono-label today-page__industry-title">
              Industry radar
            </h2>
            <span className="mono-label today-page__industry-sub">
              DevSecOps moves relevant to JFrog
            </span>
          </div>
          <ul className="today-page__industry-list">
            {data.industry.map((item) => (
              <li key={item.id} className="today-page__industry-item">
                <span className="today-page__industry-type mono-label">
                  {item.signal_type.replace(/_/g, " ")}
                </span>
                <div className="today-page__industry-body">
                  <h3 className="today-page__industry-headline">
                    {item.headline}
                  </h3>
                  <p className="today-page__industry-summary">{item.summary}</p>
                  {item.why_it_matters ? (
                    <p className="today-page__industry-why">
                      <span className="today-page__industry-why-key mono-label">
                        ↳ why it matters
                      </span>
                      {item.why_it_matters}
                    </p>
                  ) : null}
                  {item.evidence[0] ? (
                    <a
                      className="today-page__industry-src mono-label"
                      href={item.evidence[0].source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.evidence[0].source_name}
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

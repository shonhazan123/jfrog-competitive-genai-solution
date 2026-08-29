import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { RunStatus, Signal, Tier, TodayBrief } from "../api/types";
import { AskCta } from "../components/AskCta";
import { RailSection } from "../components/RailSection";
import { RunPanel } from "../components/RunPanel";
import { groupIndustry, groupSignals } from "../config/railCopy";
import runStatusFixture from "../fixtures/run_status.json";
import todayFixture from "../fixtures/today.json";
import "./Today.css";

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

  const competitorGroups = groupSignals(data.cards);
  const industryGroups = data.industry ? groupIndustry(data.industry) : [];

  return (
    <div className="today-page">
      <div className="today-page__inner">
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
          <span className="today-page__verdict-mark" aria-hidden="true" />
          <blockquote
            className="today-page__verdict-text font-display"
            data-testid="today-headline"
          >
            {data.headline}
          </blockquote>
        </section>

        <div className="today-page__tally">
          <span className="today-page__tally-item mono-label">
            <span
              className="today-page__tally-dot today-page__tally-dot--act"
              aria-hidden="true"
            />
            {tierCounts.act_on_it} act on it
          </span>
          <span className="today-page__tally-item mono-label">
            <span
              className="today-page__tally-dot today-page__tally-dot--worth"
              aria-hidden="true"
            />
            {tierCounts.worth_knowing} worth knowing
          </span>
          <span className="today-page__tally-item mono-label">
            <span
              className="today-page__tally-dot today-page__tally-dot--bg"
              aria-hidden="true"
            />
            {tierCounts.background} background
          </span>
          <span className="today-page__tally-meta mono-label">
            {data.cards.length} signals
            {sourcesCount != null ? ` · ${sourcesCount} sources` : ""}
          </span>
        </div>

        <RunPanel data={runStatus} />

        <hr className="today-page__divider" />

        <RailSection
          eyebrow="Competitors · Recent Movements"
          roomName="Competitors"
          roomPath="/comparison"
          groups={competitorGroups}
          testId="rail-competitors"
        />

        {industryGroups.length > 0 ? (
          <>
            <hr className="today-page__divider" />
            <RailSection
              eyebrow="Industry · Recent News"
              roomName="Industry"
              roomPath="/industry"
              groups={industryGroups}
              testId="rail-industry"
            />
          </>
        ) : null}

        <AskCta />
      </div>
    </div>
  );
}

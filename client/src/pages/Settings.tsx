import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  CompetitorsConfig,
  CoverageMatrix as CoverageMatrixData,
  InstructionsConfig,
  ListResponse,
  Source,
  Watchlist,
} from "../api/types";
import { CompetitorEditor } from "../components/CompetitorEditor";
import { CoverageMatrix } from "../components/CoverageMatrix";
import { InstructionsEditor } from "../components/InstructionsEditor";
import { Panel } from "../components/primitives/Panel";
import { SourceTable } from "../components/SourceTable";
import { WatchlistEditor } from "../components/WatchlistEditor";
import competitorsFixture from "../fixtures/config_competitors.json";
import instructionsFixture from "../fixtures/config_instructions.json";
import coverageFixture from "../fixtures/coverage_matrix.json";
import sourcesFixture from "../fixtures/sources.json";
import watchlistFixture from "../fixtures/watchlist.json";

export function Settings() {
  const { data: coverage } = useQuery({
    queryKey: ["coverage"],
    queryFn: () => api.getCoverage(),
    initialData: coverageFixture as CoverageMatrixData,
  });

  const { data: sources } = useQuery({
    queryKey: ["sources"],
    queryFn: () => api.getSources({ include_excluded: true }),
    initialData: sourcesFixture as ListResponse<Source>,
  });

  const { data: competitors } = useQuery({
    queryKey: ["competitors"],
    queryFn: () => api.getCompetitors(),
    initialData: competitorsFixture as CompetitorsConfig,
  });

  const { data: instructions } = useQuery({
    queryKey: ["instructions"],
    queryFn: () => api.getInstructions(),
    initialData: instructionsFixture as InstructionsConfig,
  });

  const { data: watchlist } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api.getWatchlist(),
    initialData: watchlistFixture as Watchlist,
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-5)",
        maxWidth: "var(--content-max)",
      }}
    >
      <header>
        <h1 className="page-heading">Settings</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          Sources, coverage gaps, competitors, analyst instructions, and
          watchlist terms.
        </p>
      </header>

      <Panel title="Coverage matrix">
        <CoverageMatrix data={coverage} />
      </Panel>

      <Panel title="Sources">
        <SourceTable sources={sources.items} />
      </Panel>

      <Panel title="Competitors">
        <CompetitorEditor config={competitors} />
      </Panel>

      <Panel title="Analyst instructions">
        <InstructionsEditor config={instructions} />
      </Panel>

      <Panel title="Watchlist">
        <WatchlistEditor watchlist={watchlist} />
      </Panel>
    </div>
  );
}

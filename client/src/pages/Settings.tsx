import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  CoverageMatrix as CoverageMatrixData,
  ListResponse,
  MaterialityConfig,
  Source,
  Watchlist,
} from "../api/types";
import { CoverageMatrix } from "../components/CoverageMatrix";
import { Panel } from "../components/primitives/Panel";
import { SourceTable } from "../components/SourceTable";
import { WatchlistEditor } from "../components/WatchlistEditor";
import { WeightEditor } from "../components/WeightEditor";
import coverageFixture from "../fixtures/coverage_matrix.json";
import materialityFixture from "../fixtures/materiality_weights.json";
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

  const { data: materiality } = useQuery({
    queryKey: ["materiality"],
    queryFn: () => api.getMateriality(),
    initialData: materialityFixture as MaterialityConfig,
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
          Sources, coverage gaps, materiality weights, and watchlist terms.
        </p>
      </header>

      <Panel title="Coverage matrix">
        <CoverageMatrix data={coverage} />
      </Panel>

      <Panel title="Sources">
        <SourceTable sources={sources.items} />
      </Panel>

      <Panel title="Materiality weights">
        <WeightEditor config={materiality} />
      </Panel>

      <Panel title="Watchlist">
        <WatchlistEditor watchlist={watchlist} />
      </Panel>
    </div>
  );
}

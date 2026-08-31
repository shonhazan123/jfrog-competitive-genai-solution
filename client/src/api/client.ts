import askTranscriptFixture from "../fixtures/ask_transcript.json";
import claimsAboutJfrogFixture from "../fixtures/claims_about_jfrog.json";
import claimsHistoryTimelineFixture from "../fixtures/claims_history_timeline.json";
import comparisonMatrixFixture from "../fixtures/comparison_matrix.json";
import comparisonSonatypeFixture from "../fixtures/comparison_sonatype.json";
import configCompetitorsFixture from "../fixtures/config_competitors.json";
import configInstructionsFixture from "../fixtures/config_instructions.json";
import coverageMatrixFixture from "../fixtures/coverage_matrix.json";
import digestExecWeeklyFixture from "../fixtures/digest_exec_weekly.json";
import emailPreviewFixture from "../fixtures/email_preview.json";
import industryFeedFixture from "../fixtures/industry_feed.json";
import industryThemeDetailFixture from "../fixtures/industry_theme_detail.json";
import industryThemesFixture from "../fixtures/industry_themes.json";
import kitsFixture from "../fixtures/kits.json";
import materialityWeightsFixture from "../fixtures/materiality_weights.json";
import runStatusFixture from "../fixtures/run_status.json";
import signalsProductFixture from "../fixtures/signals_product.json";
import signalsSalesFixture from "../fixtures/signals_sales.json";
import signalsTodayFixture from "../fixtures/signals_today.json";
import todayFixture from "../fixtures/today.json";
import sinceLastVisitFixture from "../fixtures/since_last_visit.json";
import sourcesFixture from "../fixtures/sources.json";
import watchlistFixture from "../fixtures/watchlist.json";

import { RUN_POLL_INTERVAL_MS } from "../config/runPolling";
import * as paths from "./endpoints";
import type {
  ArchiveTimeline,
  AskRequest,
  AskResponse,
  ChatRequest,
  ChatResponse,
  ChatStreamHandlers,
  ChatStreamEvent,
  BattlecardRow,
  Claim,
  DemoDigestResult,
  ComparisonMatrix,
  CompetitorsConfig,
  CoverageMatrix,
  InstructionsConfig,
  EmailPreview,
  ExecWeekly,
  GetClaimsParams,
  GetIndustryParams,
  GetSignalsParams,
  IndustryItem,
  IndustryTheme,
  IndustryThemeDetail,
  Kit,
  ListResponse,
  MaterialityConfig,
  PatchSourceRequest,
  Persona,
  PutMaterialityRequest,
  PutWatchlistRequest,
  ActiveBatch,
  RunProgress,
  RunStatus,
  StartAllResponse,
  SurfaceProgress,
  Signal,
  SinceLastVisit,
  Source,
  TodayBrief,
  Watchlist,
} from "./types";

export type ApiMode = "fixture" | "live";

const DEFAULT_BASE = "http://localhost:8000";

let runtimeMode: ApiMode | null = null;

export function setMode(mode: ApiMode): void {
  runtimeMode = mode;
}

function getMode(): ApiMode {
  const envMode = import.meta.env.VITE_API_MODE;
  if (runtimeMode) {
    return runtimeMode;
  }
  if (envMode === "live" || envMode === "fixture") {
    return envMode;
  }
  return "fixture";
}

// Exposed so pages can seed React Query with fixture `initialData` only in
// fixture mode. In live mode we start with no seed so an empty database renders
// the instructive first-run onboarding instead of flashing demo content.
export function isFixtureMode(): boolean {
  return getMode() === "fixture";
}

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE ?? DEFAULT_BASE;
}

function selectSignalsFixture(params?: GetSignalsParams): ListResponse<Signal> {
  if (params?.persona === "product") {
    return signalsProductFixture as ListResponse<Signal>;
  }
  if (params?.persona === "sales") {
    return signalsSalesFixture as ListResponse<Signal>;
  }
  if (params?.view === "today") {
    return signalsTodayFixture as ListResponse<Signal>;
  }
  return signalsTodayFixture as ListResponse<Signal>;
}

function selectEmailPreviewFixture(params?: {
  persona?: Persona;
  date?: string | null;
}): EmailPreview {
  const persona = params?.persona ?? "sales";
  const previews = emailPreviewFixture as Record<Persona, EmailPreview>;
  return previews[persona];
}

function selectAskFixture(body: AskRequest): AskResponse {
  const exchanges = (askTranscriptFixture as { exchanges: AskResponse[] }).exchanges;
  if (body.question) {
    const match = exchanges.find((exchange) => exchange.question === body.question);
    if (match) {
      return match;
    }
  }
  return exchanges[0];
}

function selectChatFixture(body: ChatRequest): ChatResponse {
  const exchange = selectAskFixture({ question: body.message });
  return {
    conversation_id: body.conversation_id ?? null,
    answer: exchange.answer,
    sources: exchange.evidence,
    grounded: exchange.grounded,
    plan: {
      expanded_query: exchange.question,
      steps: [
        {
          tool: "retrieve",
          query: exchange.question,
          preset: "ask_ledger",
          filters: { entity: null, signal_type: null },
          reason: "fixture",
        },
      ],
    },
    reason: exchange.refusal_reason,
    nearby_evidence: exchange.nearby_evidence,
  };
}

const FIXTURE_RUN_ID = "fixture-run";

const FIXTURE_RUN_PROGRESS: RunProgress = {
  run_id: FIXTURE_RUN_ID,
  status: "done",
  stage_label: "Done",
  progress: { current: 5, total: 5 },
  new_items: 0,
  message: "",
};

const FIXTURE_START_ALL: StartAllResponse = {
  batch_id: "fixture-batch",
  run_ids: { industry: "industry-run", signals: "signals-run", comparison: "comparison-run" },
};

const FIXTURE_SURFACE_PROGRESS: SurfaceProgress = {
  run_id: FIXTURE_RUN_ID,
  status: "done",
  surface: null,
  step_label: "Done",
  step_detail: null,
  stage_label: "Done",
  progress: { current: 5, total: 5 },
  new_items: 0,
  message: "",
};

function selectSourceFixture(sourceId: string): Source {
  const sources = (sourcesFixture as ListResponse<Source>).items;
  return sources.find((source) => source.id === sourceId) ?? sources[0];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const response = await fetch(url, init ?? {});
  const body = await response.json();
  if (!response.ok) {
    const errorBody = body as { error?: { message?: string } };
    if (errorBody.error?.message) {
      throw new Error(errorBody.error.message);
    }
    throw new Error(response.statusText);
  }
  return body as T;
}

function fixtureOrLive<T>(
  fixture: T,
  path: string,
  init?: RequestInit,
): Promise<T> {
  if (getMode() === "fixture") {
    return Promise.resolve(fixture);
  }
  return request<T>(path, init);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export type SurfaceRunKind = "industry" | "signals" | "comparison";

async function pollRunToCompletion(runId: string): Promise<RunProgress> {
  while (true) {
    const progress = await request<RunProgress>(paths.runPath(runId));
    if (progress.status === "done" || progress.status === "failed") {
      return progress;
    }
    await sleep(RUN_POLL_INTERVAL_MS);
  }
}

async function runSurfaceLive(kind: SurfaceRunKind): Promise<RunProgress> {
  const { run_id } = await request<{ run_id: string }>(paths.runsPath(), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ kind }),
  });
  return pollRunToCompletion(run_id);
}

async function runSurface(kind: SurfaceRunKind): Promise<RunProgress> {
  if (getMode() === "fixture") {
    const { run_id } = await Promise.resolve({ run_id: FIXTURE_RUN_ID });
    return { ...FIXTURE_RUN_PROGRESS, run_id };
  }
  return runSurfaceLive(kind);
}

export const FIXTURES = {
  getRunStatus: runStatusFixture,
  getSinceLastVisit: sinceLastVisitFixture,
  getSignals: signalsSalesFixture,
  getComparison: comparisonSonatypeFixture,
  getComparisonMatrix: comparisonMatrixFixture,
  getClaims: claimsAboutJfrogFixture,
  getClaimHistory: claimsHistoryTimelineFixture,
  getIndustry: industryFeedFixture,
  getThemes: industryThemesFixture,
  getThemeDetail: industryThemeDetailFixture,
  postAsk: (askTranscriptFixture as { exchanges: AskResponse[] }).exchanges[0],
  postChat: selectChatFixture({ message: "", history: [] }),
  postChatStream: selectChatFixture({ message: "", history: [] }),
  getSources: sourcesFixture,
  patchSource: (sourcesFixture as ListResponse<Source>).items[0],
  getMateriality: materialityWeightsFixture,
  putMateriality: materialityWeightsFixture,
  getWatchlist: watchlistFixture,
  putWatchlist: watchlistFixture,
  getInstructions: configInstructionsFixture,
  putInstructions: configInstructionsFixture,
  getCompetitors: configCompetitorsFixture,
  putCompetitors: configCompetitorsFixture,
  getCoverage: coverageMatrixFixture,
  getEmailPreview: (emailPreviewFixture as Record<Persona, EmailPreview>).sales,
  getExecWeekly: digestExecWeeklyFixture,
  getKits: kitsFixture,
  getToday: todayFixture,
  startRun: { run_id: FIXTURE_RUN_ID },
  getRun: FIXTURE_RUN_PROGRESS,
  runSurface: FIXTURE_RUN_PROGRESS,
  startAllRuns: FIXTURE_START_ALL,
  getRunProgress: FIXTURE_SURFACE_PROGRESS,
  getActiveBatch: { batch_id: null, runs: [] },
  sendDemoDigest: {
    status: "sent",
    recipient: "you@example.com",
    item_count: 3,
    security_count: 3,
  },
} as const;

export const api = {
  getRunStatus(): Promise<RunStatus> {
    return fixtureOrLive(
      runStatusFixture as RunStatus,
      paths.runsLatestPath(),
    );
  },

  getSinceLastVisit(params?: { actor?: string }): Promise<SinceLastVisit> {
    return fixtureOrLive(
      sinceLastVisitFixture as SinceLastVisit,
      paths.sinceLastVisitPath(params),
    );
  },

  getSignals(params?: GetSignalsParams): Promise<ListResponse<Signal>> {
    return fixtureOrLive(
      selectSignalsFixture(params),
      paths.signalsPath(params),
    );
  },

  getComparison(params?: {
    competitor?: string;
    changed_within_days?: number | null;
  }): Promise<ListResponse<BattlecardRow>> {
    return fixtureOrLive(
      comparisonSonatypeFixture as ListResponse<BattlecardRow>,
      paths.comparisonPath(params),
    );
  },

  getComparisonMatrix(): Promise<ComparisonMatrix> {
    return fixtureOrLive(
      comparisonMatrixFixture as ComparisonMatrix,
      "/comparison/matrix",
    );
  },

  getClaims(params?: GetClaimsParams): Promise<ListResponse<Claim>> {
    return fixtureOrLive(
      claimsAboutJfrogFixture as ListResponse<Claim>,
      paths.claimsPath(params),
    );
  },

  getClaimHistory(sourceId: string): Promise<ArchiveTimeline> {
    return fixtureOrLive(
      claimsHistoryTimelineFixture as ArchiveTimeline,
      paths.claimHistoryPath(sourceId),
    );
  },

  getIndustry(
    params?: GetIndustryParams,
  ): Promise<ListResponse<IndustryItem>> {
    return fixtureOrLive(
      industryFeedFixture as ListResponse<IndustryItem>,
      paths.industryPath(params),
    );
  },

  getThemes(): Promise<IndustryTheme[]> {
    return fixtureOrLive(
      industryThemesFixture as IndustryTheme[],
      "/industry/themes",
    );
  },

  getThemeDetail(key: string): Promise<IndustryThemeDetail> {
    return fixtureOrLive(
      industryThemeDetailFixture as IndustryThemeDetail,
      `/industry/themes/${encodeURIComponent(key)}`,
    );
  },

  postAsk(body: AskRequest): Promise<AskResponse> {
    return fixtureOrLive(
      selectAskFixture(body),
      paths.askPath(),
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  },

  postChat(body: ChatRequest): Promise<ChatResponse> {
    return fixtureOrLive(
      selectChatFixture(body),
      paths.chatPath(),
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  },

  async postChatStream(
    body: ChatRequest,
    handlers: ChatStreamHandlers,
  ): Promise<void> {
    if (getMode() === "fixture") {
      const fx = selectChatFixture(body);
      handlers.onPlan?.({
        type: "plan",
        expanded_query: fx.plan.expanded_query ?? body.message,
        steps: fx.plan.steps?.length ?? 0,
      });
      for (const word of fx.answer.split(/(\s+)/)) {
        if (word) handlers.onToken?.(word);
      }
      handlers.onDone?.({
        type: "done",
        grounded: fx.grounded,
        answer: fx.answer,
        sources: fx.sources,
        reason: fx.reason,
        nearby_evidence: fx.nearby_evidence,
        conversation_id: fx.conversation_id,
      });
      return;
    }

    const response = await fetch(`${getBaseUrl()}${paths.chatStreamPath()}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok || !response.body) {
      throw new Error(response.statusText || "chat stream failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    const dispatch = (event: ChatStreamEvent) => {
      if (event.type === "plan") handlers.onPlan?.(event);
      else if (event.type === "token") handlers.onToken?.(event.text);
      else if (event.type === "done") handlers.onDone?.(event);
    };

    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const dataLine = frame
          .split("\n")
          .find((line) => line.startsWith("data:"));
        if (dataLine) {
          const payload = dataLine.slice(5).trim();
          if (payload) dispatch(JSON.parse(payload) as ChatStreamEvent);
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
  },

  getSources(params?: {
    entity?: string | null;
    include_excluded?: boolean;
  }): Promise<ListResponse<Source>> {
    return fixtureOrLive(
      sourcesFixture as ListResponse<Source>,
      paths.sourcesPath(params),
    );
  },

  patchSource(
    sourceId: string,
    body: PatchSourceRequest,
  ): Promise<Source> {
    return fixtureOrLive(
      selectSourceFixture(sourceId),
      paths.sourcePath(sourceId),
      {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  },

  getMateriality(): Promise<MaterialityConfig> {
    return fixtureOrLive(
      materialityWeightsFixture as MaterialityConfig,
      paths.materialityPath(),
    );
  },

  putMateriality(body: PutMaterialityRequest): Promise<MaterialityConfig> {
    return fixtureOrLive(
      materialityWeightsFixture as MaterialityConfig,
      paths.materialityPath(),
      {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  },

  getWatchlist(): Promise<Watchlist> {
    return fixtureOrLive(
      watchlistFixture as Watchlist,
      paths.watchlistPath(),
    );
  },

  putWatchlist(body: PutWatchlistRequest): Promise<Watchlist> {
    return fixtureOrLive(
      watchlistFixture as Watchlist,
      paths.watchlistPath(),
      {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  },

  getInstructions(): Promise<InstructionsConfig> {
    return fixtureOrLive(
      configInstructionsFixture as InstructionsConfig,
      "/config/instructions",
    );
  },

  putInstructions(
    instructions: string[],
    actor?: string,
  ): Promise<InstructionsConfig> {
    return fixtureOrLive(
      configInstructionsFixture as InstructionsConfig,
      "/config/instructions",
      {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ instructions, actor }),
      },
    );
  },

  getCompetitors(): Promise<CompetitorsConfig> {
    return fixtureOrLive(
      configCompetitorsFixture as CompetitorsConfig,
      "/config/competitors",
    );
  },

  putCompetitors(
    competitors: CompetitorsConfig["competitors"],
    actor?: string,
  ): Promise<CompetitorsConfig> {
    return fixtureOrLive(
      configCompetitorsFixture as CompetitorsConfig,
      "/config/competitors",
      {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ competitors, actor }),
      },
    );
  },

  getCoverage(): Promise<CoverageMatrix> {
    return fixtureOrLive(
      coverageMatrixFixture as CoverageMatrix,
      paths.coveragePath(),
    );
  },

  getEmailPreview(params?: {
    persona?: Persona;
    date?: string | null;
  }): Promise<EmailPreview> {
    return fixtureOrLive(
      selectEmailPreviewFixture(params),
      paths.emailPreviewPath(params),
    );
  },

  getExecWeekly(params?: { week_of?: string | null }): Promise<ExecWeekly> {
    return fixtureOrLive(
      digestExecWeeklyFixture as ExecWeekly,
      paths.execWeeklyPath(params),
    );
  },

  getKits(): Promise<Kit[]> {
    return fixtureOrLive(
      kitsFixture as Kit[],
      paths.kitsPath(),
    ).then((data) =>
      Array.isArray(data) ? data : (data as ListResponse<Kit>).items,
    );
  },

  getToday(): Promise<TodayBrief> {
    return fixtureOrLive(
      todayFixture as TodayBrief,
      "/today",
    );
  },

  startRun(kind?: string): Promise<{ run_id: string }> {
    return fixtureOrLive(
      { run_id: FIXTURE_RUN_ID },
      paths.runsPath(),
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ kind: kind ?? "manual" }),
      },
    );
  },

  getRun(runId: string): Promise<RunProgress> {
    return fixtureOrLive(
      { ...FIXTURE_RUN_PROGRESS, run_id: runId },
      paths.runPath(runId),
    );
  },

  startAllRuns(): Promise<StartAllResponse> {
    return fixtureOrLive(FIXTURE_START_ALL, paths.runsAllPath(), {
      method: "POST",
      headers: { "content-type": "application/json" },
    });
  },

  getRunProgress(runId: string): Promise<SurfaceProgress> {
    return fixtureOrLive(
      { ...FIXTURE_SURFACE_PROGRESS, run_id: runId },
      paths.runPath(runId),
    );
  },

  getActiveBatch(): Promise<ActiveBatch> {
    return fixtureOrLive({ batch_id: null, runs: [] }, paths.runsActivePath());
  },

  sendDemoDigest(toEmail: string): Promise<DemoDigestResult> {
    return fixtureOrLive(
      { status: "sent", recipient: toEmail, item_count: 3, security_count: 3 },
      paths.sendDemoDigestPath(),
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ to_email: toEmail }),
      },
    );
  },

  runSurface,
};

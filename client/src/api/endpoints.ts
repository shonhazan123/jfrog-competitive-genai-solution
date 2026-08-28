import type {
  GetClaimsParams,
  GetIndustryParams,
  GetSignalsParams,
  Persona,
} from "./types";

type QueryValue = string | number | boolean | null | undefined;

function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined) {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function runsLatestPath(): string {
  return "/runs/latest";
}

export function runsPath(): string {
  return "/runs";
}

export function runPath(runId: string): string {
  return `/runs/${encodeURIComponent(runId)}`;
}

export function sinceLastVisitPath(params?: { actor?: string }): string {
  return `/activity/since-last-visit${buildQuery({ actor: params?.actor })}`;
}

export function signalsPath(params?: GetSignalsParams): string {
  return `/signals${buildQuery({
    persona: params?.persona,
    entity: params?.entity,
    signal_type: params?.signal_type,
    view: params?.view,
    since: params?.since,
    until: params?.until,
    include_interrupts: params?.include_interrupts,
    limit: params?.limit,
    cursor: params?.cursor,
  })}`;
}

export function signalPath(
  signalId: string,
  params?: { persona?: Persona | null },
): string {
  return `/signals/${encodeURIComponent(signalId)}${buildQuery({
    persona: params?.persona,
  })}`;
}

export function signalActionsPath(signalId: string): string {
  return `/signals/${encodeURIComponent(signalId)}/actions`;
}

export function comparisonPath(params?: {
  competitor?: string;
  changed_within_days?: number | null;
}): string {
  return `/comparison${buildQuery({
    competitor: params?.competitor,
    changed_within_days: params?.changed_within_days,
  })}`;
}

export function claimsPath(params?: GetClaimsParams): string {
  return `/claims${buildQuery({
    subject: params?.subject,
    asserter: params?.asserter,
    claim_type: params?.claim_type,
    include_history: params?.include_history,
  })}`;
}

export function claimHistoryPath(sourceId: string): string {
  return `/claims/history/${encodeURIComponent(sourceId)}`;
}

export function industryPath(params?: GetIndustryParams): string {
  return `/industry${buildQuery({
    signal_type: params?.signal_type,
    standard: params?.standard,
    limit: params?.limit,
    cursor: params?.cursor,
  })}`;
}

export function askPath(): string {
  return "/ask";
}

export function chatPath(): string {
  return "/chat";
}

export function sourcesPath(params?: {
  entity?: string | null;
  include_excluded?: boolean;
}): string {
  return `/sources${buildQuery({
    entity: params?.entity,
    include_excluded: params?.include_excluded,
  })}`;
}

export function sourcePath(sourceId: string): string {
  return `/sources/${encodeURIComponent(sourceId)}`;
}

export function materialityPath(): string {
  return "/config/materiality";
}

export function watchlistPath(): string {
  return "/config/watchlist";
}

export function coveragePath(): string {
  return "/coverage";
}

export function emailPreviewPath(params?: {
  persona?: Persona;
  date?: string | null;
}): string {
  return `/email/preview${buildQuery({
    persona: params?.persona,
    date: params?.date,
  })}`;
}

export function execWeeklyPath(params?: { week_of?: string | null }): string {
  return `/digests/exec/weekly${buildQuery({ week_of: params?.week_of })}`;
}

export function kitsPath(): string {
  return "/kits";
}

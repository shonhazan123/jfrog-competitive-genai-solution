/** Types transcribed from docs/API_CONTRACT.md */

export type SignalType =
  | "product_capability"
  | "positioning_messaging"
  | "pricing_packaging"
  | "security_trust"
  | "corporate_financial"
  | "partnership_ecosystem"
  | "customer_evidence"
  | "market_regulatory"
  | "talent_org";

export type Persona = "sales" | "product" | "exec";

export type Tier = "act_on_it" | "worth_knowing" | "background";

export type ReliabilityGrade = "A" | "B" | "C" | "D" | "E" | "F";

export type CredibilityScore = 1 | 2 | 3 | 4 | 5 | 6;

export type ChangeKind = "new" | "substantive" | "cosmetic" | "removed";

export type CollectionMode = "feed" | "snapshot" | "api";

export type SourceKind = "atom" | "rss" | "html_page" | "api" | "sitemap";

export type ClaimType = "capability" | "pricing" | "positioning" | "security";

export type AnalystAction = "confirm" | "reject" | "edit" | "suppress";

export type Handling = "caution";

export type Provenance = "live" | "archive";

export interface Evidence {
  quote: string;
  source_url: string;
  source_name: string;
  captured_at: string;
  reliability_grade: ReliabilityGrade;
  credibility_score: CredibilityScore;
  is_primary: boolean;
}

export interface ScoreBreakdown {
  total: number;
  parts: [string, number][];
}

export interface EntityRef {
  slug: string;
  name: string;
  tier: number | null;
}

export interface Change {
  dimension: string;
  kind: ChangeKind;
  was: string;
  now: string;
}

export interface TraceStep {
  n: number;
  node: string;
  status: "ok" | "fail" | "skipped";
  detail: string;
}

export interface Signal {
  id: string;
  entity: EntityRef;
  signal_type: SignalType;
  signal_flavour: "self" | "cross" | null;
  subject_entity: string | null;
  asserting_entity: string;
  mentions_jfrog: boolean;
  headline: string;
  occurred_at: string;
  persona: Persona | null;
  so_what: string;
  tier: Tier;
  tier_label: string;
  primary_stakeholder: Persona;
  why_it_matters: string;
  handling: Handling | null;
  awareness_only: boolean;
  evidence: Evidence[];
  cluster_id: string | null;
  corroboration_count: number;
  interrupt_tier: "critical" | null;
}

export interface SignalDetail extends Signal {
  trace: TraceStep[];
  all_persona_scores: Record<string, ScoreBreakdown>;
  bullet_classification: Record<string, unknown> | null;
}

export interface IndustryRadarItem {
  id: string;
  signal_type: string;
  headline: string;
  summary: string;
  why_it_matters: string | null;
  occurred_at: string | null;
  evidence: Evidence[];
}

export interface TodayBrief {
  headline: string;
  cards: Signal[];
  industry?: IndustryRadarItem[];
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  cursor: string | null;
}

export interface RunStatus {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  status: "ok" | "running" | "failed";
  next_run_at: string;
  live: boolean;
  sources_count: number;
  funnel: [string, number][];
  delivered_breakdown: [string, number][];
}

export interface SinceLastVisit {
  last_visit_at: string;
  new_signals: number;
  claim_changes: number;
}

export interface GetSignalsParams {
  persona?: Persona | null;
  entity?: string | null;
  signal_type?: SignalType | null;
  view?: "today" | null;
  since?: string | null;
  until?: string | null;
  include_interrupts?: boolean;
  limit?: number;
  cursor?: string | null;
}

export interface AnalystActionRequest {
  action: AnalystAction;
  actor: string;
  reason?: string | null;
  edit?: Record<string, unknown> | null;
  relevance_adjustment?: number | null;
}

export interface AnalystActionResponse {
  id: string;
  target_type: string;
  target_id: string;
  action: AnalystAction;
  actor: string;
  at: string;
}

export interface BattlecardRow {
  id: string;
  dimension: string;
  jfrog_position: string;
  competitor_position: string;
  competitor: string;
  supporting_claim_ids: string[];
  reliability_grade: ReliabilityGrade | null;
  credibility_score: CredibilityScore | null;
  evidence: Evidence[];
  no_claim_on_record: boolean;
}

export type ComparisonStance = "strong" | "moderate" | "weak" | "none";

export interface ComparisonMatrixCell {
  competitor: string;
  competitor_name: string;
  stance: ComparisonStance;
  summary: string;
  jfrog_position: string;
  evidence: Evidence[];
}

export interface ComparisonMatrixDimension {
  key: string;
  name: string;
  cells: ComparisonMatrixCell[];
}

export interface ComparisonMatrixCompetitor {
  slug: string;
  name: string;
}

export interface ComparisonMatrix {
  dimensions: ComparisonMatrixDimension[];
  competitors: ComparisonMatrixCompetitor[];
}

export interface ClaimVersion {
  changed_at: string;
  change_kind: ChangeKind;
  old_text: string | null;
  new_text: string;
  evidence_id: string | null;
}

export interface Claim {
  id: string;
  subject_entity: string;
  asserting_entity: string;
  claim_text: string;
  claim_type: ClaimType;
  capability_tags: string[];
  status: "active";
  reliability_grade: ReliabilityGrade;
  credibility_score: CredibilityScore;
  first_seen_at: string;
  last_confirmed_at: string;
  score: number;
  change: Change | null;
  evidence: Evidence[];
  versions: ClaimVersion[];
}

export interface GetClaimsParams {
  subject?: string;
  asserter?: string | null;
  claim_type?: ClaimType | null;
  include_history?: boolean;
}

export interface ArchiveVersion {
  captured_at: string;
  label: string;
  is_milestone: boolean;
  size_bytes: number | null;
  provenance: Provenance;
}

export interface ArchiveTimeline {
  source_id: string;
  source_url: string;
  method: string;
  total_versions: number;
  sampled: boolean;
  span_start: string;
  span_end: string;
  versions: ArchiveVersion[];
}

export interface IndustryItem {
  id: string;
  standard_chip: string;
  signal_type: SignalType;
  headline: string;
  body: string;
  occurred_at: string;
  evidence: Evidence;
}

export interface IndustryTheme {
  key: string;
  label: string;
  count: number;
  state_of_play: string;
  jfrog_relevance: string;
}

export interface IndustryThemeDetail {
  label: string;
  synthesis: string;
  jfrog_relevance: string;
  items: IndustryItem[];
}

export interface GetIndustryParams {
  signal_type?: SignalType | null;
  standard?: string | null;
  limit?: number;
  cursor?: string | null;
}

export interface AskEvidence {
  n: number;
  quote: string;
  source_url: string;
  source_name: string;
  captured_at: string;
  reliability_grade: ReliabilityGrade;
  credibility_score: CredibilityScore;
  citation?: Citation;
}

export interface NearbyItem {
  text: string;
}

export interface AskResponse {
  question: string;
  grounded: boolean;
  answer: string;
  evidence: AskEvidence[];
  refusal_reason: string | null;
  nearby_evidence: NearbyItem[];
}

export interface AskRequest {
  question: string;
  persona?: Persona | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  citations?: unknown[];
}

export interface ChatRequest {
  message: string;
  history: ChatTurn[];
  persona?: Persona | null;
  conversation_id?: string | null;
}

export interface ChatResponse {
  conversation_id: string | null;
  answer: string;
  sources: AskEvidence[];
  grounded: boolean;
  plan: {
    expanded_query?: string;
    steps?: {
      tool: string;
      query: string;
      preset: string;
      filters: { entity: string | null; signal_type: string | null };
      reason: string;
    }[];
  };
  reason: string | null;
  nearby_evidence: NearbyItem[];
}

export interface Source {
  id: string;
  name: string;
  entity: string;
  kind: SourceKind;
  mode: CollectionMode;
  reliability_grade: ReliabilityGrade | null;
  credibility_score: CredibilityScore | null;
  check_frequency: string | null;
  robots_allowed: boolean;
  requires_js: boolean;
  last_checked: string | null;
  enabled: boolean;
  excluded: boolean;
  exclusion_reason: string | null;
}

export interface MaterialityWeight {
  key: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  note: string;
  unit: "multiplier" | "points" | "days" | "items" | "cvss";
}

export interface MaterialityConfig {
  config_version: number;
  weights: MaterialityWeight[];
}

export interface PutMaterialityRequest {
  weights: { key: string; value: number }[];
  actor: string;
}

export interface Watchlist {
  config_version: number;
  terms: string[];
}

export interface PutWatchlistRequest {
  terms: string[];
  actor: string;
}

export interface Competitor {
  slug: string;
  name: string;
}

export interface CompetitorsConfig {
  config_version: number;
  competitors: Competitor[];
}

export interface PutCompetitorsRequest {
  competitors: Competitor[];
  actor?: string;
}

export interface InstructionsConfig {
  config_version: number;
  instructions: string[];
}

export interface PutInstructionsRequest {
  instructions: string[];
  actor?: string;
}

export interface PatchSourceRequest {
  enabled?: boolean | null;
  actor: string;
  reason?: string | null;
}

export interface CoverageCell {
  signal_type: SignalType | "positioning" | "market_regulatory";
  status: "multiple" | "one" | "gap" | "not_applicable";
  source_count: number;
}

export interface CoverageRow {
  entity: string;
  tier: number | null;
  cells: CoverageCell[];
}

export interface CoverageMatrix {
  caption: string;
  columns: string[];
  rows: CoverageRow[];
  legend: [string, string][];
}

export interface EmailDigestItem {
  signal_type: string;
  headline: string;
  so_what: string;
  flag: string | null;
  app_link: string;
}

export interface EmailPreview {
  persona: Persona;
  from_name: string;
  from_email: string;
  subject: string;
  meta: string;
  lead: string;
  items: EmailDigestItem[];
  sent_at: string;
  delivery_logged: boolean;
  footer: string;
}

export interface Trend {
  id: string;
  title: string;
  body: string;
  direction: "toward_us" | "against_us" | "lateral";
  velocity: "accelerating" | "steady" | "emerging";
  confidence_grade: ReliabilityGrade;
  confidence_note: string;
  contributing_signal_ids: string[];
}

export interface StabilityStatement {
  title: string;
  detail: string;
  entities_checked: string[];
}

export interface ExecWeekly {
  week_of: string;
  assembled_at: string;
  subject: string;
  lead: string;
  trends: Trend[];
  stability: StabilityStatement[];
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export interface Citation {
  source_name: string;
  source_url: string;
  captured_at: string;
  origin: "extracted" | "authored" | "archive";
  archived_url: string | null;
  grade: ReliabilityGrade | null;
}

export interface KitSnippet {
  headline: string;
  quote: string;
  implication: string;
  citation: Citation;
}

export interface Kit {
  key: string;
  label: string;
  question: string;
  category: string;
  order: number;
  status: "active" | "no_change";
  count: number;
  priority_label: string | null;
  snippet: KitSnippet | null;
  signal_ids: string[];
  withheld: number;
}

export interface RunProgress {
  run_id: string;
  status: "running" | "done" | "failed";
  stage_label: string;
  progress: { current: number; total: number };
  new_items: number;
  message: string;
}

import type { SurfaceProgress } from "../api/types";

export type LaneState = "running" | "done" | "empty" | "trouble";

export interface SurfaceMeta {
  name: string;
  blurb: string;
  href: string;
}

export const SURFACE_META: Record<string, SurfaceMeta> = {
  industry: { name: "Market Watch", blurb: "What's moving in the industry", href: "/industry" },
  signals: { name: "Competitor Moves", blurb: "Hiring, pricing & funding", href: "/signals" },
  comparison: { name: "Head-to-Head", blurb: "How rivals stack up vs JFrog", href: "/comparison" },
};

export function laneState(p: { status: string; new_items: number }): LaneState {
  if (p.status === "failed") return "trouble";
  if (p.status === "done") return p.new_items > 0 ? "done" : "empty";
  return "running";
}

const EXPECTED_SECONDS: Record<string, number> = {
  industry: 40,
  signals: 90,
  comparison: 120,
};

export function etaSeconds(surfaces: SurfaceProgress[]): number {
  let max = 0;
  for (const s of surfaces) {
    if (s.status !== "running") continue;
    const expected = EXPECTED_SECONDS[s.surface ?? ""] ?? 60;
    const total = s.progress?.total || 1;
    const current = s.progress?.current || 0;
    const remainingFraction = total > 0 ? Math.max(0, (total - current) / total) : 1;
    max = Math.max(max, expected * remainingFraction);
  }
  return Math.round(max);
}

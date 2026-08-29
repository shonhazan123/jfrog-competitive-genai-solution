import { useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useRunStore } from "../state/runStore";
import { SURFACE_META, etaSeconds, laneState } from "../utils/runPresentation";
import type { SurfaceProgress } from "../api/types";
import "./RunStatusCard.css";

/** Per-surface icon (accent colour is driven from CSS via data-k). */
const SURFACE_ICON: Record<string, ReactNode> = {
  industry: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2a10 10 0 0 1 0 20" />
      <path d="M12 12l6-3.5" />
    </svg>
  ),
  signals: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M4 18v-4M9 18v-8M14 18V8M19 18v-6" />
    </svg>
  ),
  comparison: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18M9 9v11" />
    </svg>
  ),
};

const CHECK = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 6L9 17l-5-5" />
  </svg>
);

function formatEta(seconds: number): string {
  if (seconds <= 0) return "almost done";
  if (seconds < 60) return `about ${seconds}s left`;
  return `about ${Math.round(seconds / 60)} min left`;
}

function Lane({ surface, showTech }: { surface: SurfaceProgress; showTech: boolean }) {
  const key = surface.surface ?? "";
  const meta = SURFACE_META[key] ?? { name: surface.surface ?? "Run", blurb: "", href: "/" };
  const state = laneState(surface);
  const total = surface.progress?.total || 1;
  const current = surface.progress?.current || 0;
  const pct = state === "running" ? Math.min(100, Math.round((current / total) * 100)) : 100;

  const glyph =
    state === "done" ? CHECK
    : state === "trouble" ? <span className="run-lane__bang">!</span>
    : (SURFACE_ICON[key] ?? null);

  return (
    <div className={`run-lane run-lane--${state}`} data-k={key} data-testid={`lane-${surface.surface}`}>
      <div className="run-lane__icon">
        {glyph}
        {state === "running" ? <span className="run-lane__spin" aria-hidden="true" /> : null}
      </div>

      <div className="run-lane__mid">
        <div className="run-lane__name">
          {meta.name}
          {meta.blurb ? <span className="run-lane__blurb"> {meta.blurb}</span> : null}
        </div>

        {state === "running" ? (
          <>
            <div className="run-lane__step">
              <span className="run-lane__step-txt">{surface.step_label}</span>
              {showTech && surface.stage_label ? (
                <span className="run-lane__tech">{surface.stage_label}</span>
              ) : null}
            </div>
            <div
              className="run-lane__bar"
              role="progressbar"
              aria-valuenow={pct}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div className="run-lane__bar-fill" style={{ width: `${pct}%` }} />
            </div>
          </>
        ) : (
          <div className="run-lane__end">
            {state === "done" ? (
              <Link className="run-lane__done" to={meta.href}>
                Open {meta.name} →
              </Link>
            ) : null}
            {state === "empty" ? (
              <span className="run-lane__empty">Nothing new worth flagging</span>
            ) : null}
            {state === "trouble" ? (
              <span className="run-lane__trouble">
                Had trouble{surface.message ? ` — ${surface.message}` : ""}
              </span>
            ) : null}
          </div>
        )}
      </div>

      <div className="run-lane__right">
        {state === "running" && surface.step_detail ? (
          <span className="run-lane__detail">{surface.step_detail}</span>
        ) : null}
        {state === "done" ? <span className="run-lane__count">{surface.new_items} new</span> : null}
      </div>
    </div>
  );
}

export function RunStatusCard() {
  const store = useRunStore();
  const [showTech, setShowTech] = useState(false);

  if (!store.active || !store.cardOpen) return null;

  const surfaces = store.surfaces;
  const resolved = surfaces.filter((s) => s.status === "done" || s.status === "failed").length;
  const overallPct = surfaces.length ? Math.round((resolved / surfaces.length) * 100) : 0;
  const eta = etaSeconds(surfaces);

  return (
    <section
      className={`run-card${store.allResolved ? " run-card--done" : ""}`}
      role="dialog"
      aria-label="Run progress"
      data-testid="run-card"
    >
      <header className="run-card__head">
        <div className="run-card__title">
          <span className="run-card__live" aria-hidden="true" />
          {store.allResolved ? "All caught up" : "Refreshing your intelligence"}
        </div>
        <span className="run-card__eta">{store.allResolved ? "done" : formatEta(eta)}</span>
        <button
          type="button"
          className="run-card__min"
          aria-label="Minimize — keeps running"
          onClick={() => store.minimize()}
        >
          –
        </button>
      </header>

      <div
        className="run-card__overall"
        role="progressbar"
        aria-valuenow={overallPct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="run-card__overall-fill" style={{ width: `${overallPct}%` }} />
      </div>

      <div className="run-card__lanes">
        {surfaces.map((s) => (
          <Lane key={s.run_id} surface={s} showTech={showTech} />
        ))}
      </div>

      <label className="run-card__toggle">
        <input
          type="checkbox"
          className="run-card__toggle-input"
          checked={showTech}
          onChange={(e) => setShowTech(e.target.checked)}
        />
        <span className="run-card__switch" aria-hidden="true" />
        <span>{showTech ? "Hide what the system is doing" : "Show what the system is doing"}</span>
      </label>
    </section>
  );
}

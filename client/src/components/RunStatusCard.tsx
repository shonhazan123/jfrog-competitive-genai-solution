import { useState } from "react";
import { Link } from "react-router-dom";
import { useRunStore } from "../state/runStore";
import { SURFACE_META, etaSeconds, laneState } from "../utils/runPresentation";
import type { SurfaceProgress } from "../api/types";
import "./RunStatusCard.css";

function formatEta(seconds: number): string {
  if (seconds <= 0) return "almost done";
  if (seconds < 60) return `about ${seconds}s left`;
  return `about ${Math.round(seconds / 60)} min left`;
}

function Lane({ surface, showTech }: { surface: SurfaceProgress; showTech: boolean }) {
  const meta =
    SURFACE_META[surface.surface ?? ""] ??
    { name: surface.surface ?? "Run", blurb: "", href: "/" };
  const state = laneState(surface);
  const total = surface.progress?.total || 1;
  const current = surface.progress?.current || 0;
  const pct = Math.min(100, Math.round((current / total) * 100));

  return (
    <div className={`run-lane run-lane--${state}`} data-testid={`lane-${surface.surface}`}>
      <div className="run-lane__head">
        <span className="run-lane__name">{meta.name}</span>
        {state === "running" && surface.step_detail ? (
          <span className="run-lane__detail">{surface.step_detail}</span>
        ) : null}
      </div>

      {state === "running" ? (
        <>
          <div className="run-lane__step">{surface.step_label}</div>
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
      ) : null}

      {state === "done" ? (
        <Link className="run-lane__done" to={meta.href}>
          Open {meta.name} →
        </Link>
      ) : null}

      {state === "empty" ? (
        <div className="run-lane__empty">Nothing new this time</div>
      ) : null}

      {state === "trouble" ? (
        <div className="run-lane__trouble">
          Had trouble{surface.message ? ` — ${surface.message}` : ""}
        </div>
      ) : null}

      {showTech ? (
        <div className="run-lane__tech">
          {surface.surface} · {surface.stage_label}
        </div>
      ) : null}
    </div>
  );
}

export function RunStatusCard() {
  const store = useRunStore();
  const [showTech, setShowTech] = useState(false);

  if (!store.active || !store.cardOpen) return null;

  const surfaces = store.surfaces;
  const resolved = surfaces.filter(
    (s) => s.status === "done" || s.status === "failed",
  ).length;
  const overallPct = surfaces.length
    ? Math.round((resolved / surfaces.length) * 100)
    : 0;
  const eta = etaSeconds(surfaces);

  return (
    <section className="run-card" role="dialog" aria-label="Run progress" data-testid="run-card">
      <header className="run-card__head">
        <span className="run-card__title">Working on your update</span>
        <span className="run-card__eta">
          {store.allResolved ? "All caught up" : formatEta(eta)}
        </span>
        <button
          type="button"
          className="run-card__min"
          aria-label="Minimize"
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
          checked={showTech}
          onChange={(e) => setShowTech(e.target.checked)}
        />
        Show what the system is doing
      </label>
    </section>
  );
}

import { useRunStore } from "../state/runStore";
import { etaSeconds } from "../utils/runPresentation";
import "./TodayRunBar.css";

function formatEta(seconds: number): string {
  if (seconds <= 0) return "almost done";
  if (seconds < 60) return `about ${seconds}s left`;
  return `about ${Math.round(seconds / 60)} min left`;
}

export function TodayRunBar() {
  const store = useRunStore();
  if (!store.active || !store.minimized) return null;

  const surfaces = store.surfaces;
  const total = surfaces.length || 3;
  const ready = surfaces.filter(
    (s) => s.status === "done" || s.status === "failed",
  ).length;
  const troubled = surfaces.filter((s) => s.status === "failed").length;
  const eta = etaSeconds(surfaces);
  const pct = total ? Math.round((ready / total) * 100) : 0;

  return (
    <button
      type="button"
      className="today-run-bar"
      data-testid="today-run-bar"
      data-done={store.allResolved || undefined}
      onClick={() => store.openCard()}
    >
      <span className="today-run-bar__dot" aria-hidden="true">
        {store.allResolved ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6L9 17l-5-5" />
          </svg>
        ) : (
          <span className="today-run-bar__spin" />
        )}
      </span>

      <span className="today-run-bar__body">
        {store.allResolved ? (
          <span className="today-run-bar__label">
            All caught up · See what's new →
            {troubled > 0 ? (
              <span className="today-run-bar__trouble"> · {troubled} had trouble</span>
            ) : null}
          </span>
        ) : (
          <span className="today-run-bar__label">
            {ready} of {total} ready · {formatEta(eta)}
          </span>
        )}
        <span className="today-run-bar__mini" aria-hidden="true">
          <span className="today-run-bar__mini-fill" style={{ width: `${pct}%` }} />
        </span>
      </span>

      <span className="today-run-bar__open">
        {store.allResolved ? "Open" : "Show status"}
      </span>
    </button>
  );
}

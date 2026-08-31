import { useRunStore } from "../state/runStore";
import "./RunPanel.css";

interface RunNowButtonProps {
  label?: string;
}

/**
 * Starts the global "gather everything" batch run (competitors + signals +
 * industry) and surfaces a plain-language error if the API can't be reached.
 * Progress itself is shown by the shared RunStatusCard, driven by the run store.
 */
export function RunNowButton({ label = "▶ Run now" }: RunNowButtonProps) {
  const store = useRunStore();
  const running = store.active && !store.allResolved;

  const handleRunNow = () => {
    if (running) return;
    store.requestStart(); // opens the email prompt; confirm/skip actually starts
  };

  return (
    <button
      type="button"
      className="run-panel__btn"
      onClick={handleRunNow}
      disabled={running}
      aria-busy={running}
    >
      {running ? "Running…" : label}
    </button>
  );
}

import { useState } from "react";
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
  const [error, setError] = useState<string | null>(null);
  const running = store.active && !store.allResolved;

  const handleRunNow = async () => {
    if (running) return;
    setError(null);
    try {
      await store.startAll();
    } catch {
      setError("Couldn't start the run — is the API reachable?");
    }
  };

  return (
    <>
      <button
        type="button"
        className="run-panel__btn"
        onClick={() => void handleRunNow()}
        disabled={running}
        aria-busy={running}
      >
        {running ? "Running…" : label}
      </button>
      {error ? (
        <span className="run-panel__error" data-testid="run-error" role="alert">
          {error}
        </span>
      ) : null}
    </>
  );
}

import { useEffect, useState } from "react";
import { useRunStore } from "../state/runStore";
import "./RunEmailPrompt.css";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/**
 * Asks for a notification email before a run starts. Confirm (valid address)
 * emails the digest when the agents finish; Skip runs without emailing. Mounted
 * once, globally, and shown while the run store has a pending start.
 */
export function RunEmailPrompt() {
  const store = useRunStore();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prefill with the remembered address each time the prompt opens.
  useEffect(() => {
    if (store.startPending) {
      setEmail(store.notifyEmail);
      setError(null);
      setBusy(false);
    }
  }, [store.startPending, store.notifyEmail]);

  useEffect(() => {
    if (!store.startPending) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) store.cancelStart();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [store, busy]);

  if (!store.startPending) return null;

  const valid = EMAIL_RE.test(email.trim());

  const run = async (starter: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await starter();
    } catch {
      setError("Couldn't start the run — is the API reachable?");
      setBusy(false);
    }
  };

  const handleConfirm = () => {
    if (!valid) return;
    void run(() => store.confirmStart(email.trim()));
  };

  return (
    <div
      className="run-prompt__backdrop"
      onClick={() => !busy && store.cancelStart()}
    >
      <section
        className="run-prompt"
        role="dialog"
        aria-modal="true"
        aria-labelledby="run-prompt-title"
        data-testid="run-email-prompt"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="run-prompt__close"
          aria-label="Close"
          onClick={() => store.cancelStart()}
          disabled={busy}
        >
          ×
        </button>

        <h2 id="run-prompt-title" className="run-prompt__title">
          Email me the digest?
        </h2>
        <p className="run-prompt__lede">
          Enter an address to get the top signals and latest security news the
          moment the run finishes — or skip and just run.
        </p>

        <form
          className="run-prompt__form"
          onSubmit={(e) => {
            e.preventDefault();
            handleConfirm();
          }}
        >
          <input
            type="email"
            className="run-prompt__input"
            placeholder="you@example.com"
            value={email}
            autoFocus
            disabled={busy}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={email.trim().length > 0 && !valid}
          />

          {error ? (
            <p className="run-prompt__error" role="alert">
              {error}
            </p>
          ) : null}

          <div className="run-prompt__actions">
            <button
              type="button"
              className="run-prompt__skip"
              onClick={() => void run(() => store.skipStart())}
              disabled={busy}
            >
              Skip for now
            </button>
            <button
              type="submit"
              className="run-prompt__confirm"
              disabled={!valid || busy}
            >
              {busy ? "Starting…" : "Confirm & run"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

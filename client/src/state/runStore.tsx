import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { DemoDigestResult, SurfaceProgress } from "../api/types";

const POLL_MS = 1500;
const STORAGE_KEY = "run.batch.v1";
const EMAIL_KEY = "run.notifyEmail.v1";

function loadEmail(): string {
  try {
    return window.localStorage.getItem(EMAIL_KEY) ?? "";
  } catch {
    return "";
  }
}

interface RunStore {
  active: boolean;
  batchId: string | null;
  surfaces: SurfaceProgress[];
  cardOpen: boolean;
  minimized: boolean;
  allResolved: boolean;
  startAll: () => Promise<void>;
  openCard: () => void;
  minimize: () => void;
  // Pre-run email prompt: requestStart opens it; confirm/skip actually start.
  startPending: boolean;
  requestStart: () => void;
  cancelStart: () => void;
  confirmStart: (email: string) => Promise<void>;
  skipStart: () => Promise<void>;
  // Demo email digest: address to notify when a run finishes, plus send state.
  notifyEmail: string;
  setNotifyEmail: (email: string) => void;
  digestSending: boolean;
  digestResult: DemoDigestResult | null;
  sendDigest: () => Promise<void>;
}

const RunContext = createContext<RunStore | null>(null);

function isResolved(p: SurfaceProgress): boolean {
  return p.status === "done" || p.status === "failed";
}

export function RunProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [batchId, setBatchId] = useState<string | null>(null);
  const [surfaces, setSurfaces] = useState<SurfaceProgress[]>([]);
  const [cardOpen, setCardOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inFlight = useRef(false);
  const invalidatedRef = useRef(false);

  const [notifyEmail, setNotifyEmailState] = useState<string>(loadEmail);
  const [digestSending, setDigestSending] = useState(false);
  const [digestResult, setDigestResult] = useState<DemoDigestResult | null>(null);
  const [startPending, setStartPending] = useState(false);
  // Kept in a ref so the completion handler can read the latest email without
  // re-creating the poll callback (which would restart the interval).
  const notifyEmailRef = useRef(notifyEmail);
  const digestSentRef = useRef(false);
  // The address to email for the CURRENT run — set by confirm/skip, kept apart
  // from the remembered notifyEmail so "Skip" means "don't email this run"
  // without forgetting the saved address.
  const activeEmailRef = useRef("");

  const active = batchId !== null;
  const allResolved = surfaces.length > 0 && surfaces.every(isResolved);

  const setNotifyEmail = useCallback((email: string) => {
    setNotifyEmailState(email);
    notifyEmailRef.current = email;
    try {
      window.localStorage.setItem(EMAIL_KEY, email);
    } catch {
      // storage unavailable (private mode) — the in-memory value still works
    }
  }, []);

  const sendDigest = useCallback(async () => {
    const email = notifyEmailRef.current.trim();
    if (!email || digestSending) return;
    setDigestSending(true);
    try {
      const result = await api.sendDemoDigest(email);
      setDigestResult(result);
    } catch (err) {
      setDigestResult({
        status: "error",
        recipient: email,
        detail: err instanceof Error ? err.message : "Couldn't send the digest.",
      });
    } finally {
      setDigestSending(false);
    }
  }, [digestSending]);

  // Latest sendDigest, callable from poll() without adding it as a dependency.
  const sendDigestRef = useRef(sendDigest);
  sendDigestRef.current = sendDigest;

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const poll = useCallback(
    async (ids: Record<string, string>) => {
      if (inFlight.current) return;
      inFlight.current = true;
      try {
        const entries = Object.entries(ids);
        const results = await Promise.all(
          entries.map(async ([surface, id]) => {
            const p = await api.getRunProgress(id);
            return { ...p, surface: p.surface ?? surface };
          }),
        );
        setSurfaces(results);
        if (results.length > 0 && results.every(isResolved)) {
          stopPolling();
          if (!invalidatedRef.current) {
            invalidatedRef.current = true;
            ["today", "signals", "run-status", "industry", "comparison"].forEach(
              (key) => void queryClient.invalidateQueries({ queryKey: [key] }),
            );
            // Run finished: email the digest if this run was armed with an
            // address. Once per batch, guarded so a late poll tick can't re-send.
            if (activeEmailRef.current.trim() && !digestSentRef.current) {
              digestSentRef.current = true;
              void sendDigestRef.current();
            }
          }
          window.localStorage.removeItem(STORAGE_KEY);
        }
      } catch {
        // keep last known state; retry next tick
      } finally {
        inFlight.current = false;
      }
    },
    [queryClient, stopPolling],
  );

  const beginPolling = useCallback(
    (ids: Record<string, string>) => {
      stopPolling();
      invalidatedRef.current = false;
      void poll(ids);
      pollRef.current = setInterval(() => void poll(ids), POLL_MS);
    },
    [poll, stopPolling],
  );

  const startAll = useCallback(async () => {
    const res = await api.startAllRuns();
    const ids = res.run_ids as unknown as Record<string, string>;
    digestSentRef.current = false;
    setDigestResult(null);
    setBatchId(res.batch_id);
    setCardOpen(true);
    setMinimized(false);
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ batch_id: res.batch_id, run_ids: ids }),
    );
    beginPolling(ids);
  }, [beginPolling]);

  const requestStart = useCallback(() => setStartPending(true), []);
  const cancelStart = useCallback(() => setStartPending(false), []);

  const confirmStart = useCallback(
    async (email: string) => {
      const clean = email.trim();
      setNotifyEmail(clean); // remember it for next time + the card field
      activeEmailRef.current = clean; // arm this run to auto-email on completion
      setStartPending(false);
      await startAll();
    },
    [setNotifyEmail, startAll],
  );

  const skipStart = useCallback(async () => {
    activeEmailRef.current = ""; // this run won't auto-email
    setStartPending(false);
    await startAll();
  }, [startAll]);

  const openCard = useCallback(() => {
    setCardOpen(true);
    setMinimized(false);
  }, []);

  const minimize = useCallback(() => {
    setMinimized(true);
    setCardOpen(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const batch = await api.getActiveBatch();
        if (cancelled || !batch.batch_id || batch.runs.length === 0) return;
        const ids: Record<string, string> = {};
        for (const r of batch.runs) {
          if (r.surface) ids[r.surface] = r.run_id;
        }
        setBatchId(batch.batch_id);
        setSurfaces(batch.runs);
        setMinimized(true);
        if (!batch.runs.every(isResolved)) beginPolling(ids);
      } catch {
        // no active batch to recover
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [beginPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const value: RunStore = {
    active,
    batchId,
    surfaces,
    cardOpen,
    minimized,
    allResolved,
    startAll,
    openCard,
    minimize,
    startPending,
    requestStart,
    cancelStart,
    confirmStart,
    skipStart,
    notifyEmail,
    setNotifyEmail,
    digestSending,
    digestResult,
    sendDigest,
  };

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRunStore(): RunStore {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRunStore must be used within RunProvider");
  return ctx;
}

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
import type { SurfaceProgress } from "../api/types";

const POLL_MS = 1500;
const STORAGE_KEY = "run.batch.v1";

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

  const active = batchId !== null;
  const allResolved = surfaces.length > 0 && surfaces.every(isResolved);

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
    setBatchId(res.batch_id);
    setCardOpen(true);
    setMinimized(false);
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ batch_id: res.batch_id, run_ids: ids }),
    );
    beginPolling(ids);
  }, [beginPolling]);

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
  };

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>;
}

export function useRunStore(): RunStore {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRunStore must be used within RunProvider");
  return ctx;
}

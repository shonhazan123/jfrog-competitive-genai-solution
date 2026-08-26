import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, test, vi } from "vitest";
import { AppRoutes } from "../app/routes";
import { api } from "../api/client";
import { queryClient } from "../api/queryClient";
import type { RunProgress } from "../api/types";

vi.mock("../config/runPolling", () => ({
  RUN_POLL_INTERVAL_MS: 10,
}));

interface RenderAppOptions {
  runStages?: string[];
  finishAfterMs?: number;
  failWith?: string;
}

function buildRunningProgress(
  runId: string,
  stageLabel: string,
  current: number,
  total: number,
): RunProgress {
  return {
    run_id: runId,
    status: "running",
    stage_label: stageLabel,
    progress: { current, total },
    new_items: 0,
    message: "",
  };
}

function renderApp(options: RenderAppOptions = {}) {
  queryClient.clear();

  const runId = "test-run";
  let pollCount = 0;
  const stages = options.runStages ?? [
    "Checking sources",
    "Reading new documents",
    "Done",
  ];
  const total = stages.length;

  vi.spyOn(api, "startRun").mockResolvedValue({ run_id: runId });
  // Keep the post-invalidation ["kits"] refetch pending so the invalidated
  // flag stays observable (fixture-mode getKits would otherwise resolve
  // synchronously and immediately clear it).
  vi.spyOn(api, "getKits").mockReturnValue(new Promise<never>(() => {}));
  vi.spyOn(api, "getRun").mockImplementation(async () => {
    pollCount += 1;

    if (options.failWith) {
      return {
        run_id: runId,
        status: "failed",
        stage_label: "Failed",
        progress: { current: 0, total },
        new_items: 0,
        message: options.failWith,
      };
    }

    if (options.finishAfterMs !== undefined) {
      if (pollCount === 1) {
        return buildRunningProgress(runId, "Checking sources", 1, total);
      }
      return {
        run_id: runId,
        status: "done",
        stage_label: "Done",
        progress: { current: total, total },
        new_items: 11,
        message: "",
      };
    }

    const stageIndex = Math.min(pollCount - 1, stages.length - 1);
    return buildRunningProgress(
      runId,
      stages[stageIndex],
      stageIndex + 1,
      total,
    );
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.useRealTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  queryClient.clear();
});

test("Run now starts a run and does not block navigation", async () => {
  const user = userEvent.setup();
  renderApp({ runStages: ["Checking sources", "Reading new documents"] });

  await user.click(screen.getByRole("button", { name: /run now/i }));
  expect(screen.getByTestId("run-progress")).toBeVisible();

  await user.click(screen.getByRole("link", { name: /comparison/i }));
  expect(screen.getByTestId("run-progress")).toBeVisible();
});

test("stages advance with human labels and a counter", async () => {
  const user = userEvent.setup();
  renderApp({ runStages: ["Checking sources", "Reading new documents"] });

  await user.click(screen.getByRole("button", { name: /run now/i }));
  expect(await screen.findByText(/checking sources/i)).toBeVisible();
  expect(await screen.findByText(/reading new documents/i)).toBeVisible();
});

test("completion refreshes the current screen in place", async () => {
  const user = userEvent.setup();
  renderApp({ finishAfterMs: 10 });

  await user.click(screen.getByRole("button", { name: /run now/i }));
  expect(await screen.findByText(/new items/i)).toBeVisible();
  expect(queryClient.getQueryState(["kits"])?.isInvalidated).toBe(true);
});

test("a failure states what happened in plain language", async () => {
  const user = userEvent.setup();
  renderApp({ failWith: "Could not reach 2 of 23 sources" });

  await user.click(screen.getByRole("button", { name: /run now/i }));
  expect(
    await screen.findByText(/could not reach 2 of 23 sources/i),
  ).toBeVisible();
});

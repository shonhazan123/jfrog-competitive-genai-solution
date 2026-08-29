import { render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { expect, test, vi } from "vitest";
import { laneState } from "../utils/runPresentation";
import { queryClient } from "../api/queryClient";
import { api } from "../api/client";
import { RunProvider, useRunStore } from "./runStore";

test("lane state derivation", () => {
  expect(laneState({ status: "running", new_items: 0 } as never)).toBe("running");
  expect(laneState({ status: "done", new_items: 5 } as never)).toBe("done");
  expect(laneState({ status: "done", new_items: 0 } as never)).toBe("empty");
  expect(laneState({ status: "failed", new_items: 0 } as never)).toBe("trouble");
});

function Probe() {
  const store = useRunStore();
  return (
    <div
      data-testid="probe"
      data-active={String(store.active)}
      data-count={store.surfaces.length}
    />
  );
}

test("recovers an in-flight batch on mount", async () => {
  vi.spyOn(api, "getActiveBatch").mockResolvedValue({
    batch_id: "b1",
    runs: [
      { run_id: "i", status: "running", surface: "industry", step_label: "…", step_detail: null, stage_label: "", progress: { current: 0, total: 4 }, new_items: 0, message: "" },
      { run_id: "s", status: "running", surface: "signals", step_label: "…", step_detail: null, stage_label: "", progress: { current: 0, total: 3 }, new_items: 0, message: "" },
      { run_id: "c", status: "running", surface: "comparison", step_label: "…", step_detail: null, stage_label: "", progress: { current: 0, total: 25 }, new_items: 0, message: "" },
    ],
  });
  vi.spyOn(api, "getRunProgress").mockImplementation(async (id: string) => ({
    run_id: id, status: "running", surface: null, step_label: "…", step_detail: null, stage_label: "", progress: { current: 0, total: 4 }, new_items: 0, message: "",
  }));

  render(
    <QueryClientProvider client={queryClient}>
      <RunProvider>
        <Probe />
      </RunProvider>
    </QueryClientProvider>,
  );

  await waitFor(() =>
    expect(screen.getByTestId("probe").getAttribute("data-active")).toBe("true"),
  );
  expect(screen.getByTestId("probe").getAttribute("data-count")).toBe("3");
  vi.restoreAllMocks();
});

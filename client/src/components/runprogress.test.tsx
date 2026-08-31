import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AppRoutes } from "../app/routes";
import { api } from "../api/client";
import { queryClient } from "../api/queryClient";

function renderApp() {
  queryClient.clear();
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

test("Run now fires the batch fan-out, not the legacy manual run", async () => {
  const user = userEvent.setup();
  const startAll = vi.spyOn(api, "startAllRuns").mockResolvedValue({
    batch_id: "b1",
    run_ids: { industry: "i", signals: "s", comparison: "c" },
  });
  const startRun = vi.spyOn(api, "startRun");
  vi.spyOn(api, "getActiveBatch").mockResolvedValue({ batch_id: null, runs: [] });
  vi.spyOn(api, "getRunProgress").mockResolvedValue({
    run_id: "i", status: "running", surface: "industry", step_label: "Searching the web for the latest", step_detail: null, stage_label: "Researching", progress: { current: 0, total: 3 }, new_items: 0, message: "",
  });

  renderApp();
  const strip = within(screen.getByRole("banner", { name: "Run status" }));
  await user.click(strip.getByRole("button", { name: /run now/i }));
  // Run now now opens the email prompt; skipping starts the batch.
  await user.click(await screen.findByRole("button", { name: /skip for now/i }));
  expect(startAll).toHaveBeenCalledTimes(1);
  expect(startRun).not.toHaveBeenCalled();
});

test("Run now disables the button while a batch is active", async () => {
  const user = userEvent.setup();
  vi.spyOn(api, "startAllRuns").mockResolvedValue({
    batch_id: "b1",
    run_ids: { industry: "i", signals: "s", comparison: "c" },
  });
  vi.spyOn(api, "getActiveBatch").mockResolvedValue({ batch_id: null, runs: [] });
  vi.spyOn(api, "getRunProgress").mockResolvedValue({
    run_id: "i", status: "running", surface: "industry", step_label: "…", step_detail: null, stage_label: "Researching", progress: { current: 0, total: 3 }, new_items: 0, message: "",
  });

  renderApp();
  const strip = within(screen.getByRole("banner", { name: "Run status" }));
  await user.click(strip.getByRole("button", { name: /run now/i }));
  await user.click(await screen.findByRole("button", { name: /skip for now/i }));
  expect(await strip.findByRole("button", { name: /running/i })).toBeDisabled();
});

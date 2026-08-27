import type { ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, test, vi } from "vitest";
import { api } from "../api/client";
import { queryClient } from "../api/queryClient";
import { Industry } from "./Industry";

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  queryClient.clear();
});

test("Run this page posts kind industry", async () => {
  const user = userEvent.setup();
  const runSurface = vi.spyOn(api, "runSurface").mockResolvedValue({
    run_id: "test-run",
    status: "done",
    stage_label: "Done",
    progress: { current: 1, total: 1 },
    new_items: 3,
    message: "",
  });

  renderPage(<Industry />);
  await user.click(screen.getByRole("button", { name: /run this page/i }));

  expect(runSurface).toHaveBeenCalledWith("industry");
});

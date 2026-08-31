import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import type { SurfaceProgress } from "../api/types";

const fakeSurfaces: SurfaceProgress[] = [
  { run_id: "s", status: "running", surface: "signals", step_label: "Checking hiring, pricing & funding", step_detail: "12 of 30", stage_label: "Researching", progress: { current: 12, total: 30 }, new_items: 0, message: "" },
  { run_id: "c", status: "done", surface: "comparison", step_label: "Filling in the grid", step_detail: null, stage_label: "Done", progress: { current: 25, total: 25 }, new_items: 7, message: "" },
  { run_id: "i", status: "failed", surface: "industry", step_label: "", step_detail: null, stage_label: "", progress: { current: 0, total: 4 }, new_items: 0, message: "Couldn't reach the web just now" },
];

vi.mock("../state/runStore", () => ({
  useRunStore: () => ({
    active: true,
    batchId: "b",
    surfaces: fakeSurfaces,
    cardOpen: true,
    minimized: false,
    allResolved: false,
    startAll: vi.fn(),
    openCard: vi.fn(),
    minimize: vi.fn(),
    notifyEmail: "",
    setNotifyEmail: vi.fn(),
    digestSending: false,
    digestResult: null,
    sendDigest: vi.fn(),
  }),
  RunProvider: ({ children }: { children: ReactNode }) => children,
}));

import { RunStatusCard } from "./RunStatusCard";

function renderCard() {
  return render(
    <MemoryRouter>
      <RunStatusCard />
    </MemoryRouter>,
  );
}

test("card shows a plain step label, a counter, a done link and a trouble note", () => {
  renderCard();
  expect(screen.getByText(/checking hiring, pricing & funding/i)).toBeVisible();
  expect(screen.getByText("12 of 30")).toBeVisible();
  expect(screen.getByRole("link", { name: /open head-to-head →/i })).toBeVisible();
  expect(screen.getByText(/had trouble/i)).toBeVisible();
});

test("no technical vocabulary leaks while the tech toggle is off", () => {
  renderCard();
  expect(screen.queryByText(/embedding|vector|chunk|\bindex\b|\bgate\b/i)).toBeNull();
});

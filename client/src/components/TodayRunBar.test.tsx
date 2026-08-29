import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import type { SurfaceProgress } from "../api/types";

const openCard = vi.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let storeValue: any;

vi.mock("../state/runStore", () => ({
  useRunStore: () => storeValue,
  RunProvider: ({ children }: { children: ReactNode }) => children,
}));

import { TodayRunBar } from "./TodayRunBar";

const running: SurfaceProgress[] = [
  { run_id: "i", status: "done", surface: "industry", step_label: "", step_detail: null, stage_label: "", progress: { current: 4, total: 4 }, new_items: 2, message: "" },
  { run_id: "s", status: "running", surface: "signals", step_label: "…", step_detail: null, stage_label: "", progress: { current: 1, total: 3 }, new_items: 0, message: "" },
  { run_id: "c", status: "running", surface: "comparison", step_label: "…", step_detail: null, stage_label: "", progress: { current: 0, total: 25 }, new_items: 0, message: "" },
];

test("bar hides unless active and minimized", () => {
  storeValue = { active: true, minimized: false, allResolved: false, surfaces: running, openCard };
  const { container } = render(<TodayRunBar />);
  expect(container).toBeEmptyDOMElement();
});

test("bar shows the ready count and opens the card on click", async () => {
  const user = userEvent.setup();
  storeValue = { active: true, minimized: true, allResolved: false, surfaces: running, openCard };
  render(<TodayRunBar />);
  expect(screen.getByText(/1 of 3 ready/i)).toBeVisible();
  await user.click(screen.getByTestId("today-run-bar"));
  expect(openCard).toHaveBeenCalled();
});

test("all resolved shows caught up and a trouble count", () => {
  const resolved: SurfaceProgress[] = running.map((s, idx) =>
    idx === 2 ? { ...s, status: "failed" as const } : { ...s, status: "done" as const },
  );
  storeValue = { active: true, minimized: true, allResolved: true, surfaces: resolved, openCard };
  render(<TodayRunBar />);
  expect(screen.getByText(/all caught up/i)).toBeVisible();
  expect(screen.getByText(/1 had trouble/i)).toBeVisible();
});

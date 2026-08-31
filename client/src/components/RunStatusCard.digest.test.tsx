import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import type { SurfaceProgress } from "../api/types";

const doneSurfaces: SurfaceProgress[] = [
  { run_id: "s", status: "done", surface: "signals", step_label: "Done", step_detail: null, stage_label: "Done", progress: { current: 5, total: 5 }, new_items: 3, message: "" },
];

const sendDigest = vi.fn();

vi.mock("../state/runStore", () => ({
  useRunStore: () => ({
    active: true,
    batchId: "b",
    surfaces: doneSurfaces,
    cardOpen: true,
    minimized: false,
    allResolved: true,
    startAll: vi.fn(),
    openCard: vi.fn(),
    minimize: vi.fn(),
    notifyEmail: "me@example.com",
    setNotifyEmail: vi.fn(),
    digestSending: false,
    digestResult: { status: "sent", recipient: "me@example.com", item_count: 3, security_count: 2 },
    sendDigest,
  }),
  RunProvider: ({ children }: { children: ReactNode }) => children,
}));

import { RunStatusCard } from "./RunStatusCard";

test("shows the sent confirmation and offers a re-send once the run is done", () => {
  render(
    <MemoryRouter>
      <RunStatusCard />
    </MemoryRouter>,
  );
  expect(screen.getByText(/digest sent to me@example.com/i)).toBeVisible();
  expect(screen.getByDisplayValue("me@example.com")).toBeVisible();
  expect(screen.getByRole("button", { name: /re-send/i })).toBeVisible();
});

import { render, screen, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, test, vi, beforeEach } from "vitest";

const confirmStart = vi.fn().mockResolvedValue(undefined);
const skipStart = vi.fn().mockResolvedValue(undefined);

const store = {
  startPending: true,
  notifyEmail: "",
  requestStart: vi.fn(),
  cancelStart: vi.fn(),
  confirmStart,
  skipStart,
};

vi.mock("../state/runStore", () => ({
  useRunStore: () => store,
  RunProvider: ({ children }: { children: ReactNode }) => children,
}));

import { RunEmailPrompt } from "./RunEmailPrompt";

beforeEach(() => {
  confirmStart.mockClear();
  skipStart.mockClear();
});

test("confirm is disabled until the email is valid, then confirms with it", () => {
  render(<RunEmailPrompt />);
  const confirm = screen.getByRole("button", { name: /confirm & run/i });
  expect(confirm).toBeDisabled();

  fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
    target: { value: "shon@example.com" },
  });
  expect(confirm).toBeEnabled();

  fireEvent.click(confirm);
  expect(confirmStart).toHaveBeenCalledWith("shon@example.com");
});

test("skip starts the run without an email", () => {
  render(<RunEmailPrompt />);
  fireEvent.click(screen.getByRole("button", { name: /skip for now/i }));
  expect(skipStart).toHaveBeenCalled();
  expect(confirmStart).not.toHaveBeenCalled();
});

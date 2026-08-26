import type { ReactElement } from "react";
import { render, screen, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { NAVIGATION } from "../config/navigation";
import { queryClient } from "../api/queryClient";
import { AboutUs } from "./AboutUs";
import { Trajectory } from "./Trajectory";

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("Trajectory sits immediately after Industry in the navigation", () => {
  const order = NAVIGATION.map((n) => n.path);
  expect(order[order.indexOf("/industry") + 1]).toBe("/trajectory");
});

test("Trajectory shows how a competitor's argument evolved, with dated captures", () => {
  renderPage(<Trajectory />);
  expect(screen.getAllByTestId("timeline-entry").length).toBeGreaterThanOrEqual(5);
  expect(screen.getAllByText(/2021/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/2026/).length).toBeGreaterThan(0);
});

test("every timeline entry links to the archived capture", () => {
  renderPage(<Trajectory />);
  screen.getAllByTestId("timeline-entry").forEach((entry) =>
    expect(within(entry).getByRole("link", { name: /as we captured it/i })).toBeInTheDocument());
});

test("Competitors to Us no longer carries the multi-year timeline", () => {
  renderPage(<AboutUs />);
  expect(screen.queryByTestId("timeline-entry")).toBeNull();
  expect(screen.getByRole("link", { name: /view full history/i })).toBeInTheDocument();
});

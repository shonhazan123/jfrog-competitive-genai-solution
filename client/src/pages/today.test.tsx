import type { ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { RunProvider } from "../state/runStore";
import todayFixture from "../fixtures/today.json";
import { Today } from "./Today";

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <RunProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </RunProvider>
    </QueryClientProvider>,
  );
}

test("the headline verdict banner renders", () => {
  renderPage(<Today />);
  const banner = screen.getByTestId("today-headline");
  expect(banner).toBeVisible();
  expect(banner).toHaveTextContent(todayFixture.headline);
});

test("signal cards render inside a Competitors rail", () => {
  renderPage(<Today />);
  expect(screen.getByTestId("rail-competitors")).toBeInTheDocument();
  const cards = screen.getAllByTestId("signal-card");
  expect(cards.length).toBeGreaterThan(0);
});

test("nothing on Today shows a raw score or a machine label", () => {
  renderPage(<Today />);
  expect(screen.queryByText(/^M ?\d+$/)).toBeNull();
  expect(screen.queryByText(/_/)).toBeNull();
});

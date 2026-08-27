import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import todayFixture from "../fixtures/today.json";
import { Today } from "./Today";

function renderPage(ui: JSX.Element) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("the headline verdict banner renders", () => {
  renderPage(<Today />);
  const banner = screen.getByTestId("today-headline");
  expect(banner).toBeVisible();
  expect(banner).toHaveTextContent(todayFixture.headline);
});

test("at most five signal cards render in a single column", () => {
  renderPage(<Today />);
  const cards = screen.getAllByTestId("signal-card");
  expect(cards.length).toBeGreaterThan(0);
  expect(cards.length).toBeLessThanOrEqual(5);
});

test("nothing on Today shows a raw score or a machine label", () => {
  renderPage(<Today />);
  expect(screen.queryByText(/^M ?\d+$/)).toBeNull();
  expect(screen.queryByText(/_/)).toBeNull();
});

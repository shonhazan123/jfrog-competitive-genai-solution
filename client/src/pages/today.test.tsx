import { render, screen, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { Today } from "./Today";

function renderPage(ui: JSX.Element) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("six tiles render, one per Key Intelligence Topic", () => {
  renderPage(<Today />);
  expect(screen.getAllByTestId("kit-tile")).toHaveLength(6);
});

test("each tile states its standing question", () => {
  renderPage(<Today />);
  expect(
    screen.getByText(/what will a rep hit in a live deal/i),
  ).toBeInTheDocument();
});

test("an active tile carries a snippet with quote, implication and a source link", () => {
  renderPage(<Today />);
  const tile = screen.getAllByTestId("kit-tile-active")[0];
  expect(within(tile).getByTestId("snippet-quote")).toBeVisible();
  expect(within(tile).getByTestId("snippet-implication")).toBeVisible();
  expect(
    within(tile).getByRole("link", { name: /source|live page/i }),
  ).toBeInTheDocument();
});

test("a quiet tile says so rather than appearing broken", () => {
  renderPage(<Today />);
  expect(screen.getAllByText(/no change in this run/i).length).toBeGreaterThan(0);
});

test("the highest-priority tile spans two columns", () => {
  renderPage(<Today />);
  expect(screen.getByTestId("kit-tile-lead")).toHaveClass("kit-tile--wide");
});

test("Today is a grid, not a single column", () => {
  renderPage(<Today />);
  const grid = screen.getByTestId("kit-grid");
  expect(getComputedStyle(grid).display).toBe("grid");
});

test("nothing on Today shows a raw score or a machine label", () => {
  renderPage(<Today />);
  expect(screen.queryByText(/^M ?\d+$/)).toBeNull();
  expect(screen.queryByText(/_/)).toBeNull();
});

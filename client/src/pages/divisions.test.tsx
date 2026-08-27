import type { ReactElement } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { Divisions } from "./Divisions";

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function expandFirstRow() {
  const firstRow = screen.getAllByTestId("signal-accordion-row")[0];
  return within(firstRow);
}

test("divisions group signals into per-company sections with a type filter", () => {
  renderPage(<Divisions />);
  expect(screen.getByTestId("division-type-filter")).toBeInTheDocument();
  expect(
    screen.getAllByTestId(/^division-company-/).length,
  ).toBeGreaterThan(0);
});

test("switching persona changes the intent read of the first signal", async () => {
  const user = userEvent.setup();
  renderPage(<Divisions />);

  const salesRow = expandFirstRow();
  await user.click(salesRow.getByRole("button"));
  const salesSoWhat = salesRow.getByTestId("so-what").textContent;

  await user.click(screen.getByRole("tab", { name: /product/i }));

  const productRow = expandFirstRow();
  await user.click(productRow.getByRole("button"));
  const productSoWhat = productRow.getByTestId("so-what").textContent;

  expect(productSoWhat).not.toBe(salesSoWhat);
});

test("the executive view is visibly sparser and may report stability", async () => {
  renderPage(<Divisions />);
  await userEvent.click(screen.getByRole("tab", { name: /executive/i }));
  expect(screen.getAllByTestId("trend-card").length).toBeLessThanOrEqual(5);
});

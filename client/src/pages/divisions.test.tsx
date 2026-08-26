import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { Divisions } from "./Divisions";

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("divisions switch persona and the so-what text changes with it", async () => {
  renderPage(<Divisions />);
  const sales = screen.getAllByTestId("so-what")[0].textContent;
  await userEvent.click(screen.getByRole("tab", { name: /product/i }));
  expect(screen.getAllByTestId("so-what")[0].textContent).not.toBe(sales);
});

test("the executive view is visibly sparser and may report stability", async () => {
  renderPage(<Divisions />);
  await userEvent.click(screen.getByRole("tab", { name: /executive/i }));
  expect(screen.getAllByTestId("trend-card").length).toBeLessThanOrEqual(5);
});

import type { ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { Divisions } from "./Divisions";

function setViewport(width: number) {
  window.innerWidth = width;
  window.dispatchEvent(new Event("resize"));
}

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("Divisions and Industry render as multi-column grids", () => {
  setViewport(1440);
  renderPage(<Divisions />);
  expect(getComputedStyle(screen.getByTestId("card-grid")).display).toBe("grid");
});

test("grids collapse to one column below 1000px", () => {
  setViewport(390);
  renderPage(<Divisions />);
  expect(screen.getByTestId("card-grid")).toHaveAttribute("data-columns", "1");
});

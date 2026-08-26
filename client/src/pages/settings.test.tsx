import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { Settings } from "./Settings";

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("the coverage matrix has nine columns and flags gaps", () => {
  renderPage(<Settings />);
  expect(screen.getAllByTestId("coverage-col")).toHaveLength(9);
  expect(screen.getAllByTestId("coverage-gap").length).toBeGreaterThan(0);
});

test("excluded sources state their reason rather than being hidden", () => {
  renderPage(<Settings />);
  expect(screen.getByText(/blocked by robots\.txt/i)).toBeInTheDocument();
  expect(screen.getByText(/terms of service/i)).toBeInTheDocument();
});

test("the coverage matrix explains what it is for", () => {
  renderPage(<Settings />);
  expect(screen.getByText(/what are we blind to/i)).toBeInTheDocument();
});

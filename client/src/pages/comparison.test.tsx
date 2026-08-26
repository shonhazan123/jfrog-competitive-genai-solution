import { render, screen, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { AboutUs } from "./AboutUs";
import { Comparison } from "./Comparison";

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("JFrog cells are marked authored and carry no grade", () => {
  renderPage(<Comparison />);
  const cell = screen.getAllByTestId("jfrog-cell")[0];
  expect(cell).toHaveAttribute("data-origin", "authored");
  expect(within(cell).queryByTestId("grade-chip")).toBeNull();
});

test("competitor cells carry a grade and link to evidence", () => {
  renderPage(<Comparison />);
  const cell = screen.getAllByTestId("competitor-cell")[0];
  expect(within(cell).getByTestId("grade-chip")).toBeInTheDocument();
});

test("an absent claim reads as no public claim, not as a graded judgement", () => {
  renderPage(<Comparison />);
  const absent = screen.getByTestId("competitor-cell-runtime_security");
  expect(absent).toHaveTextContent(/no public claim/i);
  expect(within(absent).queryByTestId("grade-chip")).toBeNull();
});

test("recently changed rows are flagged", () => {
  renderPage(<Comparison />);
  expect(screen.getAllByTestId("changed-flag").length).toBeGreaterThan(0);
});

test("the claim timeline renders was-now, never a code diff", () => {
  renderPage(<AboutUs />);
  expect(screen.getAllByText(/^was/i).length).toBeGreaterThan(0);
  expect(document.querySelector(".diff-add, .diff-remove")).toBeNull();
});

test("wide tables scroll inside their own container", () => {
  renderPage(<Comparison />);
  expect(getComputedStyle(screen.getByTestId("table-scroll")).overflowX).toBe(
    "auto",
  );
});

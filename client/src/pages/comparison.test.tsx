import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import comparisonMatrixFixture from "../fixtures/comparison_matrix.json";
import { AboutUs } from "./AboutUs";
import { Comparison } from "./Comparison";

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("the transposed grid renders a row per competitor", () => {
  renderPage(<Comparison />);
  expect(screen.getByTestId("competitor-row-sonatype")).toBeInTheDocument();
  expect(screen.getByTestId("competitor-row-harbor")).toBeInTheDocument();
  expect(screen.getByTestId("matrix-cell-sonatype-xray")).toBeInTheDocument();
  expect(screen.getByTestId("matrix-cell-harbor-artifactory")).toBeInTheDocument();
});

test("clicking a competitor row shows the detail page with dimension cards", async () => {
  const user = userEvent.setup();
  const xrayComponent = comparisonMatrixFixture.components.find(
    (component) => component.key === "xray",
  );
  const sonatypeCell = xrayComponent?.cells.find(
    (cell) => cell.competitor === "sonatype",
  );
  const evidence = sonatypeCell?.evidence[0];

  renderPage(<Comparison />);
  await user.click(screen.getByTestId("competitor-row-sonatype"));

  expect(screen.getByTestId("competitor-detail")).toBeInTheDocument();
  const xrayCard = screen.getByTestId("dimension-card-xray");
  expect(xrayCard).toBeInTheDocument();
  expect(screen.getByTestId("dimension-card-apptrust")).toBeInTheDocument();

  const link = within(xrayCard).getByRole("link", {
    name: evidence.source_name,
  });
  expect(link).toHaveAttribute("href", evidence.source_url);
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

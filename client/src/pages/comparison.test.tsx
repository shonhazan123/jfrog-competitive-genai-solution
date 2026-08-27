import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, test, vi } from "vitest";
import { api } from "../api/client";
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

afterEach(() => {
  vi.restoreAllMocks();
  queryClient.clear();
});

test("the transposed grid renders a row per competitor", () => {
  renderPage(<Comparison />);
  expect(screen.getByTestId("competitor-row-sonatype")).toBeInTheDocument();
  expect(screen.getByTestId("competitor-row-github")).toBeInTheDocument();
  expect(screen.getByTestId("matrix-cell-sonatype-sca_sbom")).toBeInTheDocument();
  expect(
    screen.getByTestId("matrix-cell-github-artifact_management"),
  ).toBeInTheDocument();
});

test("clicking a competitor row shows the detail page with dimension cards", async () => {
  const user = userEvent.setup();
  const scaDimension = comparisonMatrixFixture.dimensions.find(
    (dimension) => dimension.key === "sca_sbom",
  );
  const sonatypeCell = scaDimension?.cells.find(
    (cell) => cell.competitor === "sonatype",
  );
  const evidence = sonatypeCell?.evidence[0];

  renderPage(<Comparison />);
  await user.click(screen.getByTestId("competitor-row-sonatype"));

  expect(screen.getByTestId("competitor-detail")).toBeInTheDocument();
  const scaCard = screen.getByTestId("dimension-card-sca_sbom");
  expect(scaCard).toBeInTheDocument();
  expect(screen.getByTestId("dimension-card-container_security")).toBeInTheDocument();

  const link = within(scaCard).getByRole("link", {
    name: evidence.source_name,
  });
  expect(link).toHaveAttribute("href", evidence.source_url);
});

test("Run this page posts kind comparison", async () => {
  const user = userEvent.setup();
  const runSurface = vi.spyOn(api, "runSurface").mockResolvedValue({
    run_id: "test-run",
    status: "done",
    stage_label: "Done",
    progress: { current: 1, total: 1 },
    new_items: 2,
    message: "",
  });

  renderPage(<Comparison />);
  await user.click(screen.getByRole("button", { name: /run this page/i }));

  expect(runSurface).toHaveBeenCalledWith("comparison");
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

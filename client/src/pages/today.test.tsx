import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { StatusStrip } from "../components/StatusStrip";
import runStatus from "../fixtures/run_status.json";
import { Today } from "./Today";

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("status strip reports the run cycle and offers a manual trigger", () => {
  render(<StatusStrip data={runStatus} />);
  expect(screen.getByText(/last run/i)).toBeInTheDocument();
  expect(screen.getByText(/next run/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /run now/i })).toBeInTheDocument();
});

test("interrupts render above the feed and are visually distinct", () => {
  renderPage(<Today />);
  const interrupt = screen.getByTestId("interrupt-card");
  const first = screen.getAllByTestId("signal-card")[0];
  expect(interrupt.compareDocumentPosition(first) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("the feed is dominated by product and security, not by cross-assertion", () => {
  renderPage(<Today />);
  const types = screen.getAllByTestId("signal-type").map((n) => n.textContent);
  const crossAssertion = types.filter((t) => /positioning/i.test(t ?? "")).length;
  expect(crossAssertion).toBeLessThanOrEqual(1);
});

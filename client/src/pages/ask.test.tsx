import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { Ask } from "./Ask";
import { Industry } from "./Industry";
import { Digest } from "./Digest";

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("an answer renders its citations beneath it", () => {
  renderPage(<Ask />);
  expect(screen.getAllByTestId("citation-card").length).toBeGreaterThanOrEqual(1);
});

test("a refusal is rendered as a distinct, prominent state", () => {
  renderPage(<Ask />);
  const refusal = screen.getByTestId("refusal");
  expect(refusal).toBeVisible();
  expect(refusal).toHaveTextContent(/don't have grounded evidence/i);
});

test("a refusal offers what the ledger does hold nearby", () => {
  renderPage(<Ask />);
  expect(within(screen.getByTestId("refusal")).getByText(/here's what i do have/i)).toBeInTheDocument();
});

test("industry items carry no competitor entity", () => {
  renderPage(<Industry />);
  expect(screen.getAllByTestId("theme-tile").length).toBeGreaterThanOrEqual(1);
});

test("the digest preview switches persona", async () => {
  renderPage(<Digest />);
  const sales = screen.getByTestId("email-body").textContent;
  await userEvent.click(screen.getByRole("button", { name: /executive/i }));
  expect(screen.getByTestId("email-body").textContent).not.toBe(sales);
});

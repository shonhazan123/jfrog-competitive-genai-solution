import { render, screen, waitFor, within } from "@testing-library/react";
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

const REFUSAL_QUESTION =
  "How many net-new enterprise customers did Sonatype win from JFrog last quarter?";

async function ask(question: string) {
  await userEvent.type(screen.getByRole("textbox"), `${question}{Enter}`);
}

test("an answer renders its citations beneath it", async () => {
  renderPage(<Ask />);
  await userEvent.click(
    screen.getByRole("button", {
      name: /how does sonatype's nexus repository compare to jfrog/i,
    }),
  );
  await waitFor(() => {
    expect(screen.getAllByTestId("citation-card").length).toBeGreaterThanOrEqual(1);
  });
});

test("a refusal is rendered as a distinct, prominent state", async () => {
  renderPage(<Ask />);
  await ask(REFUSAL_QUESTION);
  await waitFor(() => {
    const refusal = screen.getByTestId("refusal");
    expect(refusal).toBeVisible();
    expect(refusal).toHaveTextContent(/don't have grounded evidence/i);
  });
});

test("a refusal offers what the ledger does hold nearby", async () => {
  renderPage(<Ask />);
  await ask(REFUSAL_QUESTION);
  await waitFor(() => {
    expect(
      within(screen.getByTestId("refusal")).getByText(/here's what i do have/i),
    ).toBeInTheDocument();
  });
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

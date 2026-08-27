import type { ReactElement } from "react";
import { render, screen, within } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import signalsTodayFixture from "../fixtures/signals_today.json";
import { Signals } from "./Signals";

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function fixtureGroups() {
  const groups = new Map<
    string,
    { signal_type: string; signal_type_label: string; items: unknown[] }
  >();

  for (const item of signalsTodayFixture.items) {
    const existing = groups.get(item.signal_type);
    if (existing) {
      existing.items.push(item);
    } else {
      groups.set(item.signal_type, {
        signal_type: item.signal_type,
        signal_type_label: item.signal_type_label,
        items: [item],
      });
    }
  }

  return [...groups.values()];
}

test("signals room groups cards by signal type with section labels", () => {
  renderPage(<Signals />);

  expect(screen.queryByRole("tablist")).not.toBeInTheDocument();

  for (const group of fixtureGroups()) {
    const section = screen.getByTestId(`signal-group-${group.signal_type}`);
    expect(
      within(section).getByText(group.signal_type_label),
    ).toBeInTheDocument();
    expect(within(section).getAllByTestId("signal-card").length).toBeGreaterThanOrEqual(
      1,
    );
  }
});

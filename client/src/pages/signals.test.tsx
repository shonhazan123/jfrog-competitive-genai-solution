import type { ReactElement } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, test, vi } from "vitest";
import { api } from "../api/client";
import { queryClient } from "../api/queryClient";
import { signalTypeLabel } from "../config/labels";
import signalsTodayFixture from "../fixtures/signals_today.json";
import { Signals } from "./Signals";

function renderPage(ui: ReactElement) {
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

test("Run this page posts kind signals", async () => {
  const user = userEvent.setup();
  const runSurface = vi.spyOn(api, "runSurface").mockResolvedValue({
    run_id: "test-run",
    status: "done",
    stage_label: "Done",
    progress: { current: 1, total: 1 },
    new_items: 5,
    message: "",
  });

  renderPage(<Signals />);
  await user.click(screen.getByRole("button", { name: /run this page/i }));

  expect(runSurface).toHaveBeenCalledWith("signals");
});

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

function presentTypesFromFixture() {
  const counts = new Map<string, number>();
  for (const item of signalsTodayFixture.items) {
    counts.set(item.signal_type, (counts.get(item.signal_type) ?? 0) + 1);
  }
  return [...counts.keys()];
}

test("signals room shows type filter chips for present types plus All", () => {
  renderPage(<Signals />);

  const filterBar = screen.getByTestId("signal-type-filter");
  const chips = within(filterBar).getAllByRole("button");

  expect(chips.length).toBe(presentTypesFromFixture().length + 1);
  expect(
    within(filterBar).getByRole("button", {
      name: `All (${signalsTodayFixture.items.length})`,
      pressed: true,
    }),
  ).toBeInTheDocument();

  for (const type of presentTypesFromFixture()) {
    const count = signalsTodayFixture.items.filter(
      (item) => item.signal_type === type,
    ).length;
    expect(
      within(filterBar).getByRole("button", {
        name: `${signalTypeLabel(type as never)} (${count})`,
      }),
    ).toBeInTheDocument();
  }
});

test("signals room groups accordion rows by signal type with mono headers", () => {
  renderPage(<Signals />);

  expect(screen.queryByRole("tablist")).not.toBeInTheDocument();

  for (const group of fixtureGroups()) {
    const section = screen.getByTestId(`signal-group-${group.signal_type}`);
    const header = within(section).getByTestId(
      `signal-group-header-${group.signal_type}`,
    );
    expect(
      within(header).getByText(signalTypeLabel(group.signal_type as never), {
        selector: ".mono-label",
      }),
    ).toBeInTheDocument();
    expect(
      within(section).getAllByTestId("signal-accordion-row").length,
    ).toBe(group.items.length);
  }
});

test("signal accordion row expands in place to show intent read", async () => {
  const user = userEvent.setup();
  renderPage(<Signals />);

  const firstSignal = signalsTodayFixture.items[0];
  const trigger = screen.getByTestId(`signal-row-trigger-${firstSignal.id}`);

  expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(
    screen.queryByTestId(`signal-row-body-${firstSignal.id}`),
  ).not.toBeInTheDocument();

  await user.click(trigger);

  expect(trigger).toHaveAttribute("aria-expanded", "true");
  const body = screen.getByTestId(`signal-row-body-${firstSignal.id}`);
  expect(within(body).getByText("Intent read")).toBeInTheDocument();
  expect(within(body).getByTestId("so-what")).toHaveTextContent(
    firstSignal.so_what,
  );
  expect(
    within(body).getByRole("link", { name: firstSignal.evidence[0].source_name }),
  ).toHaveAttribute("href", firstSignal.evidence[0].source_url);
});

test("type filter chip narrows visible groups and rows", async () => {
  const user = userEvent.setup();
  renderPage(<Signals />);

  const productType = presentTypesFromFixture()[0];
  const productCount = signalsTodayFixture.items.filter(
    (item) => item.signal_type === productType,
  ).length;
  const filterBar = screen.getByTestId("signal-type-filter");

  await user.click(
    within(filterBar).getByRole("button", {
      name: `${signalTypeLabel(productType as never)} (${productCount})`,
    }),
  );

  expect(screen.getByTestId(`signal-group-${productType}`)).toBeInTheDocument();
  expect(screen.getAllByTestId("signal-accordion-row")).toHaveLength(
    productCount,
  );

  for (const group of fixtureGroups()) {
    if (group.signal_type !== productType) {
      expect(
        screen.queryByTestId(`signal-group-${group.signal_type}`),
      ).not.toBeInTheDocument();
    }
  }
});

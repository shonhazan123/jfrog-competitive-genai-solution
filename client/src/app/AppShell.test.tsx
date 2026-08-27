import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import { NAVIGATION } from "../config/navigation";
import { AppShell } from "./AppShell";

function renderShell() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AppShell />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("shell renders every navigation label", () => {
  renderShell();
  NAVIGATION.forEach((item) =>
    expect(screen.getByRole("link", { name: new RegExp(item.label, "i") })).toBeInTheDocument()
  );
});

test("shell does not surface benched change-detection pages in the sidebar", () => {
  renderShell();
  expect(screen.queryByRole("link", { name: /Trajectory/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /Competitors → Us/i })).not.toBeInTheDocument();
});

test("no component hardcodes a hex colour", async () => {
  const files = import.meta.glob("../**/*.tsx", { as: "raw", eager: true });
  const offenders = Object.entries(files).filter(([, src]) => /#[0-9a-fA-F]{6}\b/.test(src));
  expect(offenders.map(([p]) => p)).toEqual([]);
});

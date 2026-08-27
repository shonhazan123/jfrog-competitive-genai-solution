import type { ReactElement } from "react";
import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { queryClient } from "../api/queryClient";
import industryThemeDetail from "../fixtures/industry_theme_detail.json";
import industryThemes from "../fixtures/industry_themes.json";
import { Divisions } from "./Divisions";
import { Industry } from "./Industry";
import { ThemePage } from "./ThemePage";

function setViewport(width: number) {
  window.innerWidth = width;
  window.dispatchEvent(new Event("resize"));
}

function renderPage(ui: ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("Divisions and Industry render as multi-column grids", () => {
  setViewport(1440);
  renderPage(<Divisions />);
  expect(getComputedStyle(screen.getByTestId("card-grid")).display).toBe("grid");
});

test("grids collapse to one column below 1000px", () => {
  setViewport(390);
  renderPage(<Divisions />);
  expect(screen.getByTestId("card-grid")).toHaveAttribute("data-columns", "1");
});

test("Industry renders a theme tile per theme in stable API order", () => {
  setViewport(1440);
  renderPage(<Industry />);
  const tiles = screen.getAllByTestId("theme-tile");
  expect(tiles).toHaveLength(industryThemes.length);
  industryThemes.forEach((theme, index) => {
    expect(tiles[index]).toHaveTextContent(theme.label);
    expect(tiles[index]).toHaveTextContent(theme.state_of_play);
  });
});

test("ThemePage shows the JFrog relevance section", () => {
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/industry/regulation"]}>
        <Routes>
          <Route path="/industry/:key" element={<ThemePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(
    screen.getByRole("heading", { name: industryThemeDetail.label }),
  ).toBeInTheDocument();
  expect(screen.getByText("What this means for JFrog")).toBeInTheDocument();
  expect(screen.getByText(industryThemeDetail.jfrog_relevance)).toBeInTheDocument();
});

test("ThemePage card renders evidence source as a link to source_url", () => {
  const item = industryThemeDetail.items[0];
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/industry/regulation"]}>
        <Routes>
          <Route path="/industry/:key" element={<ThemePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const link = screen.getByRole("link", { name: item.evidence.source_name });
  expect(link).toHaveAttribute("href", item.evidence.source_url);
});

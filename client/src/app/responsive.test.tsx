import { render, screen } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { NAVIGATION } from "../config/navigation";
import { queryClient } from "../api/queryClient";
import { AppShell } from "./AppShell";
import { Comparison } from "../pages/Comparison";

function setViewport(width) {
  window.innerWidth = width;
  window.matchMedia = (media) => ({
    matches: width < 900,
    media,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
    dispatchEvent() {},
  });
  window.dispatchEvent(new Event("resize"));
}

function renderPage(ui) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

test("below 900px the sidebar is replaced by a bottom bar of primary items", () => {
  setViewport(390);
  renderPage(<AppShell />);
  expect(screen.queryByTestId("sidebar")).toBeNull();
  expect(screen.getAllByTestId("bottom-nav-item")).toHaveLength(
    NAVIGATION.filter((n) => n.primary).length);
});

test("the page body never scrolls horizontally at 390px", () => {
  setViewport(390);
  renderPage(<Comparison />);
  expect(document.body.scrollWidth).toBeLessThanOrEqual(390);
});

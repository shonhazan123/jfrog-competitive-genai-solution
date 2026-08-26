import { render, screen } from "@testing-library/react";
import type { Citation } from "../api/types";
import { Cited } from "./Cited";
import { PriorityBadge } from "./PriorityBadge";
import { SourceLink } from "./SourceLink";

const CITATION: Citation = {
  source_name: "Competitor blog",
  source_url: "https://example.com/post",
  captured_at: "2026-08-26T10:00:00Z",
  origin: "extracted",
  archived_url: null,
  grade: "B",
};

test("no consumer screen renders a machine value", () => {
  const pages = import.meta.glob("../pages/!(Settings|StyleGuide).tsx", {
    as: "raw",
    eager: true,
  });
  const machineWords =
    /\b(interrupt|product_capability|positioning_messaging|talent_org|market_regulatory|corroboration|materiality)\b/;
  const offenders = Object.entries(pages).filter(([, src]) =>
    machineWords.test(src),
  );
  expect(offenders.map(([p]) => p)).toEqual([]);
});

test("SourceLink always renders a clickable origin", () => {
  render(<SourceLink citation={CITATION} />);
  const link = screen.getByRole("link", { name: /view source/i });
  expect(link).toHaveAttribute("href", CITATION.source_url);
  expect(link).toHaveAttribute("target", "_blank");
});

test("an archived capture offers both the live page and the captured version", () => {
  render(
    <SourceLink
      citation={{ ...CITATION, archived_url: "https://web.archive.org/x" }}
    />,
  );
  expect(screen.getByRole("link", { name: /live page/i })).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /as we captured it/i }),
  ).toBeInTheDocument();
});

test("an authored position states its origin instead of faking a link", () => {
  render(
    <SourceLink
      citation={{ ...CITATION, origin: "authored", source_url: "" }}
    />,
  );
  expect(screen.getByText(/authored by the ci team/i)).toBeInTheDocument();
  expect(screen.queryByRole("link")).toBeNull();
});

test("Cited refuses to render content that has no citation", () => {
  const { container } = render(
    <Cited citation={undefined}>
      <p>orphan claim</p>
    </Cited>,
  );
  expect(container).toBeEmptyDOMElement();
});

test("priority renders as a word, never as a bare number", () => {
  render(<PriorityBadge score={87} />);
  expect(screen.getByText("Critical")).toBeInTheDocument();
  expect(screen.queryByText("87")).toBeNull();
});

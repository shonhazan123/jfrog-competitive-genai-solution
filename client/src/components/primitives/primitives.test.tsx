import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Chip } from "./Chip";
import { ScoreBadge } from "./ScoreBadge";
import { GradeChip } from "./GradeChip";
import { EmptyState } from "./EmptyState";
import { WasNow } from "./WasNow";
import { Disclosure } from "./Disclosure";

test("signal chip maps every one of the nine types to its own hue token", () => {
  const TYPES = ["product_capability","positioning_messaging","pricing_packaging",
    "security_trust","corporate_financial","partnership_ecosystem",
    "customer_evidence","market_regulatory","talent_org"];
  const seen = TYPES.map((t) => {
    const { container } = render(<Chip signalType={t} />);
    return getComputedStyle(container.firstChild as Element).getPropertyValue("--chip-hue");
  });
  expect(new Set(seen).size).toBe(9);
});

test("score badge escalates by weight, not by hue", () => {
  const low = render(<ScoreBadge value={22} />).container.firstChild as HTMLElement;
  const peak = render(<ScoreBadge value={91} />).container.firstChild as HTMLElement;
  expect(low.dataset.tier).toBe("low");
  expect(peak.dataset.tier).toBe("peak");
});

test("grade chip explains itself on hover", () => {
  render(<GradeChip grade="A2" />);
  expect(screen.getByTitle(/completely reliable/i)).toBeInTheDocument();
});

test("empty state reports surveillance, never absence", () => {
  render(<EmptyState headline="No pricing changes for Sonatype in 30 days." detail="Checked 14 times." />);
  expect(screen.getByText(/checked 14 times/i)).toBeInTheDocument();
  expect(screen.queryByText(/nothing found|no results/i)).toBeNull();
});

test("was-now renders two labelled values, not a code diff", () => {
  render(<WasNow was="Limited" now="Very limited, not proactive" />);
  expect(screen.getByText(/^was/i)).toBeInTheDocument();
  expect(screen.getByText(/^now/i)).toBeInTheDocument();
});

test("disclosure is collapsed by default and toggles", async () => {
  render(<Disclosure label="Why this score"><p>detail</p></Disclosure>);
  expect(screen.queryByText("detail")).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: /why this score/i }));
  expect(screen.getByText("detail")).toBeInTheDocument();
});

import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { SignalCard, type SignalCardSignal } from "./SignalCard";
import signals from "../fixtures/signals_sales.json";

const SIGNAL: SignalCardSignal = {
  ...(signals.items[0] as unknown as SignalCardSignal),
  tier: "worth_knowing",
  tier_label: "Worth knowing",
  primary_stakeholder: "sales",
  why_it_matters: "Security advisory relevant to on-prem repository positioning.",
};

test("so-what is visible without any interaction", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  expect(screen.getByText(SIGNAL.so_what)).toBeVisible();
});

test("the verbatim quote and its source line are visible without interaction", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  expect(screen.getByText(new RegExp(SIGNAL.evidence[0].quote.slice(0, 25)))).toBeVisible();
  expect(screen.getByText(new RegExp(SIGNAL.evidence[0].source_name))).toBeVisible();
});

test("renders the evidence source as a link to source_url", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  const link = screen.getByRole("link", { name: SIGNAL.evidence[0].source_name });
  expect(link).toHaveAttribute("href", SIGNAL.evidence[0].source_url);
});

test("shows the tier verdict and one-line reason, with no numbers", () => {
  render(
    <SignalCard
      signal={{
        ...SIGNAL,
        tier: "act_on_it",
        tier_label: "Act on it",
        why_it_matters: "Directly targets Artifactory's SBOM story.",
      }}
      persona="sales"
    />,
  );
  expect(screen.getByText("Act on it")).toBeInTheDocument();
  expect(screen.getByText(/Artifactory's SBOM story/)).toBeInTheDocument();
  expect(screen.queryByTestId("score-badge")).toBeNull();
});

test("only the current persona's so-what renders", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  expect(screen.queryByText(SIGNAL.so_what_exec ?? "__none__")).toBeNull();
});

test("section labels are present so a dense card stays scannable", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  expect(screen.getByText("SO WHAT")).toBeInTheDocument();
  expect(screen.getByText("EVIDENCE")).toBeInTheDocument();
});

test("a caution-flagged security signal shows its handling warning", () => {
  render(
    <SignalCard
      signal={{ ...SIGNAL, signal_type: "security_trust", handling: "caution" }}
      persona="sales"
    />,
  );
  expect(screen.getByText(/lead on posture/i)).toBeInTheDocument();
});

test("renders no was-now diff even when change data is present on the signal", () => {
  const staleSignal = {
    ...SIGNAL,
    change: {
      dimension: "test",
      kind: "substantive",
      was: "old text",
      now: "new text",
    },
  } as unknown as SignalCardSignal;
  render(<SignalCard signal={staleSignal} persona="sales" />);
  expect(screen.queryByText(/^was$/i)).toBeNull();
  expect(document.querySelector(".was-now")).toBeNull();
});

test("the four analyst actions are always reachable", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" onAction={vi.fn()} />);
  ["confirm", "reject", "edit", "mute"].forEach((a) =>
    expect(screen.getByRole("button", { name: new RegExp(a, "i") })).toBeInTheDocument(),
  );
});

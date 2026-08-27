import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { SignalCard } from "./SignalCard";
import signals from "../fixtures/signals_sales.json";
const SIGNAL = signals.items[0];

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

test("only the score breakdown is collapsed", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  expect(screen.queryByText(/source grade/i)).toBeNull();
  expect(screen.getByRole("button", { name: /why this score/i })).toBeInTheDocument();
});

test("score breakdown expands to arithmetic that sums to the total", async () => {
  render(<SignalCard signal={SIGNAL} persona="sales" />);
  await userEvent.click(screen.getByRole("button", { name: /why this score/i }));
  // Ground-truth drift: the list/digest endpoints return score_breakdown: null
  // (confirmed against the live API and API_CONTRACT §1.5 — the arithmetic only
  // exists on GET /signals/{id}). When present it must sum to the total; when the
  // backend omits it, the disclosure surfaces a graceful note instead.
  if (SIGNAL.score_breakdown) {
    const parts = (SIGNAL.score_breakdown as [string, number][]).map(([, v]) => v);
    expect(Math.round(parts.reduce((a, b) => a + b, 0))).toBe(Math.round(SIGNAL.score));
  } else {
    expect(screen.getByText(/score breakdown not available/i)).toBeVisible();
  }
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
  render(<SignalCard signal={{ ...SIGNAL, signal_type: "security_trust", handling: "caution" }} persona="sales" />);
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
  } as unknown as import("./SignalCard").SignalCardSignal;
  render(<SignalCard signal={staleSignal} persona="sales" />);
  expect(screen.queryByText(/^was$/i)).toBeNull();
  expect(document.querySelector(".was-now")).toBeNull();
});

test("the four analyst actions are always reachable", () => {
  render(<SignalCard signal={SIGNAL} persona="sales" onAction={vi.fn()} />);
  ["confirm","reject","edit","mute"].forEach((a) =>
    expect(screen.getByRole("button", { name: new RegExp(a, "i") })).toBeInTheDocument());
});

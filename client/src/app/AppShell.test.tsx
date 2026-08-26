import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { NAVIGATION } from "../config/navigation";
import { AppShell } from "./AppShell";

test("shell renders every navigation label", () => {
  render(<MemoryRouter><AppShell /></MemoryRouter>);
  NAVIGATION.forEach((item) =>
    expect(screen.getByRole("link", { name: new RegExp(item.label, "i") })).toBeInTheDocument()
  );
});

test("no component hardcodes a hex colour", async () => {
  const files = import.meta.glob("../**/*.tsx", { as: "raw", eager: true });
  const offenders = Object.entries(files).filter(([, src]) => /#[0-9a-fA-F]{6}\b/.test(src));
  expect(offenders.map(([p]) => p)).toEqual([]);
});

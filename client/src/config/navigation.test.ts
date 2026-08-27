import { NAVIGATION } from "../config/navigation";

test("navigation is data, grouped into three clusters", () => {
  const groups = [...new Set(NAVIGATION.map((n) => n.group))];
  expect(groups).toEqual(["daily", "reference", "tools"]);
  expect(NAVIGATION).toHaveLength(8);
});

test("every destination has a unique path and a label", () => {
  const paths = NAVIGATION.map((n) => n.path);
  expect(new Set(paths).size).toBe(paths.length);
  expect(NAVIGATION.every((n) => n.label.length > 0)).toBe(true);
});

test("verdict-first primary nav: five daily rooms plus reference and tools", () => {
  const labels = NAVIGATION.map((n) => n.label);
  expect(labels).toEqual([
    "Today",
    "Competitors",
    "Signals",
    "Industry",
    "Ask",
    "Divisions",
    "Settings",
    "Email Digest",
  ]);
  expect(labels).not.toContain("Trajectory");
  expect(labels).not.toContain("Competitors → Us");
  expect(labels).not.toContain("Comparison");
});

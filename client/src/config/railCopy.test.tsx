import type { IndustryRadarItem } from "../api/types";
import { groupIndustry } from "./railCopy";

function industryItem(
  id: string,
  theme_key: string,
  theme_label: string,
): IndustryRadarItem {
  return {
    id,
    signal_type: "security_trust",
    theme_key,
    theme_label,
    headline: `headline ${id}`,
    summary: `summary ${id}`,
    why_it_matters: null,
    occurred_at: null,
    evidence: [],
  };
}

test("groupIndustry buckets by industry theme, not by signal type", () => {
  const groups = groupIndustry([
    industryItem("1", "supply_chain_vulns", "Software Supply-Chain Vulnerabilities & Exploits"),
    industryItem("2", "ai_secops", "AI Code-Gen & ML Security"),
    industryItem("3", "supply_chain_vulns", "Software Supply-Chain Vulnerabilities & Exploits"),
  ]);

  expect(groups.map((g) => g.key)).toEqual(["supply_chain_vulns", "ai_secops"]);
  expect(groups[0].shortLabel).toBe("Supply chain");
  expect(groups[0].cards).toHaveLength(2);
  expect(groups[1].shortLabel).toBe("AI security");
});

test("groupIndustry falls back to signal-type grouping when items lack themes", () => {
  const legacy: IndustryRadarItem = {
    id: "x",
    signal_type: "product_capability",
    headline: "h",
    summary: "s",
    why_it_matters: null,
    occurred_at: null,
    evidence: [],
  };
  const groups = groupIndustry([legacy]);
  expect(groups).toHaveLength(1);
  expect(groups[0].key).toBe("product_capability");
});

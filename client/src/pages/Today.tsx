import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Kit } from "../api/types";
import { KitTile } from "../components/KitTile";
import kitsFixture from "../fixtures/kits.json";

const PRIORITY_RANK: Record<string, number> = {
  Critical: 0,
  High: 1,
  Notable: 2,
  Watch: 3,
};

function findLeadKey(kits: Kit[]): string | null {
  const active = kits.filter((kit) => kit.status === "active" && kit.count > 0);
  if (active.length === 0) {
    return null;
  }

  const sorted = [...active].sort((left, right) => {
    const leftRank = PRIORITY_RANK[left.priority_label ?? "Watch"] ?? 99;
    const rightRank = PRIORITY_RANK[right.priority_label ?? "Watch"] ?? 99;
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return left.order - right.order;
  });

  return sorted[0]?.key ?? null;
}

export function Today() {
  const { data: kits } = useQuery({
    queryKey: ["kits"],
    queryFn: () => api.getKits(),
    initialData: kitsFixture as Kit[],
  });

  const ordered = [...kits].sort((left, right) => left.order - right.order);
  const leadKey = findLeadKey(ordered);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-5)",
        maxWidth: "var(--content-max)",
      }}
    >
      <header>
        <h1 className="page-heading">Today</h1>
      </header>

      <div
        data-testid="kit-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "var(--sp-4)",
        }}
      >
        {ordered.map((kit) => (
          <KitTile key={kit.key} kit={kit} isLead={kit.key === leadKey} />
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { IndustryThemeDetail } from "../api/types";
import { SectionLabel } from "../components/primitives/SectionLabel";
import industryThemeDetailFixture from "../fixtures/industry_theme_detail.json";
import { IndustryCard } from "./Industry";

const GRID_BREAKPOINT = 1000;

function useGridColumns(): string {
  const [columns, setColumns] = useState(() =>
    typeof window !== "undefined" && window.innerWidth < GRID_BREAKPOINT
      ? "1"
      : "auto",
  );

  useEffect(() => {
    const handleResize = () => {
      setColumns(window.innerWidth < GRID_BREAKPOINT ? "1" : "auto");
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return columns;
}

export function ThemePage() {
  const { key = "" } = useParams<{ key: string }>();
  const gridColumns = useGridColumns();

  const { data } = useQuery({
    queryKey: ["industry", "theme", key],
    queryFn: () => api.getThemeDetail(key),
    initialData: industryThemeDetailFixture as IndustryThemeDetail,
  });

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
        <h1 className="page-heading">{data.label}</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          {data.synthesis}
        </p>
      </header>

      <section>
        <SectionLabel>What this means for JFrog</SectionLabel>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          {data.jfrog_relevance}
        </p>
      </section>

      <div
        data-testid="card-grid"
        data-columns={gridColumns}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))",
          gap: "var(--sp-5)",
        }}
      >
        {data.items.map((item) => (
          <IndustryCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

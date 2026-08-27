import { useEffect, useState, type CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { IndustryItem, ListResponse } from "../api/types";
import { signalHue } from "../config/labels";
import { Chip } from "../components/primitives/Chip";
import { GradeChip } from "../components/primitives/GradeChip";
import { Quote } from "../components/primitives/Quote";
import { SectionLabel } from "../components/primitives/SectionLabel";
import industryFeedFixture from "../fixtures/industry_feed.json";

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

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function IndustryCard({ item }: { item: IndustryItem }) {
  const hue = signalHue(item.signal_type);
  const cardStyle = { "--signal-hue": hue } as CSSProperties;

  return (
    <article
      data-testid="signal-card"
      data-entity="industry"
      style={{
        ...cardStyle,
        borderLeft: "4px solid var(--signal-hue)",
        padding: "var(--sp-5)",
        background: "var(--surface)",
        borderRadius: "var(--r-md)",
        boxShadow: "var(--shadow-1)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-4)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--sp-3)",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: "var(--fs-meta)",
            fontWeight: 600,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: "var(--ink-secondary)",
            padding: "var(--sp-1) var(--sp-2)",
            borderRadius: "var(--r-sm)",
            background: "var(--surface-sunk)",
          }}
        >
          {item.standard_chip}
        </span>
        <Chip signalType={item.signal_type} />
        <time
          dateTime={item.occurred_at}
          style={{
            marginLeft: "auto",
            fontSize: "var(--fs-meta)",
            color: "var(--ink-muted)",
          }}
        >
          {formatDate(item.occurred_at)}
        </time>
      </header>

      <h2
        style={{
          fontSize: "var(--fs-headline)",
          lineHeight: "var(--lh-headline)",
          fontWeight: 600,
          color: "var(--ink)",
        }}
      >
        {item.headline}
      </h2>

      <p
        style={{
          fontSize: "var(--fs-body)",
          lineHeight: "var(--lh-body)",
          color: "var(--ink-secondary)",
        }}
      >
        {item.body}
      </p>

      <section>
        <SectionLabel>EVIDENCE</SectionLabel>
        <Quote>{item.evidence.quote}</Quote>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-meta)",
            lineHeight: "var(--lh-meta)",
            color: "var(--ink-secondary)",
          }}
        >
          <a
            href={item.evidence.source_url}
            target="_blank"
            rel="noreferrer"
          >
            {item.evidence.source_name}
          </a>
          {" · "}
          <time dateTime={item.evidence.captured_at}>
            {formatDate(item.evidence.captured_at)}
          </time>
          {" · "}
          <GradeChip grade={item.evidence.reliability_grade} />
        </p>
      </section>
    </article>
  );
}

export function Industry() {
  const gridColumns = useGridColumns();

  const { data } = useQuery({
    queryKey: ["industry"],
    queryFn: () => api.getIndustry(),
    initialData: industryFeedFixture as ListResponse<IndustryItem>,
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
        <h1 className="page-heading">Industry</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          DevSecOps field feed — standards, regulation and ecosystem moves. No
          competitor entity; industry-wide signals only.
        </p>
      </header>

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

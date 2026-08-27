import { useEffect, useState, type CSSProperties } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { IndustryItem, IndustryTheme } from "../api/types";
import { signalHue } from "../config/labels";
import { ThemeTile } from "../components/ThemeTile";
import { Chip } from "../components/primitives/Chip";
import { Quote } from "../components/primitives/Quote";
import { SectionLabel } from "../components/primitives/SectionLabel";
import industryThemesFixture from "../fixtures/industry_themes.json";
import "./Industry.css";

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

export function IndustryCard({ item }: { item: IndustryItem }) {
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
        </p>
      </section>
    </article>
  );
}

export function Industry() {
  const queryClient = useQueryClient();
  const gridColumns = useGridColumns();
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const { data: themes } = useQuery({
    queryKey: ["industry", "themes"],
    queryFn: () => api.getThemes(),
    initialData: industryThemesFixture as IndustryTheme[],
  });

  const handleRunThisPage = async () => {
    if (isRunning) return;
    setRunError(null);
    setIsRunning(true);
    try {
      const result = await api.runSurface("industry");
      if (result.status === "done") {
        void queryClient.invalidateQueries({ queryKey: ["industry", "themes"] });
      } else if (result.status === "failed") {
        setRunError(result.message || "The industry run could not complete.");
      }
    } catch {
      setRunError("Couldn't start the run — is the API reachable?");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="industry">
      <header className="industry__header">
        <p className="industry__eyebrow mono-label">Landscape</p>
        <h1 className="industry__title font-display">Industry &amp; Market</h1>
        <p className="industry__lede">
          The DevSecOps market on its own terms. Click a theme to read the
          synthesis and JFrog relevance.
        </p>
        <button
          type="button"
          data-testid="run-this-page"
          onClick={() => void handleRunThisPage()}
          disabled={isRunning}
          aria-busy={isRunning}
          style={{
            marginTop: "var(--sp-3)",
            padding: "var(--sp-1) var(--sp-3)",
            fontSize: "var(--fs-meta)",
            fontWeight: 500,
            color: isRunning ? "var(--ink-muted)" : "var(--accent)",
            background: isRunning ? "var(--surface-sunk)" : "var(--accent-wash)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            cursor: isRunning ? "not-allowed" : "pointer",
            opacity: isRunning ? 0.7 : 1,
          }}
        >
          {isRunning ? "Running…" : "Run this page"}
        </button>
        {runError ? (
          <p data-testid="run-error" role="alert" className="industry__run-error">
            {runError}
          </p>
        ) : null}
      </header>

      <div
        data-testid="card-grid"
        data-columns={gridColumns}
        className="industry__grid"
        style={{ display: "grid" }}
      >
        {themes.map((theme) => (
          <ThemeTile key={theme.key} theme={theme} />
        ))}
      </div>

      <footer className="industry__footer">
        <p className="industry__footer-note">
          Themes are stable week-to-week so you can track developments without
          losing your bearings. Each industry item carries a JFrog relevance
          line — that is what keeps it intel rather than a news reader.
        </p>
      </footer>
    </div>
  );
}

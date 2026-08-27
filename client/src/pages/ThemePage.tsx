import type { CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { IndustryItem, IndustryThemeDetail } from "../api/types";
import { themeAccentVar } from "../config/themeAccent";
import industryThemeDetailFixture from "../fixtures/industry_theme_detail.json";
import "./ThemePage.css";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function latestItemDate(items: IndustryItem[]): string | null {
  if (items.length === 0) {
    return null;
  }
  const latest = items.reduce((max, item) =>
    item.occurred_at > max ? item.occurred_at : max,
  items[0].occurred_at);
  return formatDate(latest);
}

function BackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path
        d="M9 2L4 7L9 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function JfrogMark() {
  return (
    <svg width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden>
      <path d="M1 4L4 1L7 4L4 7Z" fill="white" />
    </svg>
  );
}

function SourceItem({ item }: { item: IndustryItem }) {
  return (
    <li className="theme-page__source-item">
      <h3 className="theme-page__source-headline">{item.headline}</h3>
      {item.body ? (
        <p className="theme-page__source-relevance">↳ {item.body}</p>
      ) : null}
      <div className="theme-page__source-meta">
        <a href={item.evidence.source_url} target="_blank" rel="noreferrer">
          {item.evidence.source_name}
        </a>
        <span className="theme-page__meta-sep" aria-hidden>
          ·
        </span>
        <time dateTime={item.occurred_at}>{formatDate(item.occurred_at)}</time>
      </div>
    </li>
  );
}

export function ThemePage() {
  const { key = "" } = useParams<{ key: string }>();

  const { data } = useQuery({
    queryKey: ["industry", "theme", key],
    queryFn: () => api.getThemeDetail(key),
    initialData: industryThemeDetailFixture as IndustryThemeDetail,
  });

  const accent = themeAccentVar(key);
  const pageStyle = { "--theme-accent": `var(${accent})` } as CSSProperties;
  const itemCount = data.items.length;
  const updatedLabel = latestItemDate(data.items);

  return (
    <div className="theme-page" style={pageStyle}>
      <Link to="/industry" className="theme-page__back">
        <BackIcon />
        Back to Industry
      </Link>

      <header>
        <div className="theme-page__hero-accent" aria-hidden />
        <h1 className="theme-page__title font-display">{data.label}</h1>
        {(itemCount > 0 || updatedLabel) && (
          <div className="theme-page__meta">
            {itemCount > 0 ? (
              <span className="mono-label">
                {itemCount} {itemCount === 1 ? "item" : "items"} tracked
              </span>
            ) : null}
            {itemCount > 0 && updatedLabel ? (
              <span className="theme-page__meta-sep" aria-hidden>
                ·
              </span>
            ) : null}
            {updatedLabel ? (
              <span className="mono-label">Updated {updatedLabel}</span>
            ) : null}
          </div>
        )}
      </header>

      <hr className="theme-page__divider" />

      {data.synthesis ? (
        <section>
          <h2 className="theme-page__section-label mono-label">State of Play</h2>
          <p className="theme-page__state-text">{data.synthesis}</p>
        </section>
      ) : null}

      {data.jfrog_relevance ? (
        <section className="theme-page__jfrog-callout" aria-labelledby="jfrog-relevance-heading">
          <div className="theme-page__jfrog-header">
            <span className="theme-page__jfrog-mark">
              <JfrogMark />
            </span>
            <h2
              id="jfrog-relevance-heading"
              className="theme-page__jfrog-label mono-label"
            >
              What this means for JFrog
            </h2>
          </div>
          <p className="theme-page__jfrog-text">{data.jfrog_relevance}</p>
        </section>
      ) : null}

      {data.items.length > 0 ? (
        <section>
          <h2 className="theme-page__section-label mono-label">Source Items</h2>
          <ul className="theme-page__source-list">
            {data.items.map((item) => (
              <SourceItem key={item.id} item={item} />
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { IndustryTheme } from "../api/types";
import { themeAccentVar } from "../config/themeAccent";
import "./ThemeTile.css";

interface ThemeTileProps {
  theme: IndustryTheme;
  areas?: string[];
}

function ArrowIcon() {
  return (
    <svg
      className="theme-tile__arrow"
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden
    >
      <path
        d="M2.5 6H9.5M6.5 3L9.5 6L6.5 9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ThemeTile({ theme, areas }: ThemeTileProps) {
  const accent = themeAccentVar(theme.key);
  const tileStyle = { "--theme-accent": `var(${accent})` } as CSSProperties;
  const visibleAreas = areas?.slice(0, 2) ?? [];

  return (
    <Link
      to={`/industry/${theme.key}`}
      data-testid="theme-tile"
      className="theme-tile"
      style={tileStyle}
    >
      <div className="theme-tile__accent" aria-hidden />
      <h2 className="theme-tile__title font-display">{theme.label}</h2>
      <p className="theme-tile__state">{theme.state_of_play}</p>
      <div className="theme-tile__footer">
        {visibleAreas.length > 0 ? (
          <div className="theme-tile__areas">
            {visibleAreas.map((area) => (
              <span key={area} className="theme-tile__area-chip">
                {area}
              </span>
            ))}
          </div>
        ) : (
          <span />
        )}
        <div className="theme-tile__count-row">
          <span className="theme-tile__count">{theme.count}</span>
          <span className="theme-tile__count-label">items</span>
          <ArrowIcon />
        </div>
      </div>
    </Link>
  );
}

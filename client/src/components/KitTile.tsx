import type { Kit } from "../api/types";
import { stateLabel } from "../config/labels";
import { Cited } from "./Cited";
import { SourceLink } from "./SourceLink";
import "./KitTile.css";

interface KitTileProps {
  kit: Kit;
  isLead?: boolean;
}

function isActiveKit(kit: Kit): boolean {
  return kit.status === "active" && kit.count > 0 && kit.snippet !== null;
}

export function KitTile({ kit, isLead = false }: KitTileProps) {
  const active = isActiveKit(kit);
  const tileClass = ["kit-tile", isLead ? "kit-tile--wide" : ""]
    .filter(Boolean)
    .join(" ");

  const snippetBody =
    active && kit.snippet ? (
      <Cited citation={kit.snippet.citation}>
        <div className="kit-tile__snippet">
          <p className="kit-tile__headline">{kit.snippet.headline}</p>
          <p className="kit-tile__quote" data-testid="snippet-quote">
            {kit.snippet.quote}
          </p>
          <p className="kit-tile__implication" data-testid="snippet-implication">
            {kit.snippet.implication}
          </p>
          <div className="kit-tile__source">
            <SourceLink citation={kit.snippet.citation} />
          </div>
        </div>
      </Cited>
    ) : null;

  return (
    <div data-testid="kit-tile">
      <article
        className={tileClass}
        data-testid={isLead ? "kit-tile-lead" : undefined}
      >
        <header className="kit-tile__header">
          <div className="kit-tile__label-row">
            <h2 className="kit-tile__label">{kit.label}</h2>
            {kit.priority_label ? (
              <span className="kit-tile__priority">{kit.priority_label}</span>
            ) : null}
          </div>
          <p className="kit-tile__question">{kit.question}</p>
          {active ? (
            <span className="kit-tile__meta">
              {kit.count} {kit.count === 1 ? "signal" : "signals"} this run
            </span>
          ) : null}
        </header>

        {active && snippetBody ? (
          <div data-testid="kit-tile-active">{snippetBody}</div>
        ) : (
          <p className="kit-tile__quiet">{stateLabel("no_change")}</p>
        )}
      </article>
    </div>
  );
}

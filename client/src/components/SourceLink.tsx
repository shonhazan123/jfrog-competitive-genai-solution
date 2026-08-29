import type { ReactNode } from "react";
import type { Citation } from "../api/types";
import { originLabel } from "../config/labels";
import "./SourceLink.css";

interface SourceLinkProps {
  citation: Citation;
  /** When "name", the anchor text is the source name (Ask citation badges). */
  variant?: "default" | "name";
}

function isLive(href: string | null | undefined): href is string {
  return typeof href === "string" && /^https?:\/\//.test(href);
}

function ExternalLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  // Never render a dead anchor: an empty/relative href resolves to the current
  // page. Fall back to plain text when there is no live URL to link to.
  if (!isLive(href)) {
    return <span className="source-link__anchor">{children}</span>;
  }
  return (
    <a
      className="source-link__anchor"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  );
}

export function SourceLink({ citation, variant = "default" }: SourceLinkProps) {
  if (citation.origin === "authored") {
    return (
      <span className="source-link source-link--authored">
        {originLabel("authored")}
      </span>
    );
  }

  if (citation.archived_url) {
    return (
      <span className="source-link">
        <ExternalLink href={citation.source_url}>
          {variant === "name" ? citation.source_name : "Live page"}
        </ExternalLink>
        <span className="source-link__sep" aria-hidden="true">
          {" · "}
        </span>
        <ExternalLink href={citation.archived_url}>
          {variant === "name" ? "Captured copy" : "As we captured it"}
        </ExternalLink>
      </span>
    );
  }

  return (
    <ExternalLink href={citation.source_url}>
      {variant === "name" ? citation.source_name : "View source"}
    </ExternalLink>
  );
}

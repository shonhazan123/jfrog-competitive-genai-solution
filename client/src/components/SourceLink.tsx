import type { ReactNode } from "react";
import type { Citation } from "../api/types";
import { originLabel } from "../config/labels";
import "./SourceLink.css";

interface SourceLinkProps {
  citation: Citation;
}

function ExternalLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
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

export function SourceLink({ citation }: SourceLinkProps) {
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
        <ExternalLink href={citation.source_url}>Live page</ExternalLink>
        <span className="source-link__sep" aria-hidden="true">
          {" · "}
        </span>
        <ExternalLink href={citation.archived_url}>
          As we captured it
        </ExternalLink>
      </span>
    );
  }

  return (
    <ExternalLink href={citation.source_url}>View source</ExternalLink>
  );
}

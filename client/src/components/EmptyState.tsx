import type { ReactNode } from "react";
import "./EmptyState.css";

interface EmptyStateProps {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  testId?: string;
}

/**
 * Instructive placeholder shown when a surface has no data yet (typically the
 * very first run against a fresh database). Presentational only — the caller
 * supplies the copy and the action button.
 */
export function EmptyState({
  eyebrow,
  title,
  children,
  action,
  testId,
}: EmptyStateProps) {
  return (
    <section className="empty-state" data-testid={testId}>
      {eyebrow ? (
        <span className="empty-state__eyebrow mono-label">{eyebrow}</span>
      ) : null}
      <h2 className="empty-state__title font-display">{title}</h2>
      {children ? <div className="empty-state__body">{children}</div> : null}
      {action ? <div className="empty-state__action">{action}</div> : null}
    </section>
  );
}

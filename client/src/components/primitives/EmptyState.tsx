import "./EmptyState.css";

interface EmptyStateProps {
  headline: string;
  detail: string;
}

export function EmptyState({ headline, detail }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="empty-state__headline">{headline}</p>
      <p className="empty-state__detail">{detail}</p>
    </div>
  );
}

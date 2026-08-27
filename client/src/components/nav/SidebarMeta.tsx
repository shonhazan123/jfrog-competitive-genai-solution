import type { RunStatus } from "../../api/types";

interface SidebarMetaProps {
  data?: RunStatus;
}

function formatRelativeUpdate(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 0) {
    return "Updated recently";
  }
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) {
    return "Updated just now";
  }
  if (minutes < 60) {
    return `Updated ${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours === 1) {
    return "Updated 1h ago";
  }
  if (hours < 48) {
    return `Updated ${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  if (days === 1) {
    return "Updated 1d ago";
  }
  return `Updated ${days}d ago`;
}

function formatMetaDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function SidebarMeta({ data }: SidebarMetaProps) {
  if (!data) {
    return null;
  }

  const lastRunAt = data.finished_at ?? data.started_at;
  const dateLineParts: string[] = [];

  if (lastRunAt) {
    dateLineParts.push(formatMetaDate(lastRunAt));
  }
  if (data.sources_count != null) {
    dateLineParts.push(`${data.sources_count} sources`);
  }

  return (
    <div className="sidebar__footer-meta mono-label" data-testid="sidebar-meta">
      {lastRunAt ? <div>{formatRelativeUpdate(lastRunAt)}</div> : null}
      {dateLineParts.length > 0 ? (
        <div className="sidebar__footer-meta-line">{dateLineParts.join(" · ")}</div>
      ) : null}
    </div>
  );
}

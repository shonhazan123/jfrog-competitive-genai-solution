import { priorityLabel } from "../config/labels";
import "./PriorityBadge.css";

interface PriorityBadgeProps {
  score: number;
}

/** Renders the priority band word — never the raw score number. */
export function PriorityBadge({ score }: PriorityBadgeProps) {
  return <span className="priority-badge">{priorityLabel(score)}</span>;
}

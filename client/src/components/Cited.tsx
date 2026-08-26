import type { ReactNode } from "react";
import type { Citation } from "../api/types";

interface CitedProps {
  citation: Citation | null | undefined;
  children: ReactNode;
}

/** Renders children only when a citation is present — no assertion without an origin. */
export function Cited({ citation, children }: CitedProps) {
  if (!citation) return null;
  return <>{children}</>;
}

import type { ReactNode } from "react";
import "./Panel.css";

interface PanelProps {
  title?: string;
  children: ReactNode;
}

export function Panel({ title, children }: PanelProps) {
  return (
    <section className="panel">
      {title ? <h2 className="panel__title">{title}</h2> : null}
      <div className="panel__body">{children}</div>
    </section>
  );
}

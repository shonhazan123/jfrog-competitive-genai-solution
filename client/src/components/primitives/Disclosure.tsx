import { useState, type ReactNode } from "react";
import "./Disclosure.css";

interface DisclosureProps {
  label: string;
  children: ReactNode;
}

export function Disclosure({ label, children }: DisclosureProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="disclosure">
      <button
        type="button"
        className="disclosure__trigger"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span className="disclosure__icon" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
        {label}
      </button>
      {open ? <div className="disclosure__content">{children}</div> : null}
    </div>
  );
}

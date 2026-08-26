import { useState } from "react";
import type { EmailPreview, Persona } from "../api/types";
import { Panel } from "../components/primitives/Panel";
import emailPreviewFixture from "../fixtures/email_preview.json";

const PERSONAS: { id: Persona; label: string }[] = [
  { id: "sales", label: "Sales" },
  { id: "product", label: "Product" },
  { id: "exec", label: "Executive" },
];

const previews = emailPreviewFixture as Record<Persona, EmailPreview>;

function formatEmailBody(preview: EmailPreview): string {
  const lines = [
    preview.subject,
    preview.meta,
    "",
    preview.lead,
    "",
    ...preview.items.map(
      (item) =>
        `${item.headline}\n${item.so_what}${item.flag ? ` (${item.flag})` : ""}`,
    ),
    "",
    preview.footer,
  ];
  return lines.join("\n");
}

export function Digest() {
  const [persona, setPersona] = useState<Persona>("sales");
  const preview = previews[persona];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-5)",
        maxWidth: "var(--content-max)",
      }}
    >
      <header>
        <h1 className="page-heading">Email Digest</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          Preview the digest email as each persona would receive it.
        </p>
      </header>

      <div
        style={{
          display: "flex",
          gap: "var(--sp-2)",
          flexWrap: "wrap",
        }}
      >
        {PERSONAS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setPersona(id)}
            aria-pressed={persona === id}
            style={{
              padding: "var(--sp-2) var(--sp-4)",
              fontSize: "var(--fs-meta)",
              fontWeight: persona === id ? 600 : 500,
              color: persona === id ? "var(--accent)" : "var(--ink-secondary)",
              background: persona === id ? "var(--accent-wash)" : "var(--surface)",
              border: `1px solid ${persona === id ? "var(--accent)" : "var(--border)"}`,
              borderRadius: "var(--r-sm)",
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <Panel title="Inbox preview">
        <div
          style={{
            fontSize: "var(--fs-meta)",
            color: "var(--ink-muted)",
            marginBottom: "var(--sp-4)",
          }}
        >
          <p>
            From: {preview.from_name} &lt;{preview.from_email}&gt;
          </p>
          <p>Subject: {preview.subject}</p>
        </div>

        <div
          data-testid="email-body"
          style={{
            padding: "var(--sp-5)",
            background: "var(--surface-sunk)",
            borderRadius: "var(--r-md)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink)",
            whiteSpace: "pre-wrap",
          }}
        >
          {formatEmailBody(preview)}
        </div>
      </Panel>
    </div>
  );
}

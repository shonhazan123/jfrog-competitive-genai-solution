import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { CompetitorsConfig } from "../api/types";

interface CompetitorEditorProps {
  config: CompetitorsConfig;
}

function slugFromName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function CompetitorEditor({ config }: CompetitorEditorProps) {
  const queryClient = useQueryClient();
  const [competitors, setCompetitors] = useState(() => [...config.competitors]);
  const [draftName, setDraftName] = useState("");

  const mutation = useMutation({
    mutationFn: () => api.putCompetitors(competitors, "analyst"),
    onSuccess: (updated) => {
      queryClient.setQueryData(["competitors"], updated);
      setCompetitors([...updated.competitors]);
    },
  });

  function addCompetitor() {
    const name = draftName.trim();
    if (!name) return;
    const slug = slugFromName(name);
    if (!slug || competitors.some((c) => c.slug === slug)) return;
    setCompetitors((prev) => [...prev, { slug, name }]);
    setDraftName("");
  }

  function removeCompetitor(slug: string) {
    setCompetitors((prev) => prev.filter((c) => c.slug !== slug));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>
      <p
        style={{
          fontSize: "var(--fs-meta)",
          lineHeight: "var(--lh-meta)",
          color: "var(--ink-muted)",
        }}
      >
        Adding a competitor does not start collection automatically — one with no
        configured source appears as a coverage gap in the matrix above.
      </p>

      <ul
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--sp-2)",
          margin: 0,
          padding: 0,
          listStyle: "none",
        }}
      >
        {competitors.map((competitor) => (
          <li
            key={competitor.slug}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--sp-1)",
              padding: "var(--sp-1) var(--sp-2)",
              backgroundColor: "var(--accent-wash)",
              color: "var(--accent)",
              borderRadius: "var(--r-sm)",
              fontSize: "var(--fs-meta)",
            }}
          >
            {competitor.name}
            <button
              type="button"
              onClick={() => removeCompetitor(competitor.slug)}
              aria-label={`Remove ${competitor.name}`}
              style={{
                fontSize: "var(--fs-meta)",
                color: "var(--ink-muted)",
                lineHeight: 1,
              }}
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      <div style={{ display: "flex", gap: "var(--sp-2)" }}>
        <input
          type="text"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addCompetitor();
            }
          }}
          placeholder="Add a competitor…"
          aria-label="New competitor name"
          style={{
            flex: 1,
            padding: "var(--sp-2) var(--sp-3)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            fontSize: "var(--fs-body)",
            backgroundColor: "var(--surface)",
            color: "var(--ink)",
          }}
        />
        <button
          type="button"
          onClick={addCompetitor}
          style={{
            padding: "var(--sp-2) var(--sp-4)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            fontSize: "var(--fs-body)",
            color: "var(--ink-secondary)",
            backgroundColor: "var(--surface)",
          }}
        >
          Add
        </button>
      </div>

      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        style={{
          alignSelf: "flex-start",
          padding: "var(--sp-2) var(--sp-4)",
          backgroundColor: "var(--accent)",
          color: "var(--ink-inverse)",
          borderRadius: "var(--r-sm)",
          fontSize: "var(--fs-body)",
          fontWeight: 500,
        }}
      >
        {mutation.isPending ? "Saving…" : "Save competitors"}
      </button>
    </div>
  );
}

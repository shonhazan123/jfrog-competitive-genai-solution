import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Watchlist } from "../api/types";

interface WatchlistEditorProps {
  watchlist: Watchlist;
}

export function WatchlistEditor({ watchlist }: WatchlistEditorProps) {
  const queryClient = useQueryClient();
  const [terms, setTerms] = useState(() => [...watchlist.terms]);
  const [draft, setDraft] = useState("");

  const mutation = useMutation({
    mutationFn: () => api.putWatchlist({ actor: "analyst", terms }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["watchlist"], updated);
      setTerms([...updated.terms]);
    },
  });

  function addTerm() {
    const trimmed = draft.trim();
    if (!trimmed || terms.includes(trimmed)) return;
    setTerms((prev) => [...prev, trimmed]);
    setDraft("");
  }

  function removeTerm(term: string) {
    setTerms((prev) => prev.filter((t) => t !== term));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>
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
        {terms.map((term) => (
          <li
            key={term}
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
            {term}
            <button
              type="button"
              onClick={() => removeTerm(term)}
              aria-label={`Remove ${term}`}
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
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTerm();
            }
          }}
          placeholder="Add a watchlist term…"
          aria-label="New watchlist term"
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
          onClick={addTerm}
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
        {mutation.isPending ? "Saving…" : "Save watchlist"}
      </button>
    </div>
  );
}

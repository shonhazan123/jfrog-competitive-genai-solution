import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { InstructionsConfig } from "../api/types";

interface InstructionsEditorProps {
  config: InstructionsConfig;
}

export function InstructionsEditor({ config }: InstructionsEditorProps) {
  const queryClient = useQueryClient();
  const [instructions, setInstructions] = useState(() => [...config.instructions]);
  const [draft, setDraft] = useState("");

  const mutation = useMutation({
    mutationFn: () => api.putInstructions(instructions, "analyst"),
    onSuccess: (updated) => {
      queryClient.setQueryData(["instructions"], updated);
      setInstructions([...updated.instructions]);
    },
  });

  function addInstruction() {
    const trimmed = draft.trim();
    if (!trimmed || instructions.includes(trimmed)) return;
    setInstructions((prev) => [...prev, trimmed]);
    setDraft("");
  }

  function updateInstruction(index: number, value: string) {
    setInstructions((prev) => prev.map((line, i) => (i === index ? value : line)));
  }

  function removeInstruction(index: number) {
    setInstructions((prev) => prev.filter((_, i) => i !== index));
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
        Plain-language instructions to the analyst engine — for example, “flag
        anything mentioning SLSA” or “when scoring security items, lead on
        posture.”
      </p>

      <ul
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--sp-2)",
          margin: 0,
          padding: 0,
          listStyle: "none",
        }}
      >
        {instructions.map((line, index) => (
          <li
            key={`${index}-${line.slice(0, 24)}`}
            style={{ display: "flex", gap: "var(--sp-2)", alignItems: "center" }}
          >
            <input
              type="text"
              value={line}
              onChange={(e) => updateInstruction(index, e.target.value)}
              aria-label={`Instruction ${index + 1}`}
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
              onClick={() => removeInstruction(index)}
              aria-label={`Remove instruction ${index + 1}`}
              style={{
                padding: "var(--sp-2)",
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
              addInstruction();
            }
          }}
          placeholder="Add an instruction…"
          aria-label="New instruction"
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
          onClick={addInstruction}
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
        {mutation.isPending ? "Saving…" : "Save instructions"}
      </button>
    </div>
  );
}

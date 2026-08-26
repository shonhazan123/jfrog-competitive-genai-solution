import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { MaterialityConfig } from "../api/types";

interface WeightEditorProps {
  config: MaterialityConfig;
}

export function WeightEditor({ config }: WeightEditorProps) {
  const queryClient = useQueryClient();
  const [weights, setWeights] = useState(
    () => new Map(config.weights.map((w) => [w.key, w.value])),
  );

  const mutation = useMutation({
    mutationFn: () =>
      api.putMateriality({
        actor: "analyst",
        weights: config.weights.map((w) => ({
          key: w.key,
          value: weights.get(w.key) ?? w.value,
        })),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["materiality"], updated);
    },
  });

  function updateWeight(key: string, value: number) {
    setWeights((prev) => new Map(prev).set(key, value));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-4)" }}>
      {config.weights.map((weight) => {
        const current = weights.get(weight.key) ?? weight.value;
        return (
          <div
            key={weight.key}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr auto",
              gap: "var(--sp-2) var(--sp-4)",
              alignItems: "center",
              padding: "var(--sp-3)",
              backgroundColor: "var(--surface-sunk)",
              borderRadius: "var(--r-md)",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "var(--fs-body)",
                  lineHeight: "var(--lh-body)",
                  fontWeight: 500,
                }}
              >
                {weight.label}
              </div>
              <div
                style={{
                  marginTop: "var(--sp-1)",
                  fontSize: "var(--fs-meta)",
                  lineHeight: "var(--lh-meta)",
                  color: "var(--ink-muted)",
                }}
              >
                {weight.note}
              </div>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--sp-3)",
              }}
            >
              <input
                type="range"
                min={weight.min}
                max={weight.max}
                step={weight.step}
                value={current}
                onChange={(e) =>
                  updateWeight(weight.key, Number(e.target.value))
                }
                aria-label={weight.label}
                style={{ width: "120px" }}
              />
              <input
                type="number"
                min={weight.min}
                max={weight.max}
                step={weight.step}
                value={current}
                onChange={(e) =>
                  updateWeight(weight.key, Number(e.target.value))
                }
                aria-label={`${weight.label} value`}
                style={{
                  width: "72px",
                  padding: "var(--sp-1) var(--sp-2)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--r-sm)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--fs-mono)",
                  backgroundColor: "var(--surface)",
                  color: "var(--ink)",
                }}
              />
              <span
                style={{
                  fontSize: "var(--fs-meta)",
                  color: "var(--ink-muted)",
                  minWidth: "48px",
                }}
              >
                {weight.unit}
              </span>
            </div>
          </div>
        );
      })}

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
        {mutation.isPending ? "Saving…" : "Save weights"}
      </button>
    </div>
  );
}

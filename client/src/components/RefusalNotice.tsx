import type { NearbyItem } from "../api/types";
import { SectionLabel } from "./primitives/SectionLabel";

interface RefusalNoticeProps {
  answer: string;
  refusalReason: string | null;
  nearbyEvidence: NearbyItem[];
  className?: string;
}

export function RefusalNotice({
  answer,
  refusalReason,
  nearbyEvidence,
  className,
}: RefusalNoticeProps) {
  return (
    <div
      data-testid="refusal"
      role="alert"
      className={className}
      style={{
        padding: "var(--sp-5)",
        borderRadius: "var(--r-md)",
        border: "1px solid var(--caution)",
        background: "var(--caution-wash)",
      }}
    >
      {refusalReason ? (
        <p
          style={{
            fontSize: "var(--fs-meta)",
            fontWeight: 600,
            color: "var(--caution)",
            marginBottom: "var(--sp-3)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          {refusalReason}
        </p>
      ) : null}
      <p
        style={{
          fontSize: "var(--fs-body)",
          lineHeight: "var(--lh-body)",
          color: "var(--ink)",
        }}
      >
        {answer}
      </p>
      {nearbyEvidence.length > 0 ? (
        <section style={{ marginTop: "var(--sp-4)" }}>
          <SectionLabel>NEARBY EVIDENCE</SectionLabel>
          <ul
            style={{
              marginTop: "var(--sp-2)",
              paddingLeft: "var(--sp-5)",
              fontSize: "var(--fs-body)",
              lineHeight: "var(--lh-body)",
              color: "var(--ink-secondary)",
            }}
          >
            {nearbyEvidence.map((item, index) => (
              <li key={index}>{item.text}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

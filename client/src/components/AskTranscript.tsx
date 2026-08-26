import type { AskResponse } from "../api/types";
import { CitationCard } from "./CitationCard";
import { RefusalNotice } from "./RefusalNotice";

interface AskTranscriptProps {
  exchanges: AskResponse[];
}

export function AskTranscript({ exchanges }: AskTranscriptProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--sp-6)",
      }}
    >
      {exchanges.map((exchange, index) => (
        <article
          key={index}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--sp-4)",
            paddingBottom: "var(--sp-6)",
            borderBottom:
              index < exchanges.length - 1 ? "1px solid var(--border)" : undefined,
          }}
        >
          <p
            style={{
              fontSize: "var(--fs-headline)",
              lineHeight: "var(--lh-headline)",
              fontWeight: 600,
              color: "var(--ink)",
            }}
          >
            {exchange.question}
          </p>

          {exchange.grounded ? (
            <>
              <p
                style={{
                  fontSize: "var(--fs-body)",
                  lineHeight: "var(--lh-body)",
                  color: "var(--ink)",
                }}
              >
                {exchange.answer}
              </p>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "var(--sp-3)",
                }}
              >
                {exchange.evidence.map((item) => (
                  <CitationCard key={item.n} evidence={item} />
                ))}
              </div>
            </>
          ) : (
            <RefusalNotice
              answer={exchange.answer}
              refusalReason={exchange.refusal_reason}
              nearbyEvidence={exchange.nearby_evidence}
            />
          )}
        </article>
      ))}
    </div>
  );
}

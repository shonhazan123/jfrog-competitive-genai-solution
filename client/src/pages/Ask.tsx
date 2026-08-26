import { Panel } from "../components/primitives/Panel";
import { AskTranscript } from "../components/AskTranscript";
import askTranscriptFixture from "../fixtures/ask_transcript.json";
import type { AskResponse } from "../api/types";

const exchanges = (askTranscriptFixture as { exchanges: AskResponse[] }).exchanges;

export function Ask() {
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
        <h1 className="page-heading">Ask</h1>
        <p
          style={{
            marginTop: "var(--sp-2)",
            fontSize: "var(--fs-body)",
            lineHeight: "var(--lh-body)",
            color: "var(--ink-secondary)",
          }}
        >
          Grounded answers from the ledger. When evidence is insufficient, the
          system refuses and offers what it does hold nearby.
        </p>
      </header>

      <Panel title="Transcript">
        <AskTranscript exchanges={exchanges} />
      </Panel>
    </div>
  );
}

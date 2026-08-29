import type { AskResponse } from "../api/types";
import { CitationCard } from "./CitationCard";
import { RefusalNotice } from "./RefusalNotice";
import "./AskTranscript.css";

interface AskTranscriptProps {
  exchanges: AskResponse[];
  pending?: boolean;
  pendingQuestion?: string | null;
  streamingQuestion?: string | null;
  streamingAnswer?: string;
}

function AssistantAvatar() {
  return (
    <div className="ask-assistant__avatar" aria-hidden="true">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
        <path d="M1 5L5 1L9 5L5 9Z" fill="currentColor" />
      </svg>
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="ask-user">
      <div className="ask-user__bubble">{content}</div>
    </div>
  );
}

function AssistantExchange({ exchange }: { exchange: AskResponse }) {
  return (
    <>
      <UserBubble content={exchange.question} />
      <div className="ask-assistant">
        <AssistantAvatar />
        <div className="ask-assistant__body">
          <div className="ask-assistant__label">Intel Assistant</div>
          {exchange.grounded ? (
            <>
              <p className="ask-assistant__answer">{exchange.answer}</p>
              {exchange.evidence.length > 0 ? (
                <div className="ask-assistant__citations">
                  {exchange.evidence.map((item) => (
                    <CitationCard key={item.n} evidence={item} />
                  ))}
                </div>
              ) : null}
            </>
          ) : (
            <RefusalNotice
              answer={exchange.answer}
              refusalReason={exchange.refusal_reason}
              nearbyEvidence={exchange.nearby_evidence}
              className="ask-assistant__refusal"
            />
          )}
        </div>
      </div>
    </>
  );
}

function StreamingExchange({
  question,
  answer,
}: {
  question: string;
  answer: string;
}) {
  return (
    <>
      <UserBubble content={question} />
      <div className="ask-assistant">
        <AssistantAvatar />
        <div className="ask-assistant__body">
          <div className="ask-assistant__label">Intel Assistant</div>
          <p className="ask-assistant__answer">
            {answer}
            <span className="ask-assistant__caret" aria-hidden="true">
              ▌
            </span>
          </p>
        </div>
      </div>
    </>
  );
}

function AskLoader() {
  return (
    <div className="ask-loader" aria-live="polite" aria-busy="true">
      <AssistantAvatar />
      <div className="ask-loader__dots" aria-label="Loading answer">
        <span className="ask-loader__dot" />
        <span className="ask-loader__dot" />
        <span className="ask-loader__dot" />
      </div>
    </div>
  );
}

export function AskTranscript({
  exchanges,
  pending = false,
  pendingQuestion = null,
  streamingQuestion = null,
  streamingAnswer = "",
}: AskTranscriptProps) {
  const isStreaming = Boolean(streamingQuestion);
  const showStreamingAnswer = isStreaming && streamingAnswer.length > 0;
  const showPendingUser =
    !isStreaming &&
    pendingQuestion &&
    !exchanges.some((exchange) => exchange.question === pendingQuestion);

  return (
    <div className="ask-transcript">
      {exchanges.map((exchange, index) => (
        <div key={`${exchange.question}-${index}`}>
          <AssistantExchange exchange={exchange} />
        </div>
      ))}
      {showStreamingAnswer ? (
        <StreamingExchange
          question={streamingQuestion as string}
          answer={streamingAnswer}
        />
      ) : isStreaming ? (
        <>
          <UserBubble content={streamingQuestion as string} />
          <AskLoader />
        </>
      ) : (
        <>
          {showPendingUser ? <UserBubble content={pendingQuestion} /> : null}
          {pending ? <AskLoader /> : null}
        </>
      )}
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { AskResponse } from "../api/types";
import { AskTranscript } from "../components/AskTranscript";
import "./Ask.css";

const SUGGESTED_QUESTIONS = [
  "What has Sonatype changed about how it describes JFrog's malware detection?",
  "On AI and model artifacts, where does Sonatype stand versus JFrog right now?",
  "How many net-new enterprise customers did Sonatype win from JFrog last quarter?",
];

function SuggestedQuestions({ onSelect }: { onSelect: (question: string) => void }) {
  return (
    <div className="ask-suggested">
      <p className="mono-label ask-suggested__label">Suggested questions</p>
      <ul className="ask-suggested__list">
        {SUGGESTED_QUESTIONS.map((question, index) => (
          <li key={question}>
            <button
              type="button"
              className="ask-suggested__item"
              onClick={() => onSelect(question)}
            >
              <span className="ask-suggested__row">
                <span className="mono-label ask-suggested__num">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {question}
                <svg
                  className="ask-suggested__arrow"
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M2.5 6H9.5M6.5 3L9.5 6L6.5 9"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="ask-suggested__note">
        This assistant indexes collected signals — competitor cards, industry themes, hiring
        signals, and changelog entries. Every claim links back to its source item.
      </div>
    </div>
  );
}

export function Ask() {
  const [exchanges, setExchanges] = useState<AskResponse[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const showEmpty = exchanges.length === 0 && !pending && !pendingQuestion;

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [exchanges, pending, pendingQuestion]);

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  const sendQuestion = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;

    setPending(true);
    setPendingQuestion(trimmed);
    setInput("");

    try {
      const response = await api.postAsk({ question: trimmed });
      setExchanges((prev) => [...prev, response]);
    } finally {
      setPending(false);
      setPendingQuestion(null);
    }
  }, [pending]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendQuestion(input);
    }
  }

  return (
    <div className="ask-page">
      <header className="ask-page__header">
        <p className="mono-label">Pull Layer</p>
        <h1 className="ask-page__title font-display">Ask the Intel</h1>
        <p className="ask-page__subtitle">
          Every answer is cited back to the source it came from.
        </p>
      </header>

      <div className="ask-page__scroll">
        {showEmpty ? (
          <SuggestedQuestions onSelect={(question) => void sendQuestion(question)} />
        ) : (
          <AskTranscript
            exchanges={exchanges}
            pending={pending}
            pendingQuestion={pendingQuestion}
          />
        )}
        <div ref={bottomRef} />
      </div>

      <div className="ask-page__input">
        <div className="ask-input__wrap">
          <textarea
            ref={textareaRef}
            className="ask-input__field"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about competitors, signals, or market trends…"
            rows={1}
            disabled={pending}
          />
          <button
            type="button"
            className="ask-input__send"
            onClick={() => void sendQuestion(input)}
            disabled={!input.trim() || pending}
            aria-label="Send question"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M6 9.5V2.5M3 5.5L6 2.5L9 5.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
        <p className="ask-input__hint">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}

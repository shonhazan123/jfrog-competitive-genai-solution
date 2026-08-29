import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./AskCta.css";

export function AskCta() {
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  const submit = () => {
    const q = value.trim();
    navigate(q ? `/ask?q=${encodeURIComponent(q)}` : "/ask");
  };

  return (
    <section className="ask-cta">
      <span className="ask-cta__icon" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.9-.9L3 21l1.9-5.1A8.38 8.38 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z" />
        </svg>
      </span>
      <h2 className="ask-cta__title">
        Have questions about the recent research?
      </h2>
      <p className="ask-cta__lede">
        Chat with the agent and it will dig through everything we've gathered to
        surface the intel that answers you — with sources.
      </p>
      <form
        className="ask-cta__bar"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          type="text"
          className="ask-cta__input"
          placeholder="Ask anything about the competitors or the market…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          aria-label="Ask the agent a question"
        />
        <button type="submit" className="ask-cta__btn">
          Ask →
        </button>
      </form>
    </section>
  );
}

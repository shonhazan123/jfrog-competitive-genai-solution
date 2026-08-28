import { beforeEach, expect, test } from "vitest";
import {
  appendExchange,
  clearHistory,
  loadHistory,
  MAX_INTERACTIONS,
  type ChatTurn,
} from "./chatHistory";

beforeEach(() => {
  clearHistory();
});

test("an appended exchange is persisted and reloads", () => {
  const user: ChatTurn = { role: "user", content: "hello" };
  const assistant: ChatTurn = { role: "assistant", content: "hi", citations: [] };
  appendExchange(user, assistant);
  expect(loadHistory()).toEqual([user, assistant]);
});

test("history keeps only the last 10 interactions, oldest dropped, order preserved", () => {
  for (let i = 0; i < 12; i++) {
    appendExchange(
      { role: "user", content: `q${i}` },
      { role: "assistant", content: `a${i}` },
    );
  }
  const history = loadHistory();
  expect(history.length).toBe(MAX_INTERACTIONS * 2);
  // the two oldest exchanges (q0/a0, q1/a1) were popped
  expect(history[0]).toEqual({ role: "user", content: "q2" });
  expect(history[history.length - 1]).toEqual({ role: "assistant", content: "a11" });
});

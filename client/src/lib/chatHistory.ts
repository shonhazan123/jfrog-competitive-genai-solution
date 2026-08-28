export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  citations?: unknown[];
};

export const MAX_INTERACTIONS = 10;
const STORAGE_KEY = "chatHistory";

export function loadHistory(): ChatTurn[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as ChatTurn[]) : [];
  } catch {
    return [];
  }
}

function save(history: ChatTurn[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {
    /* localStorage unavailable (private mode / quota) — memory is best-effort */
  }
}

export function appendExchange(user: ChatTurn, assistant: ChatTurn): ChatTurn[] {
  const next = [...loadHistory(), user, assistant];
  // FIFO: cap at the last MAX_INTERACTIONS exchanges (2 turns each), dropping oldest.
  const trimmed = next.slice(-MAX_INTERACTIONS * 2);
  save(trimmed);
  return trimmed;
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

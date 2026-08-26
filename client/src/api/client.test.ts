import { describe, test, expect, vi } from "vitest";
import { api, setMode, FIXTURES } from "./client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

const EMPTY_LIST = { items: [], total: 0, cursor: null };

test("fixture mode resolves without any network call", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  const data = await api.getSignals({ persona: "sales" });
  expect(fetchSpy).not.toHaveBeenCalled();
  expect(data.items.length).toBeGreaterThan(0);
});

test("live mode calls the contract path", async () => {
  setMode("live");
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(EMPTY_LIST));
  await api.getSignals({ persona: "sales" });
  expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining("/signals?persona=sales"), expect.anything());
});

test("every endpoint has a fixture so the client runs with no backend", () => {
  for (const name of Object.keys(api)) expect(FIXTURES[name]).toBeDefined();
});

test("an error response surfaces the contract's readable message", async () => {
  setMode("live");
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    jsonResponse({ error: { code: "bad_config", message: "Weight must be a number" } }, 422));
  await expect(api.putMateriality({})).rejects.toThrow("Weight must be a number");
});

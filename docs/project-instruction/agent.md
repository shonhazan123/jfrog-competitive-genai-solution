# Agent graphs — ask

## Ask graph

Flow: `classify_intent → tool_loop (max 4) → grounding_gate → answer | refuse`.

Code: `backend/agent/graphs/ask/graph.py`. Logs under `agent.ask` and
`app.ask_service` (`ask.request.start` / `ask.request.done`, `ask.llm.invoke`).

## Viewing logs

```bash
docker compose logs -f api worker
```

Set verbosity with `LOG_LEVEL=DEBUG` in `.env` (default `INFO`). At DEBUG you also
see which model each `get_model(role)` call builds (`agent.llm`).

## Typical failure signals

| Log line | Meaning |
|---|---|
| `run.failed` | Background run job threw — see traceback |
| `ask.grounding.refuse` | No hits or citations not grounded |

# Agent graphs — interpret and ask

## Interpret graph

Flow: `sanitize → extract → verify → (repair | crossref | quarantine) → contextualize`.

Code: `backend/agent/graphs/interpret/graph.py`, nodes under `backend/agent/nodes/`.

Each node emits structured **INFO** lines via `agent.log.step` under logger names
`agent.sanitize`, `agent.extract`, `agent.verify`, `agent.repair`,
`agent.quarantine`, `agent.contextualize`, `agent.interpret`. The service bridge
`app.services.agent_service.interpret_capture` logs start/done/quarantine under
`app.agent_service`. Worker batch interpret logs under `worker.jobs`.

Routing after verify is logged as `interpret.route` with `from_node`, `to_node`,
and `verification_ok`.

LLM failures in extract/repair/contextualize log a full traceback at **ERROR**
(`extract.failed`, `repair.failed`, `contextualize.failed`).

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
| `verify.failed` | Quote verification failed; check `failed_quotes` |
| `interpret.route … to_node='repair'` | Retrying extraction with feedback |
| `interpret.route … to_node='quarantine'` | Max repairs exhausted |
| `quarantine` | Capture sent to analyst queue |
| `extract.failed` / `repair.failed` | LLM or schema error — see traceback |
| `run.failed` | Background run job threw — see traceback |
| `ask.grounding.refuse` | No hits or citations not grounded |

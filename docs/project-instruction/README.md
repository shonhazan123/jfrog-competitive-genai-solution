# Project instruction — operational flow

This folder is the operational source of truth for **how the running system works**.
Agents must base logic on these files and update them when behaviour changes.

Design intent (problem, requirements, build plan) stays in [PRD.md](../PRD.md),
[DESIGN.md](../DESIGN.md), and [ARCHITECTURE.md](../ARCHITECTURE.md). The HTTP
shapes live in [API_CONTRACT.md](../API_CONTRACT.md). Implementation plans in
[plans/](../plans/) are historical; do not rewrite them when code diverges — update
this folder instead.

| File | Covers |
|---|---|
| [digests.md](./digests.md) | `GET /digests/{persona}` vs `GET /digests/exec/weekly` |
| [runs.md](./runs.md) | `POST /runs` async progress, `GET /runs/{id}`, human stages |
| [kits.md](./kits.md) | `GET /kits`, KIT rollup, citations, display labels |
| [ask.md](./ask.md) | Ask graph routing, hit accumulation, `POST /ask` bridge |
| [client.md](./client.md) | React client: fixture/live switch, IA-as-data, tokens, SignalCard rule, live-wiring contract drift |

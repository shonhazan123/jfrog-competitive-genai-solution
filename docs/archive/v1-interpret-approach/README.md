# Archive — V1: the Interpret-graph approach

> **Status:** superseded. Nothing in this folder is part of the running system.
> It is kept as the design record of the project's first architecture.

## What V1 was

The first version of this tool was built around a **per-capture Interpret
graph**. Every document that collection fetched was run, one at a time, through
a fixed LangGraph pipeline:

```
sanitize → extract → verify ─┬ pass ──→ crossref → contextualize → END
                             ├ fail ──→ repair → back to verify
                             └ twice ─→ quarantine → interrupt() → analyst review
```

The design's load-bearing ideas were:

- **A verbatim verification gate.** The model was only allowed to *point* at a
  quote; code located that string in the source and cut the stored evidence from
  the source text itself. A claim whose quote could not be found verbatim was
  repaired or dropped. The intent was that no stored assertion could be a
  hallucination — the stored quote was always a substring of the real capture.
- **Element-first ingestion.** Every source (HTML, PDF, RSS, Markdown, JSON) was
  parsed into a common typed element tree before any chunking decision, so a
  comparison-table row was never split in half.
- **An HNSW / pgvector retrieval stack** with a documented HNSW-vs-IVFFlat
  rationale and a deterministic, tradecraft-weighted rerank.
- **Human-in-the-loop quarantine.** When verification failed twice, the graph
  suspended via `interrupt()` and persisted to Postgres; an analyst reviewed the
  extraction in an `analyst_queue` and resumed or rejected it.
- **Wayback backfill.** Five years of competitor positioning history was seeded
  onto a cold machine from the Internet Archive CDX API, so the tool had trend
  depth on day one rather than only going forward from first run.

## Why it was set aside

**V1 was the more rigorous approach, and it was accurate.** The verification gate
in particular produced evidence you could stand behind line by line.

It was set aside for one reason: **it was too slow to produce usable
intelligence inside the assignment's time budget.** Per-capture Interpret runs,
the repair loop, the quarantine/analyst round-trip, and the full ingest→verify
pipeline meant that turning raw collection into a populated set of signals and a
comparison grid took far longer end-to-end than the time available to demo it.
The competitive-intelligence need — *"keep the team updated daily and show how
JFrog compares"* — is better served, on this timeline, by engines that go
straight from a research question to a grounded, sourced answer.

## What replaced it

**Per-surface research engines.** Three agents — Industry, Signals, and
Comparison — each fan out over their own targets, use web search (grounded via
OpenAI citations) and structured sources, gate each hit for relevance, and
persist directly to the ledger. A shared research skeleton runs the targets
concurrently; a chat/Ask agent answers analyst questions over the resulting
ledger with a grounding gate. See the live [`docs/ARCHITECTURE.md`](../../ARCHITECTURE.md).

The retrieval stack (chunking, pgvector index, hybrid retrieval) **survived the
transition** — the chat/Ask agent uses it — so only the *design essays* about it
live here; the working code did not move.

## The honest note the new system carries forward

V1's verbatim gate is **not** exercised by the research-engine path: web-search
findings are stored as grounded *syntheses* with a source URL
(`match_method = 'synthesis'`), not as verbatim spans cut from a re-fetched
page. That is a known gap the current system owns openly rather than one the
docs paper over — re-introducing verbatim verification for the research path is
tracked as future work, not claimed as done.

## Files in this folder

| File | What it is |
|---|---|
| `ARCHITECTURE.v1.md` | The full original architecture document (Interpret graph, verification gate, element-first ingestion, HNSW indexing, Signal loop). Preserved verbatim. |
| `OFFLINE_BACKFILL.md` | The Wayback / offline-backfill operational note. |

The original V1 implementation code (Interpret nodes, quarantine/analyst
human-loop, Wayback backfill) was **removed** from the live tree during the
cleanse; it remains recoverable in git history at the `v1-archived` tag.

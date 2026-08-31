# DESIGN — Solution and build plan

| | |
|---|---|
| **Status** | Shipped — research-engine architecture |
| **Date** | 30 August 2026 |
| **Author** | Shon Hazan |
| **Related** | [PRD.md](./PRD.md) — problem & requirements · [ARCHITECTURE.md](./ARCHITECTURE.md) — code-level design · [archive/v1-interpret-approach/DESIGN.v1.md](./archive/v1-interpret-approach/DESIGN.v1.md) — the superseded first design |

> The original solution design (per-capture Interpret graph, verbatim verification
> gate, element-first ingestion, human-in-the-loop quarantine, Wayback backfill) is
> preserved verbatim in
> [`archive/v1-interpret-approach/DESIGN.v1.md`](./archive/v1-interpret-approach/DESIGN.v1.md).
> It was accurate but too slow to produce usable intelligence in the time budget.
> This document describes what was actually built.

---

## 1. The suggested solution

The CI team needs two things daily: **what changed across the DevSecOps landscape**,
and **how JFrog compares to its main competitors**. The solution is a small,
config-driven workspace that turns those needs into sourced, plain-language verdicts,
and runs — database, API, worker, UI — with one `docker compose up`.

The mechanism is **three per-surface research engines** rather than one monolithic
pipeline:

- **Industry** — sweeps four configurable topic buckets for landscape news.
- **Signals** — sweeps each allowlisted competitor across sub-types (hiring, pricing,
  funding, security advisories), preferring structured sources (job boards, OSV) and
  falling back to web search.
- **Comparison** — fills a competitors × dimensions grid, one cell at a time, with a
  stance (strong/moderate/weak) and evidence.

Each engine shares one concurrency skeleton, gates every finding for relevance
against its cited source, and persists to a common ledger. A **chat/Ask** agent then
answers analyst questions over that ledger with a grounding gate that refuses when
the evidence does not support an answer. Full design in [ARCHITECTURE.md](./ARCHITECTURE.md).

**Why this shape.** The competitive-intelligence need is answered faster by engines
that go from a research question straight to a grounded answer than by a per-document
pipeline that must fetch, parse, extract, verify and contextualise every capture
before anything reaches the analyst. The trade-off is deliberate and stated in §4.

---

## 2. What runs today (build-and-demo now)

| Capability | State |
|---|---|
| One-command stack (db · api · worker · client) | ✅ |
| Config-driven entities, sources, scoring, routing (YAML → seeded, runtime-editable) | ✅ |
| Three research engines producing signals + a comparison grid | ✅ |
| Relevance gate tied to the cited source URL; closed-enum entities (no hallucinated competitors) | ✅ |
| Materiality scoring with a persisted, on-card arithmetic breakdown | ✅ |
| Retrieval (hybrid RRF + deterministic rerank) over the ledger | ✅ |
| Chat/Ask agent with a grounding gate and refusal-as-an-edge | ✅ |
| Live snapshot diff of tracked comparison pages → `ClaimVersion` history | ✅ |
| Privilege isolation: `app` never imports LLM libraries (mechanically checkable) | ✅ |
| Digest assembly + email templates | ⚠️ wired, not yet demonstrated end-to-end |

## 3. What I'd invest in next (future, with more time)

Ordered by value to the CI team:

1. **Verbatim verification for the research path.** Today's research evidence is a
   grounded *synthesis* carried with a real source URL, not a span cut from a
   re-fetched page. Re-introducing the v1 verification gate for at least the
   comparison grid is the highest-value hardening. (This is the one design promise the
   current system deliberately does not yet keep — see [ARCHITECTURE §3](./ARCHITECTURE.md).)
2. **Corroboration & clustering** — collapse one event arriving from several framings
   into one signal so the digest isn't four copies of one story.
3. **Reliable `occurred_at` extraction** so recency scoring and "daily" freshness are real.
4. **Full competitor coverage** — ensure GitLab / Harbor / Azure Artifacts return
   results, and distinguish "silent" from "starved" so negative reporting stays honest.
5. **Digest end-to-end** — a demonstrated per-persona daily run with delivery.
6. **Observability & cost control** — per-stage token accounting and funnel metrics.

## 4. Challenges & pitfalls encountered

- **The accuracy/speed trade-off.** The v1 Interpret pipeline produced verifiable,
  verbatim-sourced evidence but was too slow to populate the surfaces within the time
  budget. Choosing the research engines bought speed and coverage at the cost of the
  verbatim gate — an explicit, documented trade, not an accident. This is the single
  most important thing to be honest about when presenting.
- **"Grounded" is not "verified."** OpenAI web-search returns real citation URLs, so
  findings are grounded, but nothing locally checks that the URL's page supports the
  synthesized quote. Labeling this honestly (`match_method = 'synthesis'`) matters
  more than hiding it.
- **A model that must return something will invent something.** Gates must bless the
  empty case, and the retriever must be allowed to return nothing — otherwise the
  system manufactures false coverage.
- **Collection starvation vs. genuine silence.** An empty result for a competitor can
  mean "no news" or "collection failed"; conflating them makes the "no material
  change" report untrustworthy.
- **Documentation drift.** A large v1 design existed before the pivot; keeping the
  live docs describing only the shipped system (and archiving the rest) is itself part
  of the engineering, not an afterthought.

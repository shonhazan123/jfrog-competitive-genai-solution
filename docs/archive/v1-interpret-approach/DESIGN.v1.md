# DESIGN — Competitive Intelligence System for JFrog

| | |
|---|---|
| **Status** | Approved · pre-implementation |
| **Date** | 25 August 2026 |
| **Author** | Shon Hazan |
| **Related** | [PRD.md](./PRD.md) — problem, users, requirements |

This document covers architecture, data model, pipeline mechanics, the boundary between
deterministic code and model inference, security, the build plan, and known pitfalls.
Requirement identifiers (R1.1, R4.2 …) refer to [PRD.md §5](./PRD.md#5-requirements).

---

## 1. Architecture overview

Three loops write into one store. Every surface reads from that store and **nothing in the
presentation layer ever reaches the internet.**

```
                   ┌──────────────────────────────────────────────┐
  SIGNAL LOOP      │  feeds · JSON APIs · article pages           │
  hourly           │  → capture → normalise → classify            │──┐
                   │  → score → route                             │  │
                   └──────────────────────────────────────────────┘  │
                                                                     ▼
                   ┌──────────────────────────────────────────────┐ ┌─────────────┐
  POSITION LOOP    │  tracked pages: comparison · pricing ·       │ │             │
  daily            │  docs · release notes                        │ │ THE LEDGER  │
                   │  → snapshot → structural diff → semantic     │►│  Postgres   │
                   │    diff → claim extraction → version trail   │ │             │
                   └──────────────────────────────────────────────┘ │ immutable   │
                                                                    │ captures +  │
                   ┌──────────────────────────────────────────────┐ │ signals +   │
  DELIVERY LOOP    │  digest assembly per persona → render →      │ │ claims +    │
  daily / weekly   │  SMTP → delivery log                         │◄┤ evidence    │
                   └──────────────────────────────────────────────┘ └──────┬──────┘
                                                                           │
  SURFACES         Today · Divisions · Comparison · Competitors→Us · Industry · Ask · Settings
```

### The seven layers

| # | Layer | Responsibility | Mechanism | Model? |
|---|---|---|---|---|
| 1 | **Collect** | Fetch each source on its cadence | httpx + feedparser · robots check · token-bucket rate limit · ETag | — |
| 2 | **Capture** | Persist raw bytes, immutably | content-hashed blob + row | — |
| 3 | **Normalise** | Page → clean text + structured region | trafilatura for articles · CSS selectors for tracked pages | — |
| 4 | **Detect** | Decide *whether* something changed | 304 → raw hash → normalised hash → structural diff | — |
| 5 | **Interpret** | Decide *what it means* | four staged calls, strict schemas, quote gate | **yes** |
| 6 | **Score** | Decide *who cares, and how much* | explainable weighted sum over extracted labels | — |
| 7 | **Deliver** | Put it where a human will see it | Jinja + SMTP · React · grounded Q&A | **yes** |

**The model touches two layers of seven.** Detection, scoring and routing are deterministic
because they must be auditable and tunable. This is a design position, not an omission — see
§6.

### Why the presentation/collection split matters twice

The rule *"the presentation layer never touches the internet"* is stated once and earns two
separate arguments:

1. **Auditability.** Everything a user sees came from a stored, hashed, timestamped capture.
2. **Security.** It is precisely the privilege-isolation boundary recommended against
   indirect prompt injection — see §8.

---

## 2. Deployment topology

Four containers, one command (N1).

| Container | Contents | Notes |
|---|---|---|
| `db` | Postgres | Volume-backed |
| `api` | FastAPI | Read paths + manual trigger endpoint + Ask |
| `worker` | APScheduler + pipeline | Real cron. Same code path the manual trigger invokes (R6.1, R6.2) |
| `web` | React (Vite) | Static build served alongside |

The scheduler runs genuinely and continuously in `worker`. The manual trigger calls the same
job function — it is a convenience, not a substitute. **This distinction is stated plainly in
the README rather than glossed over**; a scheduler that only appears to run is the one thing
that would not survive scrutiny.

---

## 3. Data model

### Principles

1. **Immutable capture, mutable interpretation.** Re-analysis is cheap; re-collection is
   impossible, because the page has already changed. Storing only a model's summary discards
   the evidence and forecloses ever re-running a better prompt over history.
2. **Every generated sentence traces to a verbatim quote with character offsets** in a stored
   capture (N5, R3.3).
3. **Claims have a lifecycle; signals have a half-life.** Different semantics, different
   tables.
4. **Source reliability and information credibility are graded independently.**

### Tables

**`entity`** — competitors, JFrog itself, and an `industry` pseudo-entity for the DevSecOps
field lane. Carries `tier` (1 = deep coverage, 2 = news only) and aliases for matching.

**`source`** — a monitored *thing*, not a document. `url`, `entity_id`, `kind`
(`atom` | `rss` | `html_page` | `api` | `sitemap`), `mode` (`feed` = expect new items,
`snapshot` = expect this page to change), `reliability_grade` (A–F), `is_primary`,
`check_frequency`, `robots_allowed`, `requires_js`, `etag`, `last_checked`.

**`raw_capture`** — **append-only, never mutated.** `source_id`, `fetched_at`, `http_status`,
`content_hash`, `blob_path`, `extracted_text`, `extraction_method`, `provenance`
(`live` | `archive`). The provenance root for the entire system.

**`document`** — the normalised read: `title`, `published_at`, `canonical_url`, `clean_text`,
`lang`, `capture_id`.

**`signal`** — a dated event. `document_id`, `entity_id`, `signal_type` (the nine-value enum),
`headline`, `occurred_at`, `cluster_id`, `materiality_sales`, `materiality_product`,
`materiality_exec`, `so_what_sales`, `so_what_product`, `so_what_exec`, `score_breakdown`
(JSONB).

**`claim`** — the durable competitive assertion.

```
claim
  id
  subject_entity_id     -- who the claim is ABOUT
  asserting_entity_id   -- who MAKES the claim
  claim_text
  claim_type            -- capability | pricing | positioning | security
  capability_tags[]     -- closed vocabulary
  status                -- active (v1 uses this value only)
  reliability_grade     -- A–F, from the source
  credibility_score     -- 1–6, from corroboration
  first_seen_at
  last_confirmed_at
```

**The two entity references are the most consequential column choice in the schema.**
*"Sonatype asserts that JFrog has hidden costs"* is `subject = JFrog`,
`asserter = Sonatype`. That asymmetry is what makes the "what competitors say about us" view
possible (R5.3), and that view is the most differentiated screen in the product.

**`claim_version`** — append-only diff trail: `claim_id`, `old_text`, `new_text`,
`changed_at`, `change_kind` (`new` | `substantive` | `cosmetic` | `removed`), `evidence_id`.
Deliberately thin — no lifecycle state machine, no re-confirmation scheduling, no
contradiction resolution (see [PRD §10](./PRD.md#10-scope)).

**`evidence`** — joins a claim or signal to a capture with **the verbatim quote and its
character offsets**. This is what makes citation verifiable rather than asserted.

**`page_snapshot`** — Position-loop state: `source_id`, `captured_at`, `text_hash`,
`structural_fingerprint`, `normalised_text`.

**`battlecard_row`** — derived, not authored: `dimension`, `jfrog_position`,
`competitor_position`, `supporting_claim_ids[]`, `last_changed_at`.

**`analyst_action`** — `target_type`, `target_id`, `actor`, `action`
(`confirm` | `reject` | `edit` | `suppress`), `reason`, `at`. The labelled dataset,
accumulating from day one (R7.1).

**`digest_run` / `delivery`** — what was assembled, sent, to whom, when. Supports audit and
the "since you last looked" behaviour (R7.5).

---

## 4. Collection

### Fetcher abstraction

```
Fetcher (interface)
├── StaticFetcher    httpx · conditional GET · rate limit · robots     [built]
└── BrowserFetcher   raises NotImplementedError with a clear message   [stub]
```

Every source carries `requires_js`. Sources needing rendering surface a visible
*"blocked: requires browser rendering"* state rather than silently returning an empty page
(R1.7).

**No headless browser ships in v1.** The high-value sources were verified as static HTML
before this decision was made — the choice is deliberate source selection, not avoidance. The
adapter seam exists; adding Playwright is one compose service and one class.

### Politeness and its second dividend

Per-domain token bucket, an honest User-Agent naming the tool with a contact address,
`robots.txt` checked and recorded, and conditional GET on every snapshot source.

Conditional GET does double duty: it reduces load on the competitor's infrastructure, **and a
`304` is definitive proof of no change** — eliminating an entire class of diff false positives
before any diff runs (R1.4, R2.1).

### Historical backfill (R1.5)

The cold-start problem is real: a system whose headline capability is change detection has
nothing to show on a fresh machine, and this tool will be demonstrated once or twice rather
than run for months.

The solution is to backfill rather than accumulate.

```
1. Wayback CDX API, collapse=digest
     → returns only versions where content actually changed
2. Fetch each: /web/<timestamp>id_/<original-url>
     → the "id_" suffix yields ORIGINAL raw HTML,
       without the archive's injected toolbar
3. Store as raw_capture, fetched_at = archive timestamp,
   provenance = "archive"
4. Run the identical pipeline as a live capture
```

**Verified 25 August 2026:** the Sonatype/JFrog comparison page has **19 distinct archived
content versions spanning February 2021 to May 2026**, growing from 20KB to 38KB — five years
of accumulating claims against JFrog, publicly retrievable.

Two properties make this the first thing built:

- **Backfill is not a separate code path.** Same pipeline, different fetcher. It therefore
  exercises the live path nineteen times before the first scheduled run — effectively free
  integration testing.
- The system is meaningfully populated the moment `docker compose up` completes (N2).

**Documented caveats:** archive coverage is sampled rather than continuous; some pages are
not archived; archived pages can miss JavaScript-rendered content; applies only to
`snapshot`-mode sources.

### The Signal loop — where most of the daily volume comes from

The Position loop above is the more novel half of the system and consequently gets more words.
The Signal loop is the larger half by volume, and this section gives it equal treatment because
under-describing it is how a reader concludes the product is only about tracked pages.

**Three collection modes, not one.** Sources declare a `mode`, and the mode determines the
entire downstream path:

| Mode | Meaning | Change means | Sources |
|---|---|---|---|
| `feed` | Expect **new items** over time | A new entry appeared | Atom/RSS release feeds, blogs, press, standards bodies |
| `api` | Expect a **structured query result** | A new record matches our filter | OSV, GHSA, CISA KEV, Greenhouse/Lever, SEC EDGAR |
| `snapshot` | Expect **the same page** to change | The page's content differs | Comparison pages, pricing, homepages, customer-logo walls |

`feed` and `api` sources never run the structural-diff cascade — there is no "before" to diff
against. Their novelty test is identity-based: has this entry ID, advisory ID, job ID or
accession number been seen before? That check is a database lookup, not a comparison, and it is
both cheaper and more reliable than diffing.

**Bullet-level classification is the decision that keeps the digest usable.** A release note is
not one signal. Nexus 3.95 might carry forty bullet points of which two are material capability
changes and thirty-eight are bug fixes. The element parser already produces one `list_item`
element per bullet, so classification runs at bullet level and the release becomes *n* candidate
signals rather than one. Treating a release as atomic is the most common way a competitor
tracker degrades into noise — the digest fills with "Competitor released version X" and the
reader learns nothing.

**Clustering runs after classification, not before.** One real-world event — a competitor
release — typically generates a release feed entry, a blog post, two press articles and a Hacker
News thread. Those become **one signal with five evidence links**, keyed on entity, capability
tags, a date window, and title similarity. This single behaviour does more for perceived digest
quality than any amount of summarisation polish, because the alternative is five cards that say
the same thing.

**The industry lane runs through the identical pipeline with a different entity.** Regulatory
and standards sources — EU CRA, NIS2, NIST SSDF, OpenSSF, SLSA, Sigstore, CNCF — are ordinary
`feed` sources whose entity is the `industry` pseudo-entity. No special-casing. They classify as
`market_regulatory`, they route predominantly to executives, and they are the reason the weekly
roll-up answers *"is the market moving toward us or away from us"* — a question competitor
tracking alone cannot address.

**Structured API sources bypass most of the pipeline and are better for it.** An OSV record
arrives already typed: affected package, version ranges, severity, references, dates. There is
nothing to extract and nothing to hallucinate. The model's only job is the per-persona so-what.
These sources deliver the highest signal quality in the system at the lowest cost, which is
worth stating plainly because the instinct in a GenAI project is to route everything through a
model.

**One handling rule encoded in the product, not just in policy.** `security_trust` signals about
competitor vulnerabilities carry a **caution flag** in the sales view. A competitor's CVEs are
legitimate competitive intelligence; leading a sales conversation with them is reputationally
hazardous, especially for a vendor whose own business is security. The generated so-what is
framed around capability posture rather than the individual advisory, and the flag is visible on
the card.

---

## 5. Change detection

> **Diffing is a funnel, not a step. The model sits at the bottom — and that is an accuracy
> decision before it is a cost decision. The fewer items reach the model, the fewer chances
> it has to be wrong.**

| Layer | Mechanism | Eliminates | Cost |
|---|---|---|---|
| 0 | Conditional GET | Unchanged pages, definitively | free |
| 1 | Raw content hash | Byte-identical responses | free |
| 2 | **Normalise, then hash** — strip navigation, footers, scripts, analytics identifiers, CSRF and session tokens, timestamps, rotating testimonials | **~80% of cosmetic noise — the highest-leverage step in the system** | free |
| 3 | **Structural diff** — extract the semantic region via selector into a normalised structure; diff the structure | Layout churn, reordering, styling changes | near-free |
| 4 | Semantic diff (model), survivors only | Genuinely ambiguous cases | tokens, on ~1–2% |

**Layer 3 deserves emphasis.** Diffing the *structure* of a comparison table rather than its
text produces output that is already insight-shaped:

```
row "Malware detection" · cell "JFrog"
   "Limited"  →  "Very limited, not proactive"
```

No model is required to produce that, and it is more precise than anything a model would
return. The model's only job is to say what it *means* — not to find it.

---

## 6. The model / code boundary

This is the design decision most likely to be challenged, so the reasoning is set out in full.

> **The model decides *what this is*. Configuration decides *who that matters to*. Code
> multiplies.**

The model's primary job is not prose. It is **converting unstructured text into typed
fields**. Scoring is arithmetic over those model-assigned labels — so the model does determine
who cares, indirectly, through classification rather than through emitting a number.

### Interpret is four stages

| Stage | Purpose | Model | Volume/day | Untrusted input |
|---|---|---|---|---|
| **1 · Extract** | Text → typed facets: signal type, subject/asserting entity, capability tags, claim candidates, verbatim quotes with offsets | small | ~100 | **yes — quarantined** |
| **2 · Cross-reference** | New / restatement / update / contradiction versus existing claims | small | ~40 | no — *v1 ships the deterministic half only* |
| **3 · Contextualise** | Per-persona "so what", written against JFrog's own position from the ledger | large | ~15 | no |
| **4 · Verify** | String-match every quote against the stored capture | code | all | — |

Stage 1 is constrained hard: temperature 0, enforced JSON schema, **closed enumerations** so
no free-text entity can be invented, and every claim candidate must carry a verbatim quote.

Stage 2 is hybrid by design: deterministic retrieval (SQL on subject entity and capability
tags, optionally embedding similarity) narrows to roughly five candidate claims, and the
model adjudicates only those. **Embeddings act as a candidate generator for a comparison, not
as general retrieval.** The model never faces the ledger — it faces five rows and one
question.

**v1 ships the deterministic half of Stage 2 and defers the model half** (R3.5 ships, R3.6 is
roadmap). Deduplication and clustering run on URL hash, title similarity, and subject-entity
plus capability-tag matching. This yields most of the clustering benefit for a fraction of the
build, and it is the correct thing to cut because the relationship it cannot determine —
restatement versus contradiction — is exactly the judgement an analyst is already reviewing
in the queue.

Stage 3 handles the nuance configuration cannot express. Configuration knows that positioning
claims matter to sales. It cannot know that *this particular* pricing change matters because
it targets a specific segment. That judgement is the "so what", and it is the model's.

Which yields the clean division:

> **Who receives it → deterministic policy. Why they should care → model judgement.**

### Scoring

Composite and explainable, over model-extracted labels: source reliability grade; signal-type
base weight per persona; entity tier; change kind; **whether JFrog is named** (large
multiplier — a competitor discussing *us* is categorically more material); corroboration
count; watchlist term hits; novelty against the ledger; recency decay.

**Worked example** — Sonatype's comparison page changes one cell:

```
model extracts:  signal_type=positioning_messaging · subject=JFrog
                 asserter=Sonatype · capability=malware_detection
                 change_kind=substantive
                 quote="Very limited, not proactive" @ offset 4471

routing.yaml:    positioning_messaging → { sales: 3, product: 1, exec: 1 }
                 modifiers: subject_is_jfrog ×2.0 · tier_1 +15 · substantive +20

code computes:   sales = (3→30) × 2.0 + 15 + 20 = 95   → top of the sales digest
                 exec  = (1→10)       + 15 + 20 = 45   → below threshold, dropped
```

The model said *"this is a positioning claim by Sonatype about JFrog's malware detection."*
Configuration said *"positioning claims about us are what sales lives on and what executives
can ignore."* Nobody asked a model to rate importance.

### Why not simply ask the model to score

1. **Re-scoring is free.** Change one weight and the entire ledger re-ranks in a SQL update.
   Model-emitted scores would require re-inferring every record. This is the decisive
   argument.
2. **Reproducibility.** Same input, same score, permanently. Model-emitted numbers drift
   between runs and across model versions, which makes A/B evaluation impossible.
3. **Tunable by a non-engineer.** A form field rather than prompt engineering.
4. **It reflects the discipline.** Intelligence practice separates analysis from
   dissemination policy. Who receives what is an organisational decision, not an analytical
   one; encoding it in a prompt conflates the two.

> **A score the analyst cannot tune is a score she will learn to ignore.** Deterministic
> weights turn disagreement into a settings change instead of a loss of faith.

**One bounded valve (R4.4):** Stage 3 may emit `llm_relevance_adjustment ∈ [-1, +1]` with a
written reason, applied on top of the configured score, logged and displayed in the
breakdown. The model gets a vote, never a veto.

### Retrieval boundary

> **This is not RAG over documents. It is retrieval over a structured ledger, with documents
> attached as evidence.**

Signals and claims are already structured records. Chunking them back into prose and
embedding them would destroy the structure a model was paid to produce.

The system therefore treats its content as **three corpora with different handling**, rather
than as one indexable pile:

| Corpus | Size | Chunked | Embedded | Retrieved how |
|---|---|---|---|---|
| **A · Recent signals** (7–14 days) | 40–80 records | no | no | passed whole into context |
| **B · The claim ledger** | hundreds–thousands | no — one claim, one vector | yes | hybrid: SQL filter + vector |
| **C · Document bodies** | thousands of chunks | yes, element-wise | yes | hybrid, as evidence lookup |

**For the daily brief — corpus A — v1 deliberately performs no retrieval at all.** A day's
signals are 40–80 structured records; passing all of them beats retrieving a top-k subset,
and it removes an entire class of retrieval-recall failure. A vector store exists in the
system and the brief does not call it. That is a decision, not an absence.

Corpora B and C are indexed in pgvector alongside a `tsvector` column in the same table, and
served by a shared retrieval service with three presets — candidate generation for the
Interpret graph's cross-reference stage, evidence for the Ask surface, and "related evidence"
panels in the interface. Full mechanics in [ARCHITECTURE.md §6–8](./ARCHITECTURE.md).

The governing rule: **embed what must be searched by meaning; index what can be searched by
value.** Entity, date, signal type and reliability grade are columns with btree indexes. No
date is ever embedded.

### Grounding and anti-hallucination

Published evaluation of deep-research systems finds their dominant failure is **not fabricated
sources but inaccurate paraphrase of real ones**. That is precisely the failure that ruins a
competitive claim.

The defence is structural rather than prompted: every claim carries a verbatim quote with
character offsets, and **Stage 4 string-matches it against the immutable capture in plain
Python**. A record whose quote does not verify never reaches a digest — it lands in the
analyst queue, flagged. This is testable, and the failing test is more persuasive in review
than any prompt.

The Ask surface follows the same rule: it answers only from the ledger, renders the evidence
it used, and **refuses when the ledger cannot support an answer** (R6.5). Empty retrieval
refuses without calling the model. Graph routing and the `POST /ask` package boundary are in
[project-instruction/ask.md](./project-instruction/ask.md).

---

## 7. Configuration and modularity

The team must be able to tune coverage without engineering involvement (R4.3, R7.3). This is
also the answer to *scalable* in the brief: adding a competitor is a configuration change,
not a code change.

**Rule: anything an analyst might tune is data, not code.**

| Artifact | Controls |
|---|---|
| `entities.yaml` | Competitors, tiers, aliases |
| `sources.yaml` | URLs, kind, reliability grade, cadence, `requires_js` |
| `signal_types.yaml` | The taxonomy and its trigger terms |
| `routing.yaml` | signal_type × persona relevance matrix |
| `materiality.yaml` | Scoring weights and modifiers |
| `watchlist.yaml` | Free-text terms of current interest |
| `prompts/*.md` | Versioned prompt files — never inline strings |

Seeded into Postgres on boot; the interface edits weights, watchlist and source enable/disable
directly; configuration is exportable back to YAML so it stays reviewable and diffable.

**Stated limit, rather than hidden.** Adding a *source* is configuration. Adding a new
*extraction shape* — a comparison table with a different DOM structure — requires a parser.
Unsupported layouts enter an explicit "needs a parser" state rather than failing silently or
extracting garbage. Naming the boundary of self-service is more credible than implying there
isn't one.

---

## 8. Security

Untrusted public content flows into a model pipeline, at a software supply chain security
company. This section is held to a correspondingly higher standard.

**Privilege isolation** is the pattern adopted: a *quarantined* component reads untrusted
content but holds no tools and takes no actions; a *privileged* component holds tools but
never reads raw untrusted content — only structured output from the quarantined one.

**This falls out of the architecture at no additional cost.** Interpret Stage 1 *is* the
quarantined model: it reads scraped pages and emits typed JSON only. Every presentation
surface reads solely from the ledger and never touches the network (N4).

| Threat | Control |
|---|---|
| Indirect prompt injection in page content | Privilege isolation; Stage 1 holds no tools and its output is schema-constrained |
| Injected instructions surviving into output | Closed enumerations; no free-text entity or URL may be emitted |
| Hidden payloads (off-screen text, comments, EXIF) | Sanitisation before the model: strip markup, comments, hidden elements, metadata |
| Ledger poisoning via a compromised source | Source reliability grading; corroboration requirements; analyst confirmation before publish |
| Exfiltration via model output | The model has no network access and no tools; output is rendered, never executed or fetched |
| Fabricated or distorted claims | Stage 4 verbatim quote verification against the immutable capture |

**Secrets:** API keys and SMTP credentials via environment variables only; `.env.example`
committed, `.env` never. No scraped third-party content is committed to the repository —
fixtures are minimal and clearly labelled.

---

## 9. Build plan

**Budget:** ~20 productive hours, of which **2 hours are README, diagram, screenshots and
demo script** — graded deliverables, not overhead. **~18 hours of build.**

Sequenced by risk, not by layer: the highest-value, highest-uncertainty component is built
first.

### Day 1 — prove the hard part

| Hours | Work |
|---|---|
| 0.5 | Repo skeleton, compose (db · api · worker · web), `.env.example` |
| 1.0 | Schema, migrations, YAML→DB seed loader |
| 1.5 | Collector: static fetcher, robots, conditional GET, feed parsing |
| **2.0** | **Wayback backfill + structural extraction of the comparison table** |
| 2.0 | Diff cascade → writes `claim` + `claim_version` |
| 1.0 | Buffer |

> **Milestone: `docker compose up` produces a database containing five years of real
> Sonatype-versus-JFrog claim history.** If everything afterwards went wrong, this alone is
> defensible. That is why it is first.

### Day 2 — the pipeline end to end

| Hours | Work |
|---|---|
| 2.0 | Interpret Stage 1 (typed extraction) + Stage 4 (quote verification gate) |
| 1.5 | Stage 3 contextualisation — per-persona "so what" |
| 1.0 | Deterministic scoring + breakdown |
| 1.0 | Live signal loop: feeds for four shallow competitors + the industry lane |
| 1.5 | Scheduler in `worker` + manual trigger endpoint |
| 1.0 | Buffer |

> **Milestone: scheduled, end to end, producing scored and cited signals.** Backend complete.

### Day 3 — surface and story

| Hours | Work |
|---|---|
| 3.0 | React: card component, grid, routing, five query variants |
| 1.0 | Ask surface — grounding, refusal, citation rendering |
| 1.0 | Email template, SMTP, a real send |
| 1.0 | Settings screen |
| **2.0** | **README, architecture diagram, screenshots, demo script** |

**Known risk:** three hours for the interface is aggressive. It works only because screens
②③④⑤ are one component with different queries. **Build it plain and correct; style it from
the buffer.**

### Cut list — in priority order, decided in advance

1. Settings → read-only; configuration edits become YAML + reseed
2. Industry → a filter on Divisions rather than its own screen
3. Ask surface → cut entirely (most commoditised; cheapest to lose)
4. Email → render the digest in-app plus one manual send proving SMTP works
5. Executive persona → ship Sales and Product; document the third

**Never cut:** historical backfill · Comparison and Competitors→Us · quote verification · the
real scheduler · the README. Those five are the argument; everything else is supporting
evidence.

### Interface

```
① Today            status strip · top signals · what changed
② Divisions        Sales / Product / Exec — card grid, filtered by competitor
                   and signal type, with the four analyst actions
③ Comparison       JFrog vs competitor by dimension, cited, change-flagged
④ Competitors→Us   what they claim about JFrog, with history
⑤ Industry         DevSecOps field news
⑥ Ask              grounded query over the ledger — cites, and refuses
⑦ Settings         sources, weights, watchlist, robots compliance
```

**The card** answers three questions, always in this order:
**What changed? → Why do I care? → How do I know?**
Verbatim quote never paraphrased; diffs rendered as `was → now` rather than as a code diff;
score breakdown collapsed but not hidden; grades explained by tooltip; only the current
persona's "so what" displayed.

**Three low-cost, high-effect mechanics:** a persistent status strip (`Last run · sources ·
signals · next run · [Run now]`) that makes the automation legible; *"since you last looked"*;
and empty states that report surveillance rather than absence — *"No pricing changes for
Sonatype in 30 days. Checked 14 times."*

---

## 10. Evaluation

Designed, not built in v1 — and deliberately not claimed as built.

**Golden set.** 50–100 manually labelled items spanning all nine signal types and both
change and no-change cases, drawn from the backfilled archive history — which is why backfill
matters twice.

**Measures.** Extraction field accuracy; **quote verification pass rate** (measurable from day
one, since it is enforced in code); classification accuracy against labels; routing precision
per persona; change-detection precision and recall, with cosmetic-versus-substantive as the
hard case; digest precision-at-budget.

**How feedback becomes labels.** Every analyst confirm/reject/edit/suppress writes an
`analyst_action` row. Rejections are labelled false positives; edits capture the delta
between generated and correct output — the most valuable signal available, because it shows
not merely *that* the system was wrong but *how*. Those rows become the training and
evaluation corpus for weight learning.

**Stated honestly:** v1 ships the collection mechanism for this data, not measured accuracy
figures. Claiming measured precision without the harness would be the same category of
unfounded confident assertion the system exists to prevent.

---

## 11. Pitfalls and challenges

For the presentation. These are real, and several were hit during design.

**Half the brief is invisible.** "Latest news" and "how JFrog compares" look like one
requirement and are two, with different clocks. A feed architecture cannot produce a
comparison. This was the first design trap and the one that shaped everything.

**The cold-start problem nearly sank the central feature.** A change detector demonstrated
twice has no history. Discovered mid-design; resolved by archive backfill rather than by
dropping the feature.

**Cosmetic noise is the dominant failure mode of change detection,** not missed changes.
Normalisation before hashing does more work than any model in the pipeline.

**A competitor's blog is two sources at once** — grade A for their own positioning, grade C
for the industry statistics they cite. Handling this required grading source reliability and
information credibility independently rather than assigning one trust score per domain.

**The most direct competitor is the least transparent.** Sonatype is private and files
nothing, so claims about their commercial performance cannot be corroborated against
regulated disclosure. The system must express lower confidence rather than hide the gap.

**Sources fail asymmetrically.** Sonatype's blog has no discoverable RSS feed, requiring a
sitemap fallback while GitHub releases arrive as clean Atom. Source quality varies far more
than source lists suggest.

**Review sites are the richest excluded source.** G2 and TrustRadius carry genuine
competitive intelligence and prohibit automated collection. Excluded on ethics — recorded as
a decision, not a gap.

**The most valuable thing the system cannot do is win/loss analysis,** because the data is
internal. Naming it is more useful than approximating it.

**Scope pressure lands on the interface.** Backend work has clear milestones; interface work
expands to fill available time. The cut list exists because that decision is better made in
advance than at 2am.

---

## 12. Roadmap

**Next two weeks** — Stage 2 model adjudication of claim relationships and contradictions;
full configuration CRUD; claim lifecycle and re-confirmation; the evaluation harness and
golden set; Slack delivery.

**Retrieval quality — deferred deliberately, with the reasoning.** Two techniques were
designed and not built, and both are worth naming because the decision to omit them was made
on cost grounds rather than by oversight:

- **Cross-encoder reranking.** v1 reranks deterministically on evidentiary value — source
  reliability grade, primary-versus-secondary standing, and recency — layered over RRF
  fusion. A cross-encoder would improve topical ordering within that set. It was deferred
  because it adds a second model dependency and per-query latency for marginal gain at a
  corpus of a few thousand chunks, and because the domain rerank addresses the failure that
  actually matters here: a topically similar blog post outranking the competitor's own
  pricing page. The right sequence is to add the cross-encoder *after* the evaluation harness
  exists, so the gain can be measured rather than assumed.
- **LLM-generated contextual chunk headers.** v1 prepends a deterministic context prefix
  (document title, section path, entity, date) to each chunk before embedding. The published
  technique generates a situating sentence per chunk with a model, which measurably improves
  retrieval but costs one inference per chunk at ingestion. Deferred on the same basis: the
  deterministic prefix captures most of the benefit at zero marginal cost.

**Next quarter** — Playwright for JavaScript-rendered sources; licensed review-site data;
analyst feedback learning the scoring weights; multi-language collection; SEC EDGAR and
job-posting ingestion.

**Where it becomes a competitive intelligence platform** — internal primary sources.
Salesforce closed-lost reasons and recorded call transcripts attaching to claims as internal
primary evidence, which is the point at which the system supports **win/loss analysis** rather
than external-signal monitoring alone.

**The JFrog-specific opportunity** — grounding competitive claims in JFrog's own product data:
Artifactory telemetry on package-type adoption trends, and Xray CVE data as competitive
evidence. A competitive intelligence system inside JFrog can do this. No external platform
ever could.

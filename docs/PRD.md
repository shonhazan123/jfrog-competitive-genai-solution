# PRD — Competitive Intelligence System for JFrog

| | |
|---|---|
| **Status** | Design approved · pre-implementation |
| **Date** | 25 August 2026 |
| **Author** | Shon Hazan |
| **Audience** | JFrog Competitive Intelligence team, CTO Office, and the assignment review panel |
| **Related** | [DESIGN.md](./DESIGN.md) — architecture and build plan |

---

## 1. Summary

The Competitive Intelligence team needs to stay current on a landscape that moves daily, and
to see how JFrog compares to its main competitors.

The obvious reading of that need is a competitor news digest. This document argues that a
digest answers only half of it, and proposes something different:

> **A system that watches the competitive landscape and the wider DevSecOps field every day,
> decides what genuinely matters, routes each finding to the division that can act on it, and
> keeps a living, sourced record of what is true — so that when something changes, the right
> person hears about it with the evidence attached.**

Two halves, deliberately given equal weight:

**The daily flow — what moved.** Competitor releases and deprecations, vulnerabilities in
competitor products, regulatory and standards movement across software supply chain security,
partnership and marketplace activity, hiring that reveals roadmap intent, new customer
evidence. This is the bulk of what the system produces, it arrives every day, and each item is
delivered as the object its audience can act on: an objection-and-response for sales, a
capability delta for product, a trend contribution for executives.

**The durable record — what is true.** Underneath the flow sits a ledger of competitive
*claims*, each with a subject, an asserter, a date, evidence, and a source grade. It is what
makes the comparison view possible, because a comparison is a *state* and a feed only carries
*events*. It is also what lets the system say *"this changed"* rather than only *"this
happened."*

The unit of the flow is the signal. The unit of the record is the claim. News becomes evidence
attached to claims; the battlecard becomes a rendered view of the ledger rather than a document
maintained by hand.

One capability deserves specific mention because it is unusual and because it is easy to
mistake for the whole product: the system detects when a **competitor changes what it publicly
claims about JFrog**. That is a genuinely differentiated signal, it is the sharpest single card
the tool produces, and it happens **less than once a week**. It is one high-value view among
several — not the spine. §6 quantifies the difference.

The system runs on a schedule without human intervention, can be triggered manually, and cites
a verbatim source for every sentence it generates.

---

## 2. The problem

**Stated need (assignment brief):** *"a system that keeps them updated daily on the latest
news and insights across our industry, and lets them see how JFrog compares to its main
competitors."*

That sentence contains two products with two different clocks:

| | Clock | Nature |
|---|---|---|
| "latest news and insights" | hours | a stream of **events** |
| "how JFrog compares" | weeks–months | a durable **state** |

A feed architecture serves the first and structurally cannot produce the second, because a
comparison is a state and a feed only carries events. This is the central design problem.

### Three failure modes this product is designed against

**1. The commodity trap.** Competitor news aggregation with LLM summarisation is a
purchasable product — Klue, Crayon, Kompyte, Contify and AlphaSense all sell it. Crayon
alone scans roughly 300 signal types. Anything we build that is merely a thinner version of
those tools invites the question *"why not buy it?"* and has no good answer.

**2. Alert fatigue.** A CI analyst does not have a coverage problem. She has a filtering
problem. A system that surfaces everything trains its readers to ignore it, and a system
that is ignored is worse than no system, because it consumes budget and creates false
confidence that the landscape is being watched.

**3. Confident wrongness.** A wrong competitive claim is worse than no claim. A sales rep
who repeats an inaccurate statement about a competitor in a live deal loses credibility with
the buyer and damages JFrog's. Published research on deep-research agents finds that their
dominant failure is not fabricated sources but **inaccurate paraphrase of real ones** — the
system says something the source nearly says. That specific failure is the one this design
guards against structurally.

### Why a general CI platform is not sufficient here

Commercial CI platforms are tuned for GTM-shaped competition: messaging, review sites,
social sentiment, press. JFrog competes on **technical substance** — package format
coverage, scanner accuracy, CVE contextual analysis, model-registry and MCP capability,
runtime posture.

A general platform cannot read a Nexus release note and tell you it changes a bake-off. A
domain-specific system can. This is also the reason the capability belongs in the CTO Office
rather than in marketing operations.

---

## 3. Users and jobs to be done

Four consumers. The central design idea:

> **Audience adaptation is not tone or length. It is a different question answered against
> the same evidence.**

Most tools that claim audience awareness simply make the executive version shorter. That is
cosmetic. Each division is asking a genuinely different question, and the correct answer is a
different *object*, not a shorter paragraph.

| | **Sales (AE / SE)** | **Product Management** | **Executives** | **CI Analyst** |
|---|---|---|---|---|
| **Question** | "Could this change a live deal in the next 90 days?" | "Does this change what we build, or how we sequence it?" | "Does this change the shape of the market or our position in it?" | "Is this trustworthy, and does it move a claim I own?" |
| **Critical inputs** | Competitor claims *about JFrog*; pricing and packaging moves; competitor security incidents; capability gaps that opened or closed | Release notes, GA features, deprecations; format and standard support; capability parity deltas; developer sentiment | M&A and funding; analyst movement; category formation; regulation reshaping demand; competitor narrative shifts | Everything, graded and queued |
| **Explicitly not critical** | Funding rounds, standards bodies, general industry trend news | Sales objections, earnings colour, most PR | Individual releases, individual objections | — |
| **Output object** | **Objection → response pair** | **Capability delta + link to the primary artifact** | **Trend with direction, velocity, confidence** | **Work item**: confirm / reject / edit / suppress |
| **Cadence** | Daily, plus interrupts | Daily, low urgency | **Weekly, never daily** | Continuous |
| **Half-life** | Hours–days | Weeks–months | Months | Permanent |
| **What kills it** | Anything requiring reading. 15 seconds or ignored. | Paraphrase without the source | Noise. False positives are punished hardest here. | Unsourced assertions |

### The illustrating example

**One event:** *Sonatype ships AI/model scanning in Nexus Firewall.*

- **Sales →** *"New Sonatype claim in bake-offs. Their coverage is HuggingFace-format only.
  Ask the prospect which model formats they actually pull. Counter: JFrog AI Catalog + Xray
  contextual analysis."*
- **Product →** *"Model scanning now present in competitor. Formats covered: […]. Gap
  analysis vs AI Catalog: […]. Primary source: release note, verbatim excerpt, link."*
- **Executive →** *"Third competitor move into AI-artifact security this quarter. The
  category is forming and JFrog is being positioned as the incumbent to displace."*
- **Analyst →** *"New claim extracted, source grade A2, affects 3 battlecard rows, needs
  confirmation before publish."*

Same evidence. One collection pass. Four different objects.

### Two notes on persona design

**Executives must be weekly, and the roll-up must be permitted to report stability.**
*"Nothing material moved this week"* is intelligence. A system willing to say so is a system
whose alerts are believed. A daily executive email is how this product dies in week two.

**Sales needs what to say, not what happened.** *"Sonatype announced X"* fails the rep.
*"If they raise X, here is the counter and the source"* succeeds. This distinction drives the
entire output format for that persona.

---

## 4. Product principles

1. **The claim is the atomic record.** Articles are evidence attached to claims, not the
   product itself.
2. **Every generated sentence traces to a verbatim quote in stored source material.** If it
   cannot, it does not ship. This is enforced in code, not requested in a prompt.
3. **Deterministic where auditable, model-driven where judgement is required.** The model
   assigns labels; policy decides audience; code does arithmetic.
4. **Scarcity over coverage.** The digest has a hard item budget. Ranking is forced.
5. **The team owns its own coverage.** Adding a competitor, a source, or a watchlist term is
   configuration, not engineering.
6. **Collection is ethical and visibly so.** Public sources only, robots.txt honoured, and
   the compliance record is shown in the product.
7. **Report stability as well as change.** Negative findings are surfaced, not silently
   omitted.

---

## 5. Requirements

### 5.1 Collection

| ID | Requirement | v1 |
|---|---|---|
| R1.1 | Collect from RSS/Atom feeds, JSON APIs, and static HTML pages on per-source schedules | ✅ |
| R1.2 | Honour `robots.txt` per domain; record and display the compliance decision per source | ✅ |
| R1.3 | Identify as a named agent with contact details; enforce per-domain rate limiting | ✅ |
| R1.4 | Use conditional GET (ETag / If-Modified-Since); treat `304` as definitive no-change | ✅ |
| R1.5 | Backfill historical versions of tracked pages from a public web archive at seed time | ✅ |
| R1.6 | Store raw responses immutably; never overwrite a capture | ✅ |
| R1.7 | Flag sources requiring JavaScript rendering as blocked rather than failing silently | ✅ |
| R1.8 | Render JavaScript-dependent pages | ⏭ roadmap |
| R1.9 | Ingest licensed review-site and social data | ⏭ roadmap |

### 5.2 Change detection

| ID | Requirement | v1 |
|---|---|---|
| R2.1 | Detect change through a cascade — HTTP 304, raw hash, normalised hash, structural diff — before invoking any model | ✅ |
| R2.2 | Normalise away navigation, footers, scripts, analytics identifiers, session tokens and rotating content before hashing | ✅ |
| R2.3 | Diff tracked pages structurally (row/cell level for comparison tables), not as free text | ✅ |
| R2.4 | Classify surviving changes as cosmetic, substantive, new claim, or removed claim | ✅ |
| R2.5 | Record a before/after trail for every claim change | ✅ |

### 5.3 Analysis

| ID | Requirement | v1 |
|---|---|---|
| R3.1 | Extract typed facets from source text: signal type, subject entity, asserting entity, capability tags, claim candidates, verbatim quotes with offsets | ✅ |
| R3.2 | Constrain extraction to closed enumerations; reject free-text entities | ✅ |
| R3.3 | Verify every quote by string match against the stored capture; reject unverifiable records to an analyst queue | ✅ |
| R3.4 | Generate a per-persona "so what" grounded in the ledger's record of JFrog's own position | ✅ |
| R3.5 | Deduplicate and cluster related items so one event produces one record with multiple evidence links | ✅ deterministic |
| R3.6 | Adjudicate new vs. restatement vs. update vs. contradiction against existing claims | ⏭ roadmap |

### 5.4 Scoring and routing

| ID | Requirement | v1 |
|---|---|---|
| R4.1 | Score materiality per persona using an explainable weighted function over extracted labels | ✅ |
| R4.2 | Display the score breakdown as arithmetic in the interface | ✅ |
| R4.3 | Make weights, the signal-type × persona matrix, and the watchlist editable without code changes | ✅ |
| R4.4 | Permit a bounded model adjustment (±1) with a written, logged reason | ✅ |
| R4.5 | Enforce a hard item budget per digest independent of score | ✅ |
| R4.6 | Support exactly one interrupt tier: competitor claims about JFrog, competitor security incidents, M&A | ✅ |
| R4.7 | Learn weights from analyst feedback | ⏭ roadmap |

### 5.5 Comparison

| ID | Requirement | v1 |
|---|---|---|
| R5.1 | Maintain a JFrog-versus-competitor view by capability dimension, derived from the claim ledger rather than hand-authored | ✅ |
| R5.2 | Flag dimensions whose supporting claims changed recently | ✅ |
| R5.3 | Provide a dedicated view of what competitors publicly assert **about JFrog**, with history | ✅ |
| R5.4 | Link every cell to its evidence: verbatim quote, source, capture date, reliability grade | ✅ |

### 5.5b Collection coverage

| ID | Requirement | v1 |
|---|---|---|
| R5.5 | Maintain a coverage matrix of entities × signal types × configured sources, and surface cells with no source | ✅ |
| R5.6 | Rank retrieved evidence by evidentiary value — source reliability, primary standing, recency — not by topical similarity alone | ✅ |
| R5.7 | Return an empty result rather than widening a filter when no evidence matches | ✅ |

**Why R5.5 exists.** The system's most differentiated view — what competitors publicly assert
about JFrog — is also its most tempting source of bias. If collection over-weights comparison
pages, the ledger fills with cross-assertions and under-represents the far more common cases:
a competitor describing itself, a third party describing a competitor, and industry-level
developments with no single subject.

The governing principle, applied here for the second time in this design:

> **Collection must be unbiased. Prioritisation may be biased — visibly, and tunably.**

Prioritisation weights (including the multiplier applied when JFrog is the subject of a
claim) live in `materiality.yaml` and can be lowered to 1.0 by an analyst, immediately
re-ranking the entire ledger. Collection breadth, by contrast, is enforced structurally: the
coverage matrix makes gaps a visible screen rather than an assumption. In the vocabulary of
the discipline, this is a **collection gap analysis**, and it is the honest answer to
*"how do you know what you are not seeing?"*

### 5.6 Distribution

| ID | Requirement | v1 |
|---|---|---|
| R6.1 | Run collection and analysis automatically on a schedule with no human trigger | ✅ |
| R6.2 | Support manual triggering of the same job path from the interface | ✅ |
| R6.3 | Send a daily email digest via SMTP, parameterised by persona, linking into the application | ✅ |
| R6.4 | Produce a weekly executive roll-up | ✅ |
| R6.5 | Answer ad-hoc questions grounded strictly in the ledger, with citations, refusing when evidence is absent | ✅ |
| R6.6 | Deliver to Slack and support per-user scheduling | ⏭ roadmap |

### 5.7 Analyst control

| ID | Requirement | v1 |
|---|---|---|
| R7.1 | Confirm, reject, edit, or suppress any item, recording the action and actor | ✅ |
| R7.2 | Display source reliability and information credibility as independent grades | ✅ |
| R7.3 | View and edit configuration (weights, watchlist, source enable/disable) in the interface | ✅ |
| R7.4 | Add competitors and sources through the interface | ⏭ roadmap (v1: configuration file) |
| R7.5 | Show what changed since the user's previous visit | ✅ |

### 5.8 Non-functional

| ID | Requirement |
|---|---|
| N1 | Runs from a clean clone via `docker compose up` with only API credentials supplied |
| N2 | Contains meaningful data immediately on first run — no waiting period before the product is demonstrable |
| N3 | Model cost bounded by funnel design; the large majority of collected items never reach a model |
| N4 | Untrusted external content never reaches a component holding tools or credentials |
| N5 | Every displayed assertion is traceable to an immutable stored capture |
| N6 | Interface is comprehensible to a non-technical analyst without training or a guided tour |

---

## 6. Signal taxonomy

One enumeration, used for routing, scoring and filtering throughout. Each type has its own
sources, its own detection mechanism, its own audience, and — importantly — its own expected
volume.

### The volume column exists to prevent a specific mistake

The most *interesting* thing this system produces is the detection of a competitor changing
what it publicly says about JFrog. It is also, by a wide margin, the **rarest** thing it
produces. Reading the design and concluding that cross-assertion detection is the product
would be a category error, and the table below is here to make that impossible to sustain.

| Type | Expected items/week | Detection | Primary sources | Sales / Prod / Exec |
|---|---|---|---|---|
| `product_capability` | **15–30** | feed | GitHub `.atom` release feeds, vendor release notes, changelogs, docs sitemaps | 2 / **3** / 1 |
| `security_trust` | **5–15** | API | **OSV.dev API**, **GitHub Security Advisories API**, CISA KEV, vendor bulletins | 2 / **3** / 2 |
| `market_regulatory` | **5–10** | feed | EU CRA/NIS2, CISA, NIST SSDF, OpenSSF/SLSA/Sigstore, CNCF, EU AI Act | 1 / 2 / **3** |
| `partnership_ecosystem` | 3–8 | feed + snapshot | Newsrooms, cloud marketplace listings, CNCF announcements, GitHub org activity | 2 / 2 / 2 |
| `talent_org` | 2–5 | API | **Greenhouse / Lever / Ashby public job JSON** | 0 / **3** / 2 |
| `customer_evidence` | 2–5 | snapshot | Competitor case-study and customer-logo pages, conference talks | **3** / 1 / 2 |
| `positioning_messaging` — *self* | 1–3 | snapshot | Homepage hero copy, category pages, product page headlines | 2 / 1 / **3** |
| `corporate_financial` | 0–2 | API + feed | **SEC EDGAR full-text search**, press releases, tech press | 0 / 0 / **3** |
| `positioning_messaging` — *cross* | **< 1** | snapshot | Competitor comparison pages | **3** / 1 / 1 |
| `pricing_packaging` | **< 0.5** | snapshot | Pricing pages, marketplace listings, licensing docs | **3** / 1 / 2 |

Read the first and last rows together. **`product_capability` outnumbers cross-assertion by
roughly thirty to one.** The daily digest is overwhelmingly made of releases, vulnerabilities
and industry movement. Cross-assertion is the rare, high-materiality event that earns an
interrupt when it happens — not the thing the system spends its time doing.

### What each type actually is

**`product_capability` — the backbone of the daily digest.**
Competitors shipping, deprecating, or extending capability. Collected from GitHub release
feeds (`.atom`, free, structured, dated), vendor release-note pages, and docs sitemaps — a new
documentation page is often the earliest public evidence of a new feature.
*Example:* "Nexus 3.95 adds Cargo registry support and drops Java 11."
The detection nuance that matters: **a release note is not one signal.** A release with forty
bullet points may contain two material capability changes and thirty-eight bug fixes.
Classification therefore happens at **bullet level**, using the element parser — each list
item is an element, judged on its own. Treating a release as an atomic signal is the single
most common way a competitor-tracking system becomes noise.

**`security_trust` — the highest-quality feed in the system, and free.**
CVEs affecting competitor products, advisories, breaches, and supply-chain incidents.
**OSV.dev and the GitHub Security Advisories API are structured, free, primary, and require no
scraping at all** — they are the cleanest Tier-1 sources available and are queried by package
and product identifier rather than crawled.
*Example:* "GHSA-xxxx: authentication bypass in Nexus Repository ≤ 3.94, CVSS 9.1."
**A handling note that belongs in the product, not just in a policy document:** a competitor's
vulnerabilities are legitimate competitive intelligence, and weaponising them in a sales
conversation is reputationally hazardous — particularly for a vendor whose own business is
security. Signals of this type carry a **handling caution flag** in the sales view, and the
so-what is framed around capability posture rather than the individual CVE.

**`market_regulatory` — the industry lane, and the reason the executive roll-up is worth
reading.**
Nothing here is about a competitor. EU Cyber Resilience Act obligations, NIS2, SBOM mandates,
NIST SSDF revisions, SLSA and Sigstore adoption, CNCF graduation events, the EU AI Act as it
touches model provenance. This is the "insights across our industry" half of the brief, and it
is the lane that answers *"is the market moving toward us or away from us?"* — a question no
amount of competitor tracking can answer on its own.
*Example:* "CRA reporting obligations for actively exploited vulnerabilities take effect;
SBOM becomes a procurement precondition in scope sectors."

**`talent_org` — the leading indicator.**
Public applicant-tracking APIs (Greenhouse, Lever, Ashby) expose competitor job postings as
JSON. Hiring reveals roadmap intent **six to twelve months before anything ships**, which
makes this the only signal type that is predictive rather than reactive.
*Example:* "Sonatype opens three roles referencing model registries and ML artifact scanning."
This is established competitive-intelligence tradecraft and it costs one JSON endpoint.

**`customer_evidence` — the ethical substitute for review-site scraping.**
Review sites are excluded on ethics grounds (§8). But a competitor's own case-study page and
customer-logo wall are public, primary, and diffable: **a new logo appearing there is a win
signal**, and a logo disappearing is worth a question. Conference talk listings serve the same
purpose.
*Example:* "A new financial-services case study appears on Sonatype's customer page."

**`positioning_messaging` — and it has two halves, of which the *self* half is larger.**
- **Self-positioning:** how a competitor describes *itself*. When a homepage headline shifts
  from "repository manager" to "software supply chain security platform," that is a strategic
  repositioning — and it is a bigger signal than any individual competitive bullet point,
  because it tells you which market they intend to compete in next.
- **Cross-assertion:** what a competitor publicly claims about JFrog.

Both are detected by the same mechanism — snapshot plus structural diff — and the self half
fires more often. **Tracking only the attack page would mean watching a competitor's argument
while missing their strategy.**

**`partnership_ecosystem`** — integrations, cloud marketplace listings, alliances, standards
body participation. Often the earliest signal of a go-to-market shift.

**`corporate_financial`** — funding, M&A, earnings, leadership change. Executive-only, and
constrained by the transparency asymmetry described in §7: JFrog, GitLab and Microsoft file
with the SEC; Sonatype is private and files nothing.

**`pricing_packaging` — rare, and the highest materiality per event in the system.**
Detected by snapshot diff of pricing tables and marketplace listings. Two nuances the design
handles explicitly: many vendors publish no price at all, so the system tracks a
`price_visible` flag over time — **a change from a listed price to "contact sales" is itself a
material signal** — and cloud marketplace listings frequently expose real pricing that the
vendor's own site does not.

---

## 6b. What a day actually looks like

A concrete illustration, because the taxonomy above is abstract and the balance of the product
is easier to see than to describe. This is a representative Tuesday.

**Collected:** 94 items across 23 sources. **Clustered:** to 41 distinct events.
**Above materiality threshold:** 11. **Delivered:** 6 to sales, 8 to product, 0 to executives
(their roll-up is weekly).

### The sales digest — 6 items, budget capped

| # | Type | Item |
|---|---|---|
| 1 | `security_trust` ⚑ | Advisory affecting Nexus Repository ≤ 3.94. *Handling caution: lead on posture, not the CVE.* Response framing supplied. |
| 2 | `product_capability` | Nexus 3.95 adds Cargo registry support. Bake-off relevant where Rust toolchains are in scope. Counter-position supplied. |
| 3 | `customer_evidence` | New financial-services case study on a competitor's customer page. Named account overlap flagged. |
| 4 | `partnership_ecosystem` | Competitor listing appears in a cloud marketplace — changes procurement path in enterprise deals. |
| 5 | `product_capability` | Deprecation announced for a format two accounts depend on. Migration angle supplied. |
| 6 | `market_regulatory` | CRA reporting obligations dated; procurement questions expected. |

### The product digest — 8 items

Release-note deltas at bullet level, a capability-parity change, two `talent_org` postings
signalling a model-registry investment, a standards movement item on SLSA adoption, and two
items marked *no action, awareness only*.

### The executive weekly, assembled Friday

Three trend contributions and one explicit stability statement: *"No material change in
competitor positioning this week."*

### And on the day it happens

> ⚑ **INTERRUPT — `positioning_messaging` (cross-assertion)**
> Sonatype changed what its comparison page says about JFrog: malware detection moved from
> *"Limited"* to *"Very limited, not proactive."* Before/after captured, source dated, grade A.

**That card is the sharpest thing in the product.** It is also the only one of these that will
not appear next Tuesday, or the Tuesday after. Both facts are true simultaneously, and the
design holds both: **the assertion card is what makes the tool memorable; the other ninety-four
items are what make it useful.**

A tool built only for the first would be a clever demonstration that goes unopened by Thursday.
A tool built only for the second would be a competent feed with no reason to prefer it over a
commercial platform. The system is built for both, and §5.5b describes the control — the
collection coverage matrix — that keeps the balance honest rather than aspirational.

---

## 7. Source strategy

Sources are tiered by reliability and by primary/secondary standing, following intelligence
practice. All Tier 1 entries below were verified directly on 25 August 2026.

**Tier 1a — free structured APIs, no scraping required.** The highest quality-to-effort ratio
in the entire source strategy, and the tier most competitive-intelligence tooling overlooks
because it is unglamorous:

| Source | Feeds | Access |
|---|---|---|
| **OSV.dev** | Vulnerabilities affecting competitor products | Public JSON API, query by package/ecosystem |
| **GitHub Security Advisories** | Advisories, severity, affected ranges | Public GraphQL/REST API |
| **GitHub Releases** (`.atom`) | Release notes, dated, with bodies | Public Atom, no auth |
| **Greenhouse / Lever / Ashby** | Competitor job postings | Public JSON board endpoints |
| **SEC EDGAR full-text search** | Filings for FROG, GTLB, MSFT | Public API |
| **CISA KEV / advisories** | Actively exploited vulnerabilities | Public JSON |

These are primary, structured, dated, and stable. They require no HTML parsing, no robots
negotiation, and no rate-limit brinkmanship — and together they supply the majority of daily
signal volume.

**Tier 1b — the competitor speaking for itself, collected by page snapshot**
Comparison pages; **homepage and category pages** (self-positioning); pricing pages; vendor
release notes and changelogs; docs sitemaps; case-study and customer-logo pages; newsrooms;
official blogs.

**Tier 2 — secondary, moderate reliability**
Technology press (The New Stack, DevOps.com, InfoQ); Hacker News; broad news aggregation.
This tier carries most of the industry lane and requires the hardest filtering, because
volume is high and value density is low.

**Tier 3 — high intelligence value, not collected**
Review sites (G2, TrustRadius, PeerSpot) and social platforms. Genuinely rich sources,
aggressively bot-protected, with terms of service that prohibit automated collection.
**Excluded as a deliberate ethics decision, not a capability gap.** Roadmap item: licensed
API access.

### A structural asymmetry worth naming

JFrog, GitLab and Microsoft file with the SEC. Sonatype is privately held and files nothing.
**The most direct competitor is the least financially transparent one.** The correct response
is to weight Sonatype's self-published material more heavily precisely because no regulated
disclosure exists to corroborate against — and to be explicit that claims about Sonatype's
commercial performance are lower-credibility by necessity.

### Source grading

Each source carries two independent grades, following the Admiralty Code used in
intelligence practice: **source reliability (A–F)** and **information credibility (1–6)**.
They are independent because a reliable source can pass along bad information and a
questionable source can be right.

This has a practical consequence the product implements: **a competitor's blog is grade A
when extracting their own positioning and grade C when extracting industry statistics.** Same
document, two grades, depending on what is being extracted.

---

## 8. Collection ethics

This section is a product requirement, not a disclaimer.

**The line, in the vocabulary of the discipline (SCIP code of ethics):** no
misrepresentation, no pretexting, no obtaining access under false pretences.

Concretely, the system will **never** register for a competitor's trial under a false
identity to collect from inside the product, and will never attempt to bypass bot protection.

**What it does:** reads publicly published pages, at a polite rate, identifying itself
honestly, honouring `robots.txt`, using conditional requests to minimise load.

**Compliance is made visible, not merely true.** The source list displays the robots
decision per source, and sources excluded on ethical grounds appear as excluded with the
reason — rather than being quietly absent.

---

## 9. Success criteria

**Product**

- An analyst can determine, in under 30 seconds on the landing screen, whether anything
  needs their attention today.
- Every assertion shown can be traced to a verbatim quote, a source, and a capture date in
  two clicks or fewer.
- A sales user receives items they can use in a conversation without further research.
- The daily digest is small enough to read completely.

**System**

- Scheduled runs complete without intervention.
- The proportion of collected items reaching a model stays low (funnel efficiency).
- No record with an unverifiable quote reaches a digest.
- Adding a watchlist term or changing a weight requires no code change and re-ranks existing
  history immediately.

**Explicitly not claimed for v1:** measured precision and recall against a labelled golden
set. The evaluation harness is designed but not built; the analyst feedback mechanism exists
to accumulate the labelled data it will require. Claiming measured accuracy without that
harness would be exactly the kind of unfounded confident assertion this product is built to
prevent.

---

## 10. Scope

### In scope for v1

Deep coverage of one competitor (Sonatype) with tracked claims, real change detection and a
populated comparison view; news-only coverage of four others; the industry lane; four
persona views; scheduled and manual runs; email delivery; grounded ad-hoc querying; analyst
confirm/reject/edit/suppress; configuration-driven coverage.

### Out of scope for v1

Deep coverage of all competitors; JavaScript-rendered sources; licensed third-party data;
model-driven claim adjudication; cross-encoder reranking and model-generated contextual chunk
headers (both designed, both deferred — see [DESIGN §12](./DESIGN.md#12-roadmap)); claim
lifecycle management; feedback-driven weight learning; Slack delivery; measured accuracy
evaluation.

### Out of scope entirely

**Win/loss analysis.** It requires CRM records and buyer interviews that are not available
in this context. The data model is designed so that Salesforce closed-lost reasons and call
transcripts can later attach to claims as *internal primary evidence* — which is the point at
which this becomes a full competitive intelligence platform rather than an external-signal
tool. It is named here as the single highest-value future investment.

---

## 11. Risks

| Risk | Response |
|---|---|
| Competitor site restructures and breaks extraction | Explicit "needs a parser" state; never silent failure or garbage extraction |
| Change detection produces cosmetic noise | Five-layer cascade; normalisation before hashing is the highest-leverage defence |
| Model misparaphrases a real source | Verbatim quote verification in code; unverifiable records are rejected, not shown |
| Digest is ignored | Hard item budget, aggressive clustering, single interrupt tier, negative reporting |
| Analyst disagrees with ranking and loses trust | Scores are visible arithmetic over tunable weights — disagreement becomes a settings change, not a loss of faith |
| Untrusted page content attempts to manipulate the pipeline | Privilege isolation: the component reading external content holds no tools and takes no actions |
| Archive coverage is uneven | Documented as sampled rather than continuous history |

---

## 12. Glossary

Included because this document has both technical and non-technical readers.

**Claim** — a durable competitive assertion with a subject (who it is about), an asserter
(who says it), evidence, a date, and a grade.

**Signal** — a dated event. Decays. Becomes evidence attached to claims.

**Battlecard** — the sales-facing comparison artifact. Here it is *derived* from the claim
ledger rather than authored by hand.

**Materiality** — how much a given change should matter to a given audience. Scored, visible,
and tunable.

**Admiralty Code** — an intelligence-practice scheme grading source reliability (A–F) and
information credibility (1–6) on independent axes.

**Primary source** — the subject speaking for itself: a competitor's own pricing page,
release note, or comparison page. **Secondary source** — a third party reporting on them.

**Corroboration** — independent sources asserting the same thing, which raises credibility
without raising source reliability.

**Win/loss analysis** — post-deal research into why deals were won or lost. Out of scope here;
see §10.

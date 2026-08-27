# KITs, Citations & Demo UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Written for **fast mode** — build all tasks, write each task's tests as part of the task, run the suite once at the end.

> ## ⛔ Precondition
> Plans 1–4 complete. `docker compose up -d` serves the API on :8000 and the client on :5173,
> and every screen renders. This plan is a **delta**, not a rebuild.

**Goal:** Turn a working pipeline into a demo that lands the job — by reorganising what is shown around the six questions a CI lead actually asks, citing every single assertion with a clickable origin, and making the agent visibly work without blocking the user.

## Scope discipline — read this first

**This is a demo, not a product.** Nobody will use it for months. Therefore:

**Explicitly NOT built** — and if you find yourself adding any of these, stop:
- Recency windows, rolling date ranges, "since your last visit", unread state
- Run history, persistence of past runs beyond the current one
- As-of-date reconstruction of past comparisons
- User accounts, preferences, saved views

**Every daily screen shows the latest run. Full stop.**

The demo has exactly two beats, and every task below serves one of them:

| Beat | The claim | Where it lands |
|---|---|---|
| **1 · The agent** | *"I gather what matters, for every division, automatically — and cite all of it."* | Run now → stages → Today's six KIT tiles → the same event framed three ways in Divisions |
| **2 · The trajectory** | *"And separately, here is how a competitor's argument against us evolved over five years."* | Its own tab, after Industry |

## Global Constraints

All prior plan constraints hold. Additionally:

- **No system word reaches a consumer screen.** No `interrupt`, `M 87`, `product_capability`, `cluster`, `corroboration`. Human labels come from `config/labels.yaml`. **One carve-out: Settings**, where an analyst tunes the machine and needs the machine's names.
- **No assertion renders without a clickable origin link.** Not just quotes — every headline, every comparison cell, every KIT snippet, every Ask citation. If a record has no resolvable `source_url`, the API does not return it to a delivery surface.
- **One exception, visually marked:** JFrog's own authored positions, which show "Authored by the CI team" in place of a link.
- No new dependencies.

---

## File Structure

| File | Responsibility |
|---|---|
| `config/kits.yaml` | The six Key Intelligence Topics and their signal-type membership |
| `config/labels.yaml` | Every machine value → its human display label |
| `config/run_stages.yaml` | Human-named pipeline stages |
| `backend/app/services/kits.py` | Signals → KIT rollup |
| `backend/app/services/citation.py` | Resolve and validate origin links |
| `backend/app/models/run.py` | `Run` — id, stage, counters, status |
| `backend/app/routers/kits.py`, `runs.py` | `GET /kits`, `POST /runs`, `GET /runs/{id}` |
| `client/src/config/labels.ts` | Client-side label lookup |
| `client/src/components/SourceLink.tsx` | The citation component — used everywhere |
| `client/src/components/KitTile.tsx` | One KIT, with snippet |
| `client/src/components/RunProgress.tsx` | Non-blocking stage indicator |
| `client/src/pages/Today.tsx` | Rewritten as a KIT grid |
| `client/src/pages/Trajectory.tsx` | The archive tab |

---

### Task 1: KIT rollup, display labels and citation enforcement

**Files:**
- Create: `config/kits.yaml`, `config/labels.yaml`, `backend/app/services/kits.py`, `backend/app/services/citation.py`, `backend/app/routers/kits.py`
- Modify: `backend/app/config/schema.py`, existing signal/comparison serialisers to embed citations and labels
- Test: `tests/test_kits.py`, `tests/test_citation.py`

**Produces:** `GET /kits`, `Citation` in every delivered payload, `label` on every enum value

- [ ] **Step 1: Write the failing tests**

```python
def test_every_signal_type_belongs_to_exactly_one_kit():
    config = load_config()
    membership = [t for kit in config.kits.kits for t in kit.includes.signal_types]
    assert sorted(membership) == sorted(set(membership))          # no double-counting
    assert set(membership) == set(config.signal_types.types)      # nothing orphaned

def test_kits_roll_up_the_latest_run_only(session, signals_across_two_runs):
    from app.services.kits import roll_up
    kits = roll_up(session, cfg=CFG)
    total = sum(k.count for k in kits)
    assert total == LATEST_RUN_SIGNAL_COUNT

def test_a_quiet_kit_reports_no_change_rather_than_being_omitted(session, sparse_signals):
    kits = roll_up(session, cfg=CFG)
    assert len(kits) == 6
    quiet = [k for k in kits if k.count == 0]
    assert quiet and all(k.status == "no_change" for k in quiet)

def test_each_kit_carries_a_snippet_with_a_citation(session, seeded_signals):
    kit = next(k for k in roll_up(session, cfg=CFG) if k.count > 0)
    assert kit.snippet.headline
    assert kit.snippet.citation.source_url.startswith("http")

def test_a_signal_without_a_source_url_is_never_delivered(session, signal_missing_url):
    from app.services.citation import deliverable
    assert deliverable(signal_missing_url) is False

def test_archived_captures_expose_both_a_live_and_an_archived_link(session, archive_signal):
    from app.services.citation import build_citation
    citation = build_citation(archive_signal)
    assert citation.source_url and citation.archived_url
    assert "web.archive.org" in citation.archived_url

def test_every_enum_value_has_a_human_label():
    config = load_config()
    for value in config.signal_types.types:
        assert config.labels.signal_types[value]
        assert "_" not in config.labels.signal_types[value]
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose run --rm api pytest tests/test_kits.py tests/test_citation.py -v`

- [ ] **Step 3: Write `config/kits.yaml`**

```yaml
# Key Intelligence Topics — the six standing questions the CI team asks.
# Signal types are how the machine classifies. KITs are how the team thinks.
# Every signal type belongs to exactly one KIT; nothing is orphaned or double-counted.
kits:
  - key: deal_threats
    label: Deal Threats
    question: What will a rep hit in a live deal this quarter?
    category: early_warning
    order: 1
    includes:
      signal_types: [positioning_messaging, pricing_packaging, customer_evidence]

  - key: parity_gaps
    label: Parity & Gaps
    question: Where did the capability line move — in either direction?
    category: strategic
    order: 2
    includes:
      signal_types: [product_capability]

  - key: rival_strategy
    label: Rival Strategy
    question: Is a competitor repositioning itself, and toward what?
    category: key_players
    order: 3
    includes:
      signal_types: [partnership_ecosystem]

  - key: category_market
    label: Category & Market
    question: Is the field forming around something new?
    category: strategic
    order: 4
    includes:
      signal_types: [market_regulatory]

  - key: trust_security
    label: Trust & Security
    question: Incidents and advisories — theirs, and the category's.
    category: early_warning
    order: 5
    includes:
      signal_types: [security_trust]

  - key: momentum
    label: Momentum & Viability
    question: Who is rising, who is stalling?
    category: key_players
    order: 6
    includes:
      signal_types: [corporate_financial, talent_org]

# A signal whose subject is JFrog is promoted into Deal Threats regardless of
# its type — a competitor talking about us is always deal-relevant.
promote_to_deal_threats_when:
  subject_entity: jfrog
```

- [ ] **Step 4: Write `config/labels.yaml`**

```yaml
# No machine word reaches a consumer screen. Settings is the one carve-out.
signal_types:
  product_capability:    Product release
  positioning_messaging: Positioning
  pricing_packaging:     Pricing & packaging
  security_trust:        Security advisory
  corporate_financial:   Corporate
  partnership_ecosystem: Partnership
  customer_evidence:     Customer evidence
  market_regulatory:     Industry & regulation
  talent_org:            Hiring signal

priority_bands:
  - { max: 39,  label: Watch }
  - { max: 59,  label: Notable }
  - { max: 79,  label: High }
  - { max: 100, label: Critical }

states:
  interrupt:   Needs attention today
  no_change:   No change in this run
  caution:     Handle with care — lead on posture, not the advisory
  authored:    Authored by the CI team
  absent:      No public claim on record

personas:
  sales:   Sales
  product: Product
  exec:    Executive

origins:
  extracted: From the source
  authored:  Authored by the CI team
  archive:   From the web archive
```

- [ ] **Step 5: Implement `citation.py`**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Citation:
    source_name: str
    source_url: str            # live URL — never None on a delivered record
    captured_at: str
    origin: str                # extracted | authored | archive
    archived_url: str | None = None
    grade: str | None = None   # None for authored

def deliverable(record) -> bool:
    """No assertion reaches a consumer screen without a resolvable origin.
    Authored positions are the one exception and carry origin='authored'."""
    if getattr(record, "origin", None) == "authored":
        return True
    url = getattr(record, "source_url", None)
    return bool(url) and url.startswith("http")

def build_citation(record) -> Citation:
    archived = None
    if getattr(record, "provenance", None) == "archive":
        stamp = record.fetched_at.strftime("%Y%m%d%H%M%S")
        archived = f"https://web.archive.org/web/{stamp}id_/{record.source_url}"
    return Citation(
        source_name=record.source_name,
        source_url=record.source_url,
        captured_at=record.fetched_at.isoformat(),
        origin=getattr(record, "provenance", "extracted"),
        archived_url=archived,
        grade=getattr(record, "reliability_grade", None),
    )
```

- [ ] **Step 6: Implement `kits.py` and mount `GET /kits`**

Roll up the latest run's signals into the six KITs. Each returns:
`key · label · question · status (active|no_change) · count · priority_label · snippet{headline, quote, implication, citation} · signal_ids`.
Records failing `deliverable()` are excluded and counted separately as `withheld`.

- [ ] **Step 7: Embed labels and citations in existing serialisers**

Every signal, comparison cell and Ask citation gains a `label` (human) alongside its raw value, and a `citation` object. Raw values stay in the payload — Settings needs them.

- [ ] **Step 8: Run tests, then the full suite, then commit**

```bash
git add config backend/app/services/kits.py backend/app/services/citation.py backend/app/routers/kits.py tests/
git commit -m "feat: KIT rollup, human display labels and citation enforcement"
```

---

### Task 2: Async run model with human-named stages

**Files:**
- Create: `backend/app/models/run.py`, `config/run_stages.yaml`
- Modify: `backend/app/routers/runs.py`, `backend/worker/jobs.py`
- Test: `tests/test_run_progress.py`

**Produces:** `POST /runs` → `202 {run_id}`, `GET /runs/{id}` → stage + counters

- [ ] **Step 1: Write the failing tests**

```python
def test_post_runs_returns_immediately_with_a_run_id(client):
    response = client.post("/runs", json={"kind": "collect"})
    assert response.status_code == 202
    assert response.json()["run_id"]

def test_progress_reports_a_human_stage_never_a_layer_name(client, running_run):
    body = client.get(f"/runs/{running_run.id}").json()
    assert body["stage_label"] in ("Checking sources", "Reading new documents",
                                   "Extracting claims", "Scoring and routing", "Done")
    assert "_" not in body["stage_label"]

def test_progress_carries_counters_so_the_ui_can_show_movement(client, running_run):
    body = client.get(f"/runs/{running_run.id}").json()
    assert {"current", "total"} <= set(body["progress"])

def test_a_finished_run_reports_what_it_produced(client, finished_run):
    body = client.get(f"/runs/{finished_run.id}").json()
    assert body["status"] == "done"
    assert body["new_items"] >= 0

def test_a_failed_run_surfaces_a_readable_message_not_a_traceback(client, failed_run):
    body = client.get(f"/runs/{failed_run.id}").json()
    assert body["status"] == "failed"
    assert "Traceback" not in body["message"]
```

- [ ] **Step 2: Write `config/run_stages.yaml`**

```yaml
stages:
  - { key: collect, label: Checking sources }
  - { key: read,    label: Reading new documents }
  - { key: extract, label: Extracting claims }
  - { key: score,   label: Scoring and routing }
  - { key: done,    label: Done }
```

- [ ] **Steps 3–5: Implement, run, commit**

`POST /runs` inserts a `Run` row, dispatches the job to a background task, returns `202`
immediately. The job updates `stage`, `current`, `total` as it proceeds. **Only the current
run is retained** — this is a demo; there is no run history.

```bash
git commit -am "feat: async run with human-named progress stages"
```

---

### Task 3: Client vocabulary layer and the SourceLink component

**Files:** `client/src/config/labels.ts`, `client/src/components/SourceLink.tsx`, `client/src/components/Cited.tsx`
**Test:** `client/src/components/citation.test.tsx`

- [ ] **Step 1: Write the failing tests — these are the enforcement mechanism**

```tsx
test("no consumer screen renders a machine value", () => {
  const pages = import.meta.glob("../pages/!(Settings|StyleGuide).tsx", { as: "raw", eager: true });
  const machineWords = /\b(interrupt|product_capability|positioning_messaging|talent_org|market_regulatory|corroboration|materiality)\b/;
  const offenders = Object.entries(pages).filter(([, src]) => machineWords.test(src));
  expect(offenders.map(([p]) => p)).toEqual([]);
});

test("SourceLink always renders a clickable origin", () => {
  render(<SourceLink citation={CITATION} />);
  const link = screen.getByRole("link", { name: /view source/i });
  expect(link).toHaveAttribute("href", CITATION.source_url);
  expect(link).toHaveAttribute("target", "_blank");
});

test("an archived capture offers both the live page and the captured version", () => {
  render(<SourceLink citation={{ ...CITATION, archived_url: "https://web.archive.org/x" }} />);
  expect(screen.getByRole("link", { name: /live page/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /as we captured it/i })).toBeInTheDocument();
});

test("an authored position states its origin instead of faking a link", () => {
  render(<SourceLink citation={{ ...CITATION, origin: "authored", source_url: "" }} />);
  expect(screen.getByText(/authored by the ci team/i)).toBeInTheDocument();
  expect(screen.queryByRole("link")).toBeNull();
});

test("Cited refuses to render content that has no citation", () => {
  const { container } = render(<Cited citation={undefined}><p>orphan claim</p></Cited>);
  expect(container).toBeEmptyDOMElement();
});

test("priority renders as a word, never as a bare number", () => {
  render(<PriorityBadge score={87} />);
  expect(screen.getByText("Critical")).toBeInTheDocument();
  expect(screen.queryByText("87")).toBeNull();
});
```

- [ ] **Steps 2–4: Run, implement, run**

`<Cited citation={…}>` is the wrapper every assertion goes through — it renders nothing if
there is no citation. That makes "no assertion without an origin" structural rather than a
convention someone has to remember.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(client): human vocabulary layer and mandatory citation components"
```

---

### Task 4: Today as a KIT grid

**Files:** `client/src/pages/Today.tsx`, `client/src/components/KitTile.tsx`
**Test:** `client/src/pages/today.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
test("six tiles render, one per Key Intelligence Topic", () => {
  renderPage(<Today />);
  expect(screen.getAllByTestId("kit-tile")).toHaveLength(6);
});

test("each tile states its standing question", () => {
  renderPage(<Today />);
  expect(screen.getByText(/what will a rep hit in a live deal/i)).toBeInTheDocument();
});

test("an active tile carries a snippet with quote, implication and a source link", () => {
  renderPage(<Today />);
  const tile = screen.getAllByTestId("kit-tile-active")[0];
  expect(within(tile).getByTestId("snippet-quote")).toBeVisible();
  expect(within(tile).getByTestId("snippet-implication")).toBeVisible();
  expect(within(tile).getByRole("link", { name: /source|live page/i })).toBeInTheDocument();
});

test("a quiet tile says so rather than appearing broken", () => {
  renderPage(<Today />);
  expect(screen.getAllByText(/no change in this run/i).length).toBeGreaterThan(0);
});

test("the highest-priority tile spans two columns", () => {
  renderPage(<Today />);
  expect(screen.getByTestId("kit-tile-lead")).toHaveClass("kit-tile--wide");
});

test("Today is a grid, not a single column", () => {
  renderPage(<Today />);
  const grid = screen.getByTestId("kit-grid");
  expect(getComputedStyle(grid).display).toBe("grid");
});

test("nothing on Today shows a raw score or a machine label", () => {
  renderPage(<Today />);
  expect(screen.queryByText(/^M ?\d+$/)).toBeNull();
  expect(screen.queryByText(/_/)).toBeNull();
});
```

- [ ] **Steps 2–4: Run, implement, run**

Grid: `repeat(auto-fit, minmax(320px, 1fr))`, lead tile `grid-column: span 2` at ≥1000px.
Tile content: KIT label · standing question · status/count · snippet (headline, one line of
verbatim quote, the implication) · `SourceLink`. Click opens the KIT's signals.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(client): Today as a six-tile Key Intelligence Topic grid"
```

---

### Task 5: Non-blocking run progress

**Files:** `client/src/components/RunProgress.tsx`, modify `StatusStrip.tsx`, `AppShell.tsx`
**Test:** `client/src/components/runprogress.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
test("Run now starts a run and does not block navigation", async () => {
  renderApp();
  await userEvent.click(screen.getByRole("button", { name: /run now/i }));
  expect(screen.getByTestId("run-progress")).toBeVisible();
  await userEvent.click(screen.getByRole("link", { name: /comparison/i }));
  expect(screen.getByTestId("run-progress")).toBeVisible();   // survives navigation
});

test("stages advance with human labels and a counter", async () => {
  renderApp({ runStages: ["Checking sources", "Reading new documents"] });
  await userEvent.click(screen.getByRole("button", { name: /run now/i }));
  expect(await screen.findByText(/checking sources/i)).toBeVisible();
  expect(await screen.findByText(/reading new documents/i)).toBeVisible();
});

test("completion refreshes the current screen in place", async () => {
  const { rerender } = renderApp({ finishAfterMs: 10 });
  await userEvent.click(screen.getByRole("button", { name: /run now/i }));
  expect(await screen.findByText(/new items/i)).toBeVisible();
  expect(queryClient.getQueryState(["kits"])?.isInvalidated).toBe(true);
});

test("a failure states what happened in plain language", async () => {
  renderApp({ failWith: "Could not reach 2 of 23 sources" });
  await userEvent.click(screen.getByRole("button", { name: /run now/i }));
  expect(await screen.findByText(/could not reach 2 of 23 sources/i)).toBeVisible();
});
```

- [ ] **Steps 2–4: Run, implement, run**

`POST /runs` → poll `GET /runs/{id}` every 1.5s. The indicator lives in the status strip, so
it persists across route changes. On `done`, invalidate the query cache and show a
`11 new items` toast. Never a modal, never a spinner over the page.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(client): non-blocking run progress with human stages"
```

---

### Task 6: Grid layouts and the Trajectory tab

**Files:** `client/src/pages/Trajectory.tsx`, modify `Divisions.tsx`, `Industry.tsx`, `AboutUs.tsx`, `src/config/navigation.ts`
**Test:** `client/src/pages/trajectory.test.tsx`, `client/src/pages/grids.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
test("Trajectory sits immediately after Industry in the navigation", () => {
  const order = NAVIGATION.map((n) => n.path);
  expect(order[order.indexOf("/industry") + 1]).toBe("/trajectory");
});

test("Trajectory shows how a competitor's argument evolved, with dated captures", () => {
  renderPage(<Trajectory />);
  expect(screen.getAllByTestId("timeline-entry").length).toBeGreaterThanOrEqual(5);
  expect(screen.getByText(/2021/)).toBeInTheDocument();
  expect(screen.getByText(/2026/)).toBeInTheDocument();
});

test("every timeline entry links to the archived capture", () => {
  renderPage(<Trajectory />);
  screen.getAllByTestId("timeline-entry").forEach((entry) =>
    expect(within(entry).getByRole("link", { name: /as we captured it/i })).toBeInTheDocument());
});

test("Competitors to Us no longer carries the multi-year timeline", () => {
  renderPage(<AboutUs />);
  expect(screen.queryByTestId("timeline-entry")).toBeNull();
  expect(screen.getByRole("link", { name: /view full history/i })).toBeInTheDocument();
});

test("Divisions and Industry render as multi-column grids", () => {
  setViewport(1440);
  renderPage(<Divisions />);
  expect(getComputedStyle(screen.getByTestId("card-grid")).display).toBe("grid");
});

test("grids collapse to one column below 1000px", () => {
  setViewport(390);
  renderPage(<Divisions />);
  expect(screen.getByTestId("card-grid")).toHaveAttribute("data-columns", "1");
});
```

- [ ] **Steps 2–4: Run, implement, run**

Add `{ path: "/trajectory", label: "Trajectory", group: "reference", icon: "history", primary: false }`
immediately after Industry. Move the timeline component out of `AboutUs` into `Trajectory`;
`AboutUs` keeps current claims with a "View full history" link.

Card grids: `repeat(auto-fill, minmax(420px, 1fr))`, one column below 1000px.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(client): card grids and a dedicated Trajectory tab"
```

---

## Self-review notes

**What this plan deliberately does not do:** recency windows, unread state, run history, as-of-date reconstruction, user preferences. All were considered and cut — this is a demo, and every one of them costs build time while adding nothing a viewer would notice in ten minutes.

**The two tests that carry the most weight** are `no consumer screen renders a machine value` (Task 3) and `Cited refuses to render content that has no citation` (Task 3). They make the two headline promises — plain language, and nothing unsourced — structural rather than aspirational. If either is weakened, the demo's core claim weakens with it.

**One judgement to be aware of:** `kits.yaml` assigns `partnership_ecosystem` to *Rival Strategy* rather than *Category & Market*. Partnerships read as strategy when a rival makes them and as market movement when the category does. The membership is config, so it is a one-line change if it looks wrong in the demo.

**Type consistency:** `Citation` is defined once in `citation.py`, mirrored in `client/src/api/types.ts`, and consumed unchanged by `SourceLink`, `Cited`, `KitTile`, `SignalCard`, `ComparisonTable` and the Ask transcript.

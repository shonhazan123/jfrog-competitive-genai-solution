# Foundation & Position Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docker compose up` produces a Postgres database containing five years of real, cited Sonatype-versus-JFrog positioning claims, extracted from archived versions of Sonatype's public comparison page.

**Architecture:** A FastAPI/SQLAlchemy backend split MVC-style, with all pipeline logic in `app/services/`. This plan builds layers 1–4 of the seven-layer pipeline (Collect, Capture, Normalise, Detect) plus the claim ledger they write into. No LLM code is written in this plan — the `agent/` package is created empty and stays empty until Plan 2. Every threshold lives in `config/*.yaml`, validated at boot.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 + pydantic-settings · httpx · selectolax · rapidfuzz · pytest · Postgres 17 + pgvector · Docker Compose

**Spec:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) (code-level) · [`docs/DESIGN.md`](../DESIGN.md) (solution design) · [`docs/PRD.md`](../PRD.md) (requirements)

## Global Constraints

- **No magic numbers in code.** Every threshold, budget, cap and weight is declared in `config/*.yaml`, validated by a Pydantic model at boot. A value hardcoded in a function is a defect.
- **`app` must never import `langchain`, `langgraph`, or `openai`.** Enforced by a test (Task 1). The `agent/` package is the only place those may appear.
- **`raw_capture` rows are append-only.** No code path updates or deletes one.
- **All collection honours `robots.txt`** and sends an identifying User-Agent from config. No source is fetched without a recorded robots decision.
- **Python 3.13**, SQLAlchemy 2.0 declarative style (`Mapped[...]` / `mapped_column`), Pydantic v2.
- **Prefer a maintained library over hand-written logic** — but check the last release date before adding one. A package whose most recent release is over a year old is a liability, not a saving; in that case write the small function and own it. Versions in `pyproject.toml` were verified against PyPI on 2026-08-26 and must not be changed from memory. If a dependency fails to resolve, check PyPI for the current version rather than guessing.
- **Tests run against real Postgres, never SQLite.** SQLite silently accepts JSON and array semantics that Postgres rejects, so a green SQLite suite proves nothing about the deployed database.
- **Tests must not touch the network.** Fixtures live in `tests/fixtures/`. The only network-touching test is marked `@pytest.mark.live` and excluded from the default run.
- **Timestamps are timezone-aware UTC** (`DateTime(timezone=True)`), never naive.
- Commit after every task. Conventional commit prefixes (`feat:`, `test:`, `chore:`).

---

## File Structure

| File | Responsibility |
|---|---|
| `docker-compose.yml` | Four services: `db`, `api`, `worker`, `client`. `client` is a placeholder until Plan 3. |
| `backend/pyproject.toml` | Dependencies and pytest configuration |
| `backend/app/settings.py` | Environment-derived settings (DB URL, user agent, API keys) |
| `backend/app/main.py` | FastAPI app, health router mount, config validation on startup |
| `backend/app/config/schema.py` | Pydantic models for every YAML config file |
| `backend/app/config/loader.py` | Reads, validates and caches `config/*.yaml` |
| `backend/app/models/base.py` | Declarative base, timestamp mixin |
| `backend/app/models/registry.py` | `Entity`, `Source` |
| `backend/app/models/capture.py` | `RawCapture`, `Document`, `PageSnapshot` |
| `backend/app/models/ledger.py` | `Claim`, `ClaimVersion`, `Evidence` |
| `backend/app/services/seeding.py` | YAML config → database rows |
| `backend/app/services/collection/robots.py` | `robots.txt` fetch, parse, cache, decision |
| `backend/app/services/collection/ratelimit.py` | Per-domain token bucket |
| `backend/app/services/collection/fetcher.py` | `Fetcher` protocol, `StaticFetcher`, `BrowserFetcher` stub |
| `backend/app/services/collection/wayback.py` | CDX snapshot listing and snapshot retrieval |
| `backend/app/services/normalization/elements.py` | `Element` dataclass and `ElementKind` |
| `backend/app/services/normalization/parsers/html_dom.py` | HTML → `list[Element]` |
| `backend/app/services/normalization/clean.py` | Text normalisation for hashing and quote matching |
| `backend/app/services/normalization/tracked_page.py` | Comparison-table extraction → `ComparisonRow` |
| `backend/app/services/detection/hashing.py` | Raw and normalised content hashes |
| `backend/app/services/detection/structural_diff.py` | `ComparisonRow` lists → `RowChange` list |
| `backend/app/services/backfill.py` | Orchestrates archive replay into the ledger |
| `backend/agent/__init__.py` | Empty. Reserved for Plan 2. |
| `backend/worker/jobs.py` | Callable job functions (scheduler wiring is Plan 2) |
| `tests/fixtures/` | Saved HTML captures used by every parser and diff test |

### Interfaces established by this plan

```python
# collection/fetcher.py
@dataclass(frozen=True)
class FetchResult:
    url: str; status: int; body: bytes | None
    etag: str | None; last_modified: str | None; not_modified: bool

class Fetcher(Protocol):
    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult: ...

# normalization/elements.py
class ElementKind(StrEnum):
    heading = "heading"; paragraph = "paragraph"; list_item = "list_item"
    table_row = "table_row"; code_block = "code_block"; quote = "quote"; caption = "caption"

@dataclass(frozen=True)
class Element:
    kind: ElementKind; text: str; order: int
    level: int | None = None
    path: tuple[str, ...] = ()
    attrs: dict[str, object] = field(default_factory=dict)

# normalization/clean.py
def normalize_text(s: str) -> str: ...

# normalization/tracked_page.py
@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    cells: dict[str, str]        # column label -> cell text

def extract_comparison_rows(elements: list[Element]) -> list[ComparisonRow]: ...

# detection/hashing.py
def content_hash(data: bytes) -> str: ...
def normalized_hash(text: str) -> str: ...

# detection/structural_diff.py
@dataclass(frozen=True)
class RowChange:
    dimension: str; column: str
    old_value: str | None; new_value: str | None
    kind: Literal["added", "removed", "substantive", "cosmetic"]

def diff_rows(old: list[ComparisonRow], new: list[ComparisonRow]) -> list[RowChange]: ...

# collection/wayback.py
@dataclass(frozen=True)
class Snapshot:
    timestamp: datetime; digest: str; original_url: str
    @property
    def raw_url(self) -> str: ...      # /web/<ts>id_/<original>

def list_snapshots(url: str, fetcher: Fetcher) -> list[Snapshot]: ...
```

---

### Task 1: Project skeleton, Compose stack, health endpoint

**Files:**
- Create: `.gitignore`, `docker-compose.yml`, `.env.example`, `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/settings.py`, `backend/app/main.py`, `backend/app/routers/health.py`, `backend/agent/__init__.py`
- Test: `tests/test_boundaries.py`, `tests/test_health.py`

**Interfaces:**
- Consumes: nothing
- Produces: `app.settings.Settings`, FastAPI app object `app.main.app`, `GET /health` → `{"status": "ok"}`

- [ ] **Step 1: Initialise the repository**

```bash
cd "C:/Users/shonh/OneDrive/Desktop/Projects/Jfrog_agent"
git init
git add docs/
git commit -m "docs: PRD, design and architecture"
```

- [ ] **Step 2: Write `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
node_modules/
data/blobs/
```

- [ ] **Step 3: Write `backend/pyproject.toml`**

All versions below were verified against PyPI on **2026-08-26**. Bounds are
`>=minor,<next-major` so patch updates flow but a major cannot break the build silently.

```toml
[project]
name = "jfrog-ci"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
  # web + db
  "fastapi>=0.141,<0.142",
  "uvicorn[standard]>=0.52,<0.53",
  "sqlalchemy>=2.0.52,<2.1",
  "alembic>=1.19,<2",
  "psycopg[binary]>=3.3,<4",
  "pydantic>=2.13,<3",
  "pydantic-settings>=2.15,<3",
  # collection
  "httpx>=0.28,<0.29",
  "protego>=0.6,<1",              # robots.txt — correct wildcard/Allow handling
  "pyrate-limiter>=4.4,<5",       # per-domain rate limiting
  "tenacity>=9.1,<10",            # retries with backoff
  "feedparser>=6.0.14,<7",
  # parsing
  "selectolax>=0.4.11,<0.5",      # fast DOM walk for tracked pages
  "trafilatura>=2.2,<3",          # article extraction + boilerplate removal
  "ftfy>=6.3,<7",                 # unicode / mojibake repair
  "dateparser>=1.4,<2",
  "rapidfuzz>=3.14,<4",
  # infra
  "pyyaml>=6.0.3,<7",
  "structlog>=26.1,<27",
]

[project.optional-dependencies]
dev = [
  "pytest>=9.1,<10",
  "pytest-asyncio>=1.4,<2",
  "testcontainers[postgres]>=4.15,<5",
  "respx>=0.23,<0.24",
  "ruff>=0.16,<0.17",
]

[tool.pytest.ini_options]
testpaths = ["../tests"]
markers = ["live: touches the network; excluded by default"]
addopts = "-m 'not live'"
```

**Deliberately not included, with reasons — do not add these:**

| Package | Why not |
|---|---|
| `waybackpy` | Last release 2022-03-15. The CDX call is ~15 lines of httpx (Task 10). An unmaintained dependency is a worse liability than a small function we own. |
| `unstructured`, `docling` | Correct abstraction, but both pull large ML-backed dependency trees and flatten a comparison table into one `Table` element we would have to re-parse. `unstructured` also caps at Python <3.14. |
| `langchain-postgres` | Version `0.0.17`, pre-1.0, six months stale. Hybrid RRF is written as raw SQL regardless, so it earns nothing. Use the `pgvector` client directly (Plan 3). |
| `premailer` | Last release 2021. Use `css-inline` for email CSS inlining (Plan 3). |
| `beautifulsoup4` | `selectolax` is faster and sufficient; two HTML parsers is one too many. |

**Arriving in later plans, not now:** `langgraph>=1.2,<2`, `langgraph-checkpoint-postgres>=3.1,<4`, `langchain-openai>=1.6,<2`, `openai>=3.3,<4`, `tiktoken>=0.14,<0.15`, `nh3>=0.3,<0.4` (Plan 2); `pgvector>=0.5,<0.6`, `apscheduler>=3.11,<4`, `jinja2>=3.1,<4`, `css-inline>=0.21,<0.22` (Plan 3).

- [ ] **Step 4: Write the boundary test — this is the constraint that must never silently break**

`tests/test_boundaries.py`:

```python
from pathlib import Path

FORBIDDEN = ("langchain", "langgraph", "openai")
APP = Path(__file__).resolve().parents[1] / "backend" / "app"

def test_app_package_never_imports_llm_libraries():
    offenders = []
    for py in APP.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for lib in FORBIDDEN:
            if f"import {lib}" in text or f"from {lib}" in text:
                offenders.append(f"{py.relative_to(APP)} imports {lib}")
    assert offenders == [], (
        "app/ must not import LLM libraries; that belongs in agent/. " + "; ".join(offenders)
    )
```

- [ ] **Step 5: Run it to verify it passes on an empty app**

Run: `pytest tests/test_boundaries.py -v`
Expected: PASS (nothing to violate yet — this test guards the boundary from here on)

- [ ] **Step 6: Write the failing health test**

`tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_returns_ok():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 7: Run it to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 8: Write `backend/app/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ci:ci@db:5432/ci"
    config_dir: str = "/app/config"
    blob_dir: str = "/app/data/blobs"
    user_agent: str = "jfrog-ci-bot/0.1 (+contact: shonhazan19955@gmail.com)"

settings = Settings()
```

- [ ] **Step 9: Write `backend/app/routers/health.py` and `backend/app/main.py`**

```python
# routers/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# main.py
from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="JFrog Competitive Intelligence")
app.include_router(health.router)
```

- [ ] **Step 10: Run the health test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 11: Write `docker-compose.yml` and `.env.example`**

```yaml
services:
  db:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: ci
      POSTGRES_PASSWORD: ci
      POSTGRES_DB: ci
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ci"]
      interval: 3s
      retries: 20

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql+psycopg://ci:ci@db:5432/ci
    volumes: ["./config:/app/config:ro", "blobs:/app/data/blobs"]
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }

  worker:
    build: ./backend
    command: python -m worker.main
    environment:
      DATABASE_URL: postgresql+psycopg://ci:ci@db:5432/ci
    volumes: ["./config:/app/config:ro", "blobs:/app/data/blobs"]
    depends_on:
      db: { condition: service_healthy }

volumes:
  pgdata:
  blobs:
```

`.env.example`:

```
OPENAI_API_KEY=
SMTP_USER=
SMTP_APP_PASSWORD=
```

- [ ] **Step 12: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
```

- [ ] **Step 13: Create the empty agent package**

```bash
mkdir -p backend/agent && echo "# Reserved for Plan 2 — LLM code lives only here." > backend/agent/__init__.py
```

- [ ] **Step 14: Verify the stack starts**

Run: `docker compose up -d db && docker compose run --rm api pytest -v`
Expected: all tests PASS

- [ ] **Step 15: Commit**

```bash
git add .
git commit -m "feat: project skeleton, compose stack, health endpoint, boundary test"
```

---

### Task 2: Configuration schema, loader and boot-time validation

**Files:**
- Create: `config/entities.yaml`, `config/sources.yaml`, `config/chunking.yaml`, `config/verification.yaml`, `backend/app/config/schema.py`, `backend/app/config/loader.py`
- Modify: `backend/app/main.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `app.settings.settings.config_dir`
- Produces: `app.config.loader.load_config() -> AppConfig`; `AppConfig.entities: list[EntityConfig]`, `AppConfig.sources: list[SourceConfig]`, `AppConfig.verification: VerificationConfig`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:

```python
import pytest
from pydantic import ValidationError
from app.config.schema import VerificationConfig
from app.config.loader import load_config

def test_loads_and_validates_all_config_files(tmp_path):
    config = load_config()
    assert any(e.slug == "sonatype" for e in config.entities)
    assert any(s.mode == "snapshot" for s in config.sources)

def test_rejects_out_of_range_threshold():
    with pytest.raises(ValidationError):
        VerificationConfig.model_validate(
            {"quote_matching": {"fuzzy": {"accept_threshold": 150, "min_quote_chars": 25}}}
        )
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Write `backend/app/config/schema.py`**

```python
from typing import Literal
from pydantic import BaseModel, Field

class EntityConfig(BaseModel):
    slug: str
    name: str
    kind: Literal["competitor", "self", "industry"]
    tier: int = Field(ge=1, le=3)
    aliases: list[str] = []

class SourceConfig(BaseModel):
    key: str
    entity: str
    url: str
    kind: Literal["atom", "rss", "html_page", "api", "sitemap"]
    mode: Literal["feed", "snapshot"]
    reliability_grade: Literal["A", "B", "C", "D", "E", "F"]
    is_primary: bool
    check_frequency_minutes: int = Field(ge=5)
    requires_js: bool = False
    row_selector: str | None = None      # snapshot sources only

class FuzzyConfig(BaseModel):
    enabled: bool = True
    accept_threshold: int = Field(ge=0, le=100)
    min_quote_chars: int = Field(ge=1)

class QuoteMatchingConfig(BaseModel):
    fuzzy: FuzzyConfig

class VerificationConfig(BaseModel):
    quote_matching: QuoteMatchingConfig

class ChunkingConfig(BaseModel):
    target_tokens: int = Field(ge=100)
    max_tokens: int = Field(ge=100)
    break_on_heading_level: int = Field(ge=1, le=6)
    never_split: list[str]

class AppConfig(BaseModel):
    entities: list[EntityConfig]
    sources: list[SourceConfig]
    verification: VerificationConfig
    chunking: ChunkingConfig
```

- [ ] **Step 4: Write `backend/app/config/loader.py`**

```python
from functools import lru_cache
from pathlib import Path
import yaml
from app.config.schema import AppConfig
from app.settings import settings

def _read(name: str) -> dict:
    return yaml.safe_load((Path(settings.config_dir) / name).read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    return AppConfig(
        entities=_read("entities.yaml")["entities"],
        sources=_read("sources.yaml")["sources"],
        verification=_read("verification.yaml"),
        chunking=_read("chunking.yaml"),
    )
```

- [ ] **Step 5: Write the YAML files**

`config/entities.yaml`:

```yaml
entities:
  - { slug: jfrog,     name: JFrog,           kind: self,       tier: 1, aliases: [Artifactory, Xray] }
  - { slug: sonatype,  name: Sonatype,        kind: competitor, tier: 1, aliases: [Nexus, "Nexus Repository"] }
  - { slug: github,    name: GitHub Packages, kind: competitor, tier: 2, aliases: ["GitHub Packages"] }
  - { slug: gitlab,    name: GitLab,          kind: competitor, tier: 2, aliases: [] }
  - { slug: harbor,    name: Harbor,          kind: competitor, tier: 2, aliases: [goharbor] }
  - { slug: industry,  name: Industry,        kind: industry,   tier: 1, aliases: [] }
```

`config/sources.yaml`:

```yaml
sources:
  - key: sonatype_compare_jfrog
    entity: sonatype
    url: https://www.sonatype.com/compare/sonatype-nexus-versus-jfrog-artifactory
    kind: html_page
    mode: snapshot
    reliability_grade: A
    is_primary: true
    check_frequency_minutes: 1440
    row_selector: "table tr"

  - key: sonatype_nexus_releases
    entity: sonatype
    url: https://github.com/sonatype/nexus-public/releases.atom
    kind: atom
    mode: feed
    reliability_grade: A
    is_primary: true
    check_frequency_minutes: 360

  - key: harbor_releases
    entity: harbor
    url: https://github.com/goharbor/harbor/releases.atom
    kind: atom
    mode: feed
    reliability_grade: A
    is_primary: true
    check_frequency_minutes: 360
```

`config/verification.yaml`:

```yaml
quote_matching:
  fuzzy:
    enabled: true
    accept_threshold: 98
    min_quote_chars: 25
```

`config/chunking.yaml`:

```yaml
target_tokens: 800
max_tokens: 1200
break_on_heading_level: 2
never_split: [table_row, list_item, code_block]
```

- [ ] **Step 6: Validate config at application startup**

Add to `backend/app/main.py`:

```python
from contextlib import asynccontextmanager
from app.config.loader import load_config

@asynccontextmanager
async def lifespan(_: FastAPI):
    load_config()          # raises ValidationError on bad config, before serving traffic
    yield

app = FastAPI(title="JFrog Competitive Intelligence", lifespan=lifespan)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: PASS (both tests)

- [ ] **Step 8: Commit**

```bash
git add config backend/app/config backend/app/main.py tests/test_config.py
git commit -m "feat: config schema, loader and boot-time validation"
```

---

### Task 3: Database models and initial migration

**Files:**
- Create: `backend/app/models/base.py`, `backend/app/models/registry.py`, `backend/app/models/capture.py`, `backend/app/models/ledger.py`, `backend/app/db/session.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: `app.settings.settings.database_url`
- Produces: `Entity`, `Source`, `RawCapture`, `Document`, `PageSnapshot`, `Claim`, `ClaimVersion`, `Evidence`; `app.db.session.get_session()`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:

```python
from datetime import UTC, datetime
from app.models.registry import Entity, Source
from app.models.ledger import Claim, ClaimVersion

def test_claim_carries_subject_and_asserter_separately(session):
    jfrog = Entity(slug="jfrog", name="JFrog", kind="self", tier=1)
    sona = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    session.add_all([jfrog, sona])
    session.flush()

    claim = Claim(
        subject_entity_id=jfrog.id,
        asserting_entity_id=sona.id,
        claim_text="JFrog has hidden costs for storage and transfer",
        claim_type="pricing",
        capability_tags=["pricing_model"],
        reliability_grade="A",
        first_seen_at=datetime.now(UTC),
    )
    session.add(claim)
    session.flush()

    assert claim.subject_entity_id != claim.asserting_entity_id
    assert claim.status == "active"

def test_claim_version_records_a_before_and_after(session, sample_claim):
    version = ClaimVersion(
        claim_id=sample_claim.id,
        old_text="Limited",
        new_text="Very limited, not proactive",
        change_kind="substantive",
        changed_at=datetime.now(UTC),
    )
    session.add(version)
    session.flush()
    assert version.old_text != version.new_text
```

- [ ] **Step 2: Write `tests/conftest.py` providing the `session` and `sample_claim` fixtures**

**Postgres, not SQLite.** SQLite accepts JSON and array semantics Postgres rejects, and pgvector
does not exist there at all — a green SQLite suite would prove nothing about the deployed
database. The container starts once per session and each test gets a rolled-back transaction.

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from app.models.base import Base

@pytest.fixture(scope="session")
def engine():
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as pg:
        engine = create_engine(pg.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine

@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    with sessionmaker(bind=connection)() as s:
        yield s
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_claim(session):
    from datetime import UTC, datetime
    from app.models.registry import Entity
    from app.models.ledger import Claim
    a = Entity(slug="jfrog", name="JFrog", kind="self", tier=1)
    b = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    session.add_all([a, b]); session.flush()
    claim = Claim(
        subject_entity_id=a.id, asserting_entity_id=b.id,
        claim_text="x", claim_type="pricing", capability_tags=[],
        reliability_grade="A", first_seen_at=datetime.now(UTC),
    )
    session.add(claim); session.flush()
    return claim
```

- [ ] **Step 3: Run to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 4: Write `backend/app/models/base.py`**

```python
from datetime import UTC, datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

- [ ] **Step 5: Write `backend/app/models/registry.py`**

```python
from sqlalchemy import Boolean, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Entity(Base, TimestampMixin):
    __tablename__ = "entity"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))
    tier: Mapped[int] = mapped_column(Integer)
    aliases: Mapped[list] = mapped_column(JSON, default=list)

class Source(Base, TimestampMixin):
    __tablename__ = "source"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    url: Mapped[str] = mapped_column(String(1024))
    kind: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(16))
    reliability_grade: Mapped[str] = mapped_column(String(1))
    is_primary: Mapped[bool] = mapped_column(Boolean)
    check_frequency_minutes: Mapped[int] = mapped_column(Integer)
    requires_js: Mapped[bool] = mapped_column(Boolean, default=False)
    row_selector: Mapped[str | None] = mapped_column(String(256), nullable=True)
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(256), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 6: Write `backend/app/models/capture.py`**

```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class RawCapture(Base, TimestampMixin):
    """Append-only. No code path may update or delete a row of this table."""
    __tablename__ = "raw_capture"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    blob_path: Mapped[str] = mapped_column(String(512))
    extracted_text: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(String(16), default="live")  # live | archive

class Document(Base, TimestampMixin):
    __tablename__ = "document"
    id: Mapped[int] = mapped_column(primary_key=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    canonical_url: Mapped[str] = mapped_column(String(1024))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clean_text: Mapped[str] = mapped_column(Text)

class PageSnapshot(Base, TimestampMixin):
    __tablename__ = "page_snapshot"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    text_hash: Mapped[str] = mapped_column(String(64))
    rows: Mapped[list] = mapped_column(JSON)   # serialised list[ComparisonRow]
```

- [ ] **Step 7: Write `backend/app/models/ledger.py`**

```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Claim(Base, TimestampMixin):
    __tablename__ = "claim"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    asserting_entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    claim_text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(32))
    capability_tags: Mapped[list] = mapped_column(JSON, default=list)
    dimension: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    reliability_grade: Mapped[str] = mapped_column(String(1))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ClaimVersion(Base, TimestampMixin):
    __tablename__ = "claim_version"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"))
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_kind: Mapped[str] = mapped_column(String(16))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"))
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    quote: Mapped[str] = mapped_column(Text)
    quote_offset: Mapped[int] = mapped_column(Integer)
```

- [ ] **Step 8: Write `backend/app/db/session.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_session():
    with SessionLocal() as session:
        yield session
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS (both tests)

- [ ] **Step 10: Generate and apply the migration**

```bash
docker compose run --rm api alembic revision --autogenerate -m "initial schema"
docker compose run --rm api alembic upgrade head
```

- [ ] **Step 11: Commit**

```bash
git add backend/app/models backend/app/db backend/alembic* tests/test_models.py tests/conftest.py
git commit -m "feat: ledger schema with subject/asserting entity split"
```

---

### Task 4: Seed configuration into the database

**Files:**
- Create: `backend/app/services/seeding.py`
- Test: `tests/test_seeding.py`

**Interfaces:**
- Consumes: `load_config()`, `Entity`, `Source`
- Produces: `app.services.seeding.seed(session) -> SeedReport` where `SeedReport` has `.entities_created`, `.sources_created`, `.sources_updated`

- [ ] **Step 1: Write the failing test**

```python
from app.services.seeding import seed

def test_seed_is_idempotent(session):
    first = seed(session)
    second = seed(session)
    assert first.entities_created > 0
    assert second.entities_created == 0
    assert second.sources_created == 0

def test_seed_links_sources_to_entities(session):
    from app.models.registry import Source, Entity
    seed(session)
    source = session.query(Source).filter_by(key="sonatype_compare_jfrog").one()
    entity = session.get(Entity, source.entity_id)
    assert entity.slug == "sonatype"
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_seeding.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.seeding'`

- [ ] **Step 3: Implement `seed`**

```python
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.config.loader import load_config
from app.models.registry import Entity, Source

@dataclass
class SeedReport:
    entities_created: int = 0
    sources_created: int = 0
    sources_updated: int = 0

def seed(session: Session) -> SeedReport:
    config, report = load_config(), SeedReport()

    by_slug: dict[str, Entity] = {e.slug: e for e in session.query(Entity).all()}
    for spec in config.entities:
        if spec.slug not in by_slug:
            entity = Entity(**spec.model_dump())
            session.add(entity)
            by_slug[spec.slug] = entity
            report.entities_created += 1
    session.flush()

    existing = {s.key: s for s in session.query(Source).all()}
    for spec in config.sources:
        payload = spec.model_dump(exclude={"entity"}) | {"entity_id": by_slug[spec.entity].id}
        if spec.key in existing:
            for field, value in payload.items():
                setattr(existing[spec.key], field, value)
            report.sources_updated += 1
        else:
            session.add(Source(**payload))
            report.sources_created += 1
    session.commit()
    return report
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_seeding.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/seeding.py tests/test_seeding.py
git commit -m "feat: idempotent config seeding into the database"
```

---

### Task 5: Robots, rate limiting and the static fetcher

**Files:**
- Create: `backend/app/services/collection/robots.py`, `backend/app/services/collection/ratelimit.py`, `backend/app/services/collection/fetcher.py`
- Test: `tests/test_fetcher.py`

**Interfaces:**
- Consumes: `settings.user_agent`
- Produces: `FetchResult`, `Fetcher` protocol, `StaticFetcher`, `BrowserFetcher`, `RobotsCache.allowed(url) -> bool`, `RobotsCache.crawl_delay(url) -> float | None`, `DomainRateLimiter.acquire(url)`

- [ ] **Step 1: Write the failing test**

```python
import httpx, pytest
from app.services.collection.fetcher import StaticFetcher, BrowserFetcher
from app.services.collection.robots import RobotsCache

def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))

def test_conditional_get_reports_not_modified():
    def handler(request):
        assert request.headers["If-None-Match"] == 'W/"abc"'
        return httpx.Response(304)
    result = StaticFetcher(client=_client(handler)).fetch("https://x.test/p", etag='W/"abc"')
    assert result.not_modified is True
    assert result.body is None

def test_successful_fetch_captures_etag_and_body():
    def handler(request):
        return httpx.Response(200, content=b"<html>hi</html>", headers={"ETag": 'W/"z"'})
    result = StaticFetcher(client=_client(handler)).fetch("https://x.test/p")
    assert result.status == 200
    assert result.body == b"<html>hi</html>"
    assert result.etag == 'W/"z"'

def test_sends_identifying_user_agent():
    seen = {}
    def handler(request):
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, content=b"")
    StaticFetcher(client=_client(handler)).fetch("https://x.test/p")
    assert "jfrog-ci-bot" in seen["ua"]

def test_robots_disallow_is_respected():
    def handler(request):
        return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    cache = RobotsCache(client=_client(handler))
    assert cache.allowed("https://x.test/public") is True
    assert cache.allowed("https://x.test/private/page") is False

def test_browser_fetcher_fails_loudly():
    with pytest.raises(NotImplementedError, match="browser rendering"):
        BrowserFetcher().fetch("https://x.test/p")
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_fetcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.collection'`

- [ ] **Step 3: Implement `robots.py`**

Uses **protego**, not `urllib.robotparser`. The stdlib parser mishandles wildcards and `Allow`
precedence, and ignores `Crawl-delay`. Robots compliance is a demonstrated feature of this
product, so it must actually be correct.

```python
from urllib.parse import urlparse
import httpx
from protego import Protego
from app.settings import settings

class RobotsCache:
    """One parsed robots.txt per origin, cached for the process lifetime."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10, follow_redirects=True)
        self._parsers: dict[str, Protego] = {}

    def _parser_for(self, origin: str) -> Protego:
        if origin not in self._parsers:
            try:
                response = self._client.get(f"{origin}/robots.txt")
                text = response.text if response.status_code == 200 else ""
            except httpx.HTTPError:
                text = ""                 # unreachable robots.txt -> treat as permissive
            self._parsers[origin] = Protego.parse(text)
        return self._parsers[origin]

    def allowed(self, url: str) -> bool:
        parts = urlparse(url)
        return self._parser_for(f"{parts.scheme}://{parts.netloc}").can_fetch(
            url, settings.user_agent
        )

    def crawl_delay(self, url: str) -> float | None:
        parts = urlparse(url)
        return self._parser_for(f"{parts.scheme}://{parts.netloc}").crawl_delay(
            settings.user_agent
        )
```

- [ ] **Step 4: Implement `ratelimit.py`**

Uses **pyrate-limiter** rather than hand-rolled threading. One bucket per domain, keyed by
netloc, blocking until a slot frees.

```python
from urllib.parse import urlparse
from pyrate_limiter import Duration, Limiter, Rate

class DomainRateLimiter:
    """Per-domain politeness limit. Blocks rather than raising when exhausted."""

    def __init__(self, per_minute: int = 20, max_delay_ms: int = 60_000) -> None:
        self._limiter = Limiter(
            Rate(per_minute, Duration.MINUTE),
            raise_when_fail=False,
            max_delay=max_delay_ms,
        )

    def acquire(self, url: str) -> None:
        self._limiter.try_acquire(urlparse(url).netloc)
```

Note the rename: `TokenBucket` → `DomainRateLimiter`, and `StaticFetcher` takes a
`limiter: DomainRateLimiter` parameter rather than `bucket: TokenBucket`. Update the
`fetcher.py` import and constructor in Step 5 accordingly.

- [ ] **Step 5: Implement `fetcher.py`**

```python
from dataclasses import dataclass
from typing import Protocol
import httpx
from app.services.collection.ratelimit import DomainRateLimiter
from app.settings import settings

@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    body: bytes | None
    etag: str | None
    last_modified: str | None
    not_modified: bool

class Fetcher(Protocol):
    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult: ...

class StaticFetcher:
    def __init__(self, client: httpx.Client | None = None,
                 limiter: DomainRateLimiter | None = None) -> None:
        self._client = client or httpx.Client(timeout=20, follow_redirects=True)
        self._limiter = limiter or DomainRateLimiter()

    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult:
        self._limiter.acquire(url)
        headers = {"User-Agent": settings.user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        response = self._client.get(url, headers=headers)
        not_modified = response.status_code == 304
        return FetchResult(
            url=url,
            status=response.status_code,
            body=None if not_modified else response.content,
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
            not_modified=not_modified,
        )

class BrowserFetcher:
    """Adapter seam for JavaScript-rendered sources. Not built — see ARCHITECTURE.md §2."""

    def fetch(self, url: str, etag: str | None = None,
              last_modified: str | None = None) -> FetchResult:
        raise NotImplementedError(
            f"{url} requires browser rendering; no BrowserFetcher is configured. "
            "Mark the source requires_js=false or add a Playwright service."
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_fetcher.py -v`
Expected: PASS (all five tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/collection tests/test_fetcher.py
git commit -m "feat: polite static fetcher with robots, rate limiting and conditional GET"
```

---

### Task 6: HTML element parser

**Files:**
- Create: `backend/app/services/normalization/elements.py`, `backend/app/services/normalization/parsers/html_dom.py`
- Test: `tests/test_html_parser.py`, `tests/fixtures/comparison_sample.html`

**Interfaces:**
- Consumes: nothing
- Produces: `ElementKind`, `Element`, `parse_html(html: str) -> list[Element]`

- [ ] **Step 1: Write the fixture `tests/fixtures/comparison_sample.html`**

```html
<html><body>
  <nav>Products Pricing</nav>
  <h1>Sonatype vs JFrog</h1>
  <h2>Security</h2>
  <p>Sonatype blocks malicious components at the gate.</p>
  <table>
    <tr><th>Capability</th><th>Sonatype</th><th>JFrog</th></tr>
    <tr><td>Malware detection</td><td>Fully identifies</td><td>Limited</td></tr>
    <tr><td>SBOM</td><td>Full management</td><td>Export only</td></tr>
  </table>
  <script>var x = 1;</script>
  <footer>© Sonatype</footer>
</body></html>
```

- [ ] **Step 2: Write the failing test**

```python
from pathlib import Path
from app.services.normalization.elements import ElementKind
from app.services.normalization.parsers.html_dom import parse_html

HTML = (Path(__file__).parent / "fixtures" / "comparison_sample.html").read_text(encoding="utf-8")

def test_headings_carry_their_level():
    elements = parse_html(HTML)
    headings = [e for e in elements if e.kind is ElementKind.heading]
    assert [(h.text, h.level) for h in headings] == [("Sonatype vs JFrog", 1), ("Security", 2)]

def test_paragraph_inherits_the_heading_path():
    elements = parse_html(HTML)
    paragraph = next(e for e in elements if e.kind is ElementKind.paragraph)
    assert paragraph.path == ("Sonatype vs JFrog", "Security")

def test_table_rows_preserve_cells_in_order():
    elements = parse_html(HTML)
    rows = [e for e in elements if e.kind is ElementKind.table_row]
    assert rows[1].attrs["cells"] == ["Malware detection", "Fully identifies", "Limited"]

def test_script_nav_and_footer_are_dropped():
    text = " ".join(e.text for e in parse_html(HTML))
    assert "var x" not in text
    assert "Products Pricing" not in text
    assert "© Sonatype" not in text
```

- [ ] **Step 3: Run to verify it fails**

Run: `pytest tests/test_html_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.normalization'`

- [ ] **Step 4: Implement `elements.py`**

```python
from dataclasses import dataclass, field
from enum import StrEnum

class ElementKind(StrEnum):
    heading = "heading"
    paragraph = "paragraph"
    list_item = "list_item"
    table_row = "table_row"
    code_block = "code_block"
    quote = "quote"
    caption = "caption"

@dataclass(frozen=True)
class Element:
    kind: ElementKind
    text: str
    order: int
    level: int | None = None
    path: tuple[str, ...] = ()
    attrs: dict = field(default_factory=dict)
```

- [ ] **Step 5: Implement `parsers/html_dom.py`**

```python
from selectolax.parser import HTMLParser
from app.services.normalization.elements import Element, ElementKind

DROP = {"script", "style", "nav", "footer", "noscript", "svg", "form", "aside"}
TAG_KINDS = {"p": ElementKind.paragraph, "li": ElementKind.list_item,
             "blockquote": ElementKind.quote, "pre": ElementKind.code_block,
             "figcaption": ElementKind.caption}

def parse_html(html: str) -> list[Element]:
    tree = HTMLParser(html)
    for tag in DROP:
        for node in tree.css(tag):
            node.decompose()

    elements: list[Element] = []
    path: list[str] = []
    order = 0

    for node in tree.css("h1, h2, h3, h4, h5, h6, p, li, blockquote, pre, figcaption, tr"):
        text = " ".join(node.text(separator=" ").split())
        if not text:
            continue

        if node.tag.startswith("h") and len(node.tag) == 2 and node.tag[1].isdigit():
            level = int(node.tag[1])
            del path[level - 1:]
            path.append(text)
            elements.append(Element(ElementKind.heading, text, order, level=level,
                                    path=tuple(path[:-1])))
        elif node.tag == "tr":
            cells = [" ".join(c.text(separator=" ").split())
                     for c in node.css("td, th")]
            elements.append(Element(ElementKind.table_row, " │ ".join(cells), order,
                                    path=tuple(path), attrs={"cells": cells}))
        else:
            elements.append(Element(TAG_KINDS[node.tag], text, order, path=tuple(path)))
        order += 1

    return elements
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_html_parser.py -v`
Expected: PASS (all four tests)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/normalization tests/test_html_parser.py tests/fixtures
git commit -m "feat: element-first HTML parser with heading paths and table rows"
```

---

### Task 7: Text normalisation and content hashing

**Files:**
- Create: `backend/app/services/normalization/clean.py`, `backend/app/services/detection/hashing.py`
- Test: `tests/test_normalization.py`

**Interfaces:**
- Consumes: nothing
- Produces: `normalize_text(s: str) -> str`, `content_hash(data: bytes) -> str`, `normalized_hash(text: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
from app.services.normalization.clean import normalize_text
from app.services.detection.hashing import content_hash, normalized_hash

def test_decodes_entities_and_normalises_quotes():
    assert normalize_text("JFrog&nbsp;&amp; \u201cNexus\u201d") == 'jfrog & "nexus"'

def test_collapses_whitespace_and_strips_zero_width():
    assert normalize_text("a\u200b  b\n\nc") == "a b c"

def test_cosmetic_change_produces_the_same_normalised_hash():
    a = normalized_hash("Malware detection:  Limited")
    b = normalized_hash("Malware   detection: Limited\n")
    assert a == b

def test_substantive_change_produces_a_different_hash():
    a = normalized_hash("Malware detection: Limited")
    b = normalized_hash("Malware detection: Very limited, not proactive")
    assert a != b

def test_content_hash_is_stable_and_hex():
    digest = content_hash(b"abc")
    assert digest == content_hash(b"abc")
    assert len(digest) == 64
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_normalization.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.normalization.clean'`

- [ ] **Step 3: Implement `clean.py`**

```python
import html
import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u00ad"), None)
_WHITESPACE = re.compile(r"\s+")

def normalize_text(s: str) -> str:
    s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_ZERO_WIDTH)
    s = s.replace("\u00a0", " ")
    return _WHITESPACE.sub(" ", s).strip().lower()
```

- [ ] **Step 4: Implement `hashing.py`**

```python
import hashlib
from app.services.normalization.clean import normalize_text

def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def normalized_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_normalization.py -v`
Expected: PASS (all five tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/normalization/clean.py backend/app/services/detection tests/test_normalization.py
git commit -m "feat: text normalisation and content hashing"
```

---

### Task 8: Comparison-table extraction

**Files:**
- Create: `backend/app/services/normalization/tracked_page.py`
- Test: `tests/test_tracked_page.py`

**Interfaces:**
- Consumes: `Element`, `ElementKind`
- Produces: `ComparisonRow`, `extract_comparison_rows(elements: list[Element]) -> list[ComparisonRow]`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from app.services.normalization.parsers.html_dom import parse_html
from app.services.normalization.tracked_page import extract_comparison_rows

HTML = (Path(__file__).parent / "fixtures" / "comparison_sample.html").read_text(encoding="utf-8")

def test_first_row_becomes_column_headers_not_a_row():
    rows = extract_comparison_rows(parse_html(HTML))
    assert [r.dimension for r in rows] == ["Malware detection", "SBOM"]

def test_cells_are_keyed_by_column_label():
    rows = extract_comparison_rows(parse_html(HTML))
    assert rows[0].cells == {"Sonatype": "Fully identifies", "JFrog": "Limited"}

def test_rows_with_a_single_cell_are_ignored():
    from app.services.normalization.elements import Element, ElementKind
    lone = [Element(ElementKind.table_row, "x", 0, attrs={"cells": ["x"]})]
    assert extract_comparison_rows(lone) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_tracked_page.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.normalization.tracked_page'`

- [ ] **Step 3: Implement `tracked_page.py`**

```python
from dataclasses import dataclass
from app.services.normalization.elements import Element, ElementKind

@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    cells: dict[str, str]

def extract_comparison_rows(elements: list[Element]) -> list[ComparisonRow]:
    table_rows = [e for e in elements
                  if e.kind is ElementKind.table_row and len(e.attrs.get("cells", [])) >= 2]
    if not table_rows:
        return []

    headers = table_rows[0].attrs["cells"][1:]
    rows: list[ComparisonRow] = []
    for element in table_rows[1:]:
        cells = element.attrs["cells"]
        rows.append(ComparisonRow(
            dimension=cells[0],
            cells={label: value for label, value in zip(headers, cells[1:])},
        ))
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tracked_page.py -v`
Expected: PASS (all three tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/normalization/tracked_page.py tests/test_tracked_page.py
git commit -m "feat: comparison-table extraction into dimension rows"
```

---

### Task 9: Structural diff

**Files:**
- Create: `backend/app/services/detection/structural_diff.py`
- Test: `tests/test_structural_diff.py`

**Interfaces:**
- Consumes: `ComparisonRow`, `normalize_text`
- Produces: `RowChange`, `diff_rows(old, new) -> list[RowChange]`

- [ ] **Step 1: Write the failing test**

```python
from app.services.normalization.tracked_page import ComparisonRow
from app.services.detection.structural_diff import diff_rows

def row(dim, jfrog): return ComparisonRow(dimension=dim, cells={"JFrog": jfrog})

def test_no_change_yields_nothing():
    assert diff_rows([row("Malware", "Limited")], [row("Malware", "Limited")]) == []

def test_whitespace_and_case_change_is_cosmetic():
    changes = diff_rows([row("Malware", "Limited")], [row("Malware", "  limited ")])
    assert [c.kind for c in changes] == ["cosmetic"]

def test_reworded_cell_is_substantive_and_carries_before_and_after():
    changes = diff_rows([row("Malware", "Limited")],
                        [row("Malware", "Very limited, not proactive")])
    assert len(changes) == 1
    assert changes[0].kind == "substantive"
    assert changes[0].dimension == "Malware"
    assert changes[0].column == "JFrog"
    assert changes[0].old_value == "Limited"
    assert changes[0].new_value == "Very limited, not proactive"

def test_new_dimension_is_added_and_missing_one_is_removed():
    changes = diff_rows([row("Malware", "Limited")], [row("SBOM", "Export only")])
    assert sorted(c.kind for c in changes) == ["added", "removed"]

def test_row_reordering_is_not_a_change():
    old = [row("Malware", "Limited"), row("SBOM", "Export only")]
    new = [row("SBOM", "Export only"), row("Malware", "Limited")]
    assert diff_rows(old, new) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_structural_diff.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.detection.structural_diff'`

- [ ] **Step 3: Implement `structural_diff.py`**

```python
from dataclasses import dataclass
from typing import Literal
from app.services.normalization.clean import normalize_text
from app.services.normalization.tracked_page import ComparisonRow

ChangeKind = Literal["added", "removed", "substantive", "cosmetic"]

@dataclass(frozen=True)
class RowChange:
    dimension: str
    column: str
    old_value: str | None
    new_value: str | None
    kind: ChangeKind

def _key(dimension: str) -> str:
    return normalize_text(dimension)

def diff_rows(old: list[ComparisonRow], new: list[ComparisonRow]) -> list[RowChange]:
    """Compare by dimension key, so row reordering is not reported as a change."""
    old_by_key = {_key(r.dimension): r for r in old}
    new_by_key = {_key(r.dimension): r for r in new}
    changes: list[RowChange] = []

    for key, new_row in new_by_key.items():
        old_row = old_by_key.get(key)
        if old_row is None:
            for column, value in new_row.cells.items():
                changes.append(RowChange(new_row.dimension, column, None, value, "added"))
            continue
        for column, new_value in new_row.cells.items():
            old_value = old_row.cells.get(column)
            if old_value == new_value:
                continue
            if old_value is not None and normalize_text(old_value) == normalize_text(new_value):
                kind: ChangeKind = "cosmetic"
            else:
                kind = "substantive" if old_value is not None else "added"
            changes.append(RowChange(new_row.dimension, column, old_value, new_value, kind))

    for key, old_row in old_by_key.items():
        if key not in new_by_key:
            for column, value in old_row.cells.items():
                changes.append(RowChange(old_row.dimension, column, value, None, "removed"))

    return changes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_structural_diff.py -v`
Expected: PASS (all five tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/detection/structural_diff.py tests/test_structural_diff.py
git commit -m "feat: structural diff distinguishing cosmetic from substantive change"
```

---

### Task 10: Wayback CDX client

**Files:**
- Create: `backend/app/services/collection/wayback.py`
- Test: `tests/test_wayback.py`

**Interfaces:**
- Consumes: `Fetcher`, `FetchResult`
- Produces: `Snapshot`, `list_snapshots(url: str, fetcher: Fetcher) -> list[Snapshot]`

- [ ] **Step 1: Write the failing test**

```python
import json
from datetime import UTC
import pytest
from app.services.collection.fetcher import FetchResult
from app.services.collection.wayback import Snapshot, list_snapshots

CDX = json.dumps([
    ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"],
    ["com,sonatype)/compare", "20210227194637", "https://www.sonatype.com/compare",
     "text/html", "200", "O2KLUGIMT67GWKVC4JFCXMA63AD4VE6E", "20225"],
    ["com,sonatype)/compare", "20260510141655", "https://www.sonatype.com/compare",
     "text/html", "200", "BG4PXMHZX4WVWVNBC66Q6EBE4R6WIWDS", "38371"],
]).encode()

class FakeFetcher:
    def __init__(self, body): self.body, self.calls = body, []
    def fetch(self, url, etag=None, last_modified=None):
        self.calls.append(url)
        return FetchResult(url, 200, self.body, None, None, False)

def test_parses_snapshots_and_drops_the_header_row():
    snapshots = list_snapshots("https://www.sonatype.com/compare", FakeFetcher(CDX))
    assert len(snapshots) == 2
    assert snapshots[0].digest == "O2KLUGIMT67GWKVC4JFCXMA63AD4VE6E"

def test_timestamps_parse_as_utc_and_sort_ascending():
    snapshots = list_snapshots("https://www.sonatype.com/compare", FakeFetcher(CDX))
    assert snapshots[0].timestamp.tzinfo is UTC
    assert snapshots[0].timestamp < snapshots[1].timestamp

def test_requests_collapse_by_digest_so_only_real_changes_are_returned():
    fetcher = FakeFetcher(CDX)
    list_snapshots("https://www.sonatype.com/compare", fetcher)
    assert "collapse=digest" in fetcher.calls[0]

def test_raw_url_uses_the_id_suffix_to_avoid_the_archive_toolbar():
    snapshots = list_snapshots("https://www.sonatype.com/compare", FakeFetcher(CDX))
    assert snapshots[0].raw_url == (
        "https://web.archive.org/web/20210227194637id_/https://www.sonatype.com/compare"
    )

def test_empty_archive_response_returns_no_snapshots():
    assert list_snapshots("https://x.test", FakeFetcher(b"")) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_wayback.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.collection.wayback'`

- [ ] **Step 3: Implement `wayback.py`**

```python
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote
from app.services.collection.fetcher import Fetcher

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
RAW_PREFIX = "https://web.archive.org/web"

@dataclass(frozen=True)
class Snapshot:
    timestamp: datetime
    digest: str
    original_url: str

    @property
    def raw_url(self) -> str:
        stamp = self.timestamp.strftime("%Y%m%d%H%M%S")
        return f"{RAW_PREFIX}/{stamp}id_/{self.original_url}"

def list_snapshots(url: str, fetcher: Fetcher, limit: int = 60) -> list[Snapshot]:
    """List archived versions where the content actually changed.

    collapse=digest asks the archive to omit consecutive identical captures, so
    every returned row is a real content change rather than a re-crawl.
    """
    query = (f"{CDX_ENDPOINT}?url={quote(url, safe='')}"
             f"&output=json&limit={limit}&collapse=digest&filter=statuscode:200")
    result = fetcher.fetch(query)
    if not result.body:
        return []

    rows = json.loads(result.body)
    snapshots = [
        Snapshot(
            timestamp=datetime.strptime(row[1], "%Y%m%d%H%M%S").replace(tzinfo=UTC),
            digest=row[5],
            original_url=row[2],
        )
        for row in rows[1:]                     # row 0 is the column header
    ]
    return sorted(snapshots, key=lambda s: s.timestamp)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_wayback.py -v`
Expected: PASS (all five tests)

- [ ] **Step 5: Add one live test, excluded from the default run**

```python
@pytest.mark.live
def test_live_archive_has_many_versions_of_the_sonatype_comparison_page():
    from app.services.collection.fetcher import StaticFetcher
    snapshots = list_snapshots(
        "https://www.sonatype.com/compare/sonatype-nexus-versus-jfrog-artifactory",
        StaticFetcher(),
    )
    assert len(snapshots) >= 10
```

Run: `pytest tests/test_wayback.py -m live -v`
Expected: PASS (confirms the archive still behaves as designed against)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/collection/wayback.py tests/test_wayback.py
git commit -m "feat: Wayback CDX client returning only real content changes"
```

---

### Task 11: Backfill orchestration — the Day 1 milestone

**Files:**
- Create: `backend/app/services/backfill.py`, `backend/worker/jobs.py`, `backend/worker/main.py`
- Modify: `backend/app/routers/health.py` (add `/stats`)
- Test: `tests/test_backfill.py`

**Interfaces:**
- Consumes: everything from Tasks 3–10
- Produces: `backfill_source(session, source, fetcher) -> BackfillReport` with `.captures`, `.claims_created`, `.versions_created`; `worker.jobs.run_backfill()`

- [ ] **Step 1: Write the failing test**

```python
from datetime import UTC, datetime
from app.services.collection.fetcher import FetchResult
from app.services.collection.wayback import Snapshot
from app.services.backfill import backfill_source
from app.models.ledger import Claim, ClaimVersion
from app.models.capture import RawCapture

V1 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Limited</td></tr></table></body></html>"
V2 = b"<html><body><table><tr><th>Capability</th><th>JFrog</th></tr>" \
     b"<tr><td>Malware detection</td><td>Very limited, not proactive</td></tr></table></body></html>"

class ScriptedFetcher:
    def __init__(self, pages): self.pages = pages
    def fetch(self, url, etag=None, last_modified=None):
        return FetchResult(url, 200, self.pages[url], None, None, False)

def test_backfill_creates_one_capture_per_snapshot(session, seeded_source, monkeypatch):
    snapshots = [
        Snapshot(datetime(2021, 2, 27, tzinfo=UTC), "d1", "https://x.test/c"),
        Snapshot(datetime(2026, 5, 10, tzinfo=UTC), "d2", "https://x.test/c"),
    ]
    monkeypatch.setattr("app.services.backfill.list_snapshots", lambda *a, **k: snapshots)
    fetcher = ScriptedFetcher({snapshots[0].raw_url: V1, snapshots[1].raw_url: V2})

    report = backfill_source(session, seeded_source, fetcher)

    assert report.captures == 2
    assert session.query(RawCapture).filter_by(provenance="archive").count() == 2

def test_backfill_records_the_claim_change_between_versions(session, seeded_source, monkeypatch):
    snapshots = [
        Snapshot(datetime(2021, 2, 27, tzinfo=UTC), "d1", "https://x.test/c"),
        Snapshot(datetime(2026, 5, 10, tzinfo=UTC), "d2", "https://x.test/c"),
    ]
    monkeypatch.setattr("app.services.backfill.list_snapshots", lambda *a, **k: snapshots)
    fetcher = ScriptedFetcher({snapshots[0].raw_url: V1, snapshots[1].raw_url: V2})

    backfill_source(session, seeded_source, fetcher)

    version = session.query(ClaimVersion).one()
    assert version.old_text == "Limited"
    assert version.new_text == "Very limited, not proactive"
    assert version.change_kind == "substantive"

def test_claim_subject_is_jfrog_and_asserter_is_the_source_entity(session, seeded_source, monkeypatch):
    snapshots = [Snapshot(datetime(2021, 2, 27, tzinfo=UTC), "d1", "https://x.test/c")]
    monkeypatch.setattr("app.services.backfill.list_snapshots", lambda *a, **k: snapshots)
    backfill_source(session, seeded_source, ScriptedFetcher({snapshots[0].raw_url: V1}))

    from app.models.registry import Entity
    claim = session.query(Claim).one()
    assert session.get(Entity, claim.subject_entity_id).slug == "jfrog"
    assert session.get(Entity, claim.asserting_entity_id).slug == "sonatype"
```

- [ ] **Step 2: Add the `seeded_source` fixture to `tests/conftest.py`**

```python
@pytest.fixture
def seeded_source(session):
    from app.services.seeding import seed
    from app.models.registry import Source
    seed(session)
    return session.query(Source).filter_by(key="sonatype_compare_jfrog").one()
```

- [ ] **Step 3: Run to verify it fails**

Run: `pytest tests/test_backfill.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.backfill'`

- [ ] **Step 4: Implement `backfill.py`**

```python
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.capture import PageSnapshot, RawCapture
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.registry import Entity, Source
from app.services.collection.fetcher import Fetcher
from app.services.collection.wayback import list_snapshots
from app.services.detection.hashing import content_hash, normalized_hash
from app.services.detection.structural_diff import diff_rows
from app.services.normalization.parsers.html_dom import parse_html
from app.services.normalization.tracked_page import ComparisonRow, extract_comparison_rows
from app.settings import settings

@dataclass
class BackfillReport:
    captures: int = 0
    claims_created: int = 0
    versions_created: int = 0

def _store_blob(digest: str, body: bytes) -> str:
    path = Path(settings.blob_dir) / f"{digest}.bin"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return str(path)

def _rows_from(body: bytes) -> list[ComparisonRow]:
    return extract_comparison_rows(parse_html(body.decode("utf-8", errors="replace")))

def backfill_source(session: Session, source: Source, fetcher: Fetcher) -> BackfillReport:
    """Replay every archived version of a tracked page through the live pipeline."""
    report = BackfillReport()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    previous: list[ComparisonRow] = []

    for snapshot in list_snapshots(source.url, fetcher):
        result = fetcher.fetch(snapshot.raw_url)
        if not result.body:
            continue

        digest = content_hash(result.body)
        text = result.body.decode("utf-8", errors="replace")
        capture = RawCapture(
            source_id=source.id, fetched_at=snapshot.timestamp, http_status=result.status,
            content_hash=digest, blob_path=_store_blob(digest, result.body),
            extracted_text=text, provenance="archive",
        )
        session.add(capture)
        session.flush()
        report.captures += 1

        rows = _rows_from(result.body)
        session.add(PageSnapshot(
            source_id=source.id, capture_id=capture.id, captured_at=snapshot.timestamp,
            text_hash=normalized_hash(text),
            rows=[{"dimension": r.dimension, "cells": r.cells} for r in rows],
        ))

        for change in diff_rows(previous, rows):
            if change.kind == "cosmetic":
                continue
            report.claims_created, report.versions_created = _apply(
                session, source, jfrog, snapshot.timestamp, change, capture, report
            )
        previous = rows

    session.commit()
    return report

def _apply(session, source, jfrog, at, change, capture, report):
    """Create or update the claim this change refers to, and record its version."""
    dimension_claim = (
        session.query(Claim)
        .filter_by(dimension=change.dimension, asserting_entity_id=source.entity_id,
                   subject_entity_id=jfrog.id)
        .one_or_none()
    )
    if dimension_claim is None:
        dimension_claim = Claim(
            subject_entity_id=jfrog.id, asserting_entity_id=source.entity_id,
            claim_text=change.new_value or "", claim_type="positioning",
            capability_tags=[], dimension=change.dimension,
            reliability_grade=source.reliability_grade, first_seen_at=at, last_confirmed_at=at,
        )
        session.add(dimension_claim)
        session.flush()
        report.claims_created += 1
    else:
        dimension_claim.claim_text = change.new_value or dimension_claim.claim_text
        dimension_claim.last_confirmed_at = at

    session.add(ClaimVersion(
        claim_id=dimension_claim.id, old_text=change.old_value,
        new_text=change.new_value, change_kind=change.kind, changed_at=at,
    ))
    report.versions_created += 1

    if change.new_value:
        offset = capture.extracted_text.find(change.new_value)
        if offset >= 0:
            session.add(Evidence(
                claim_id=dimension_claim.id, capture_id=capture.id,
                quote=capture.extracted_text[offset:offset + len(change.new_value)],
                quote_offset=offset,
            ))
    return report.claims_created, report.versions_created
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_backfill.py -v`
Expected: PASS (all three tests)

- [ ] **Step 6: Write `backend/worker/jobs.py` and `backend/worker/main.py`**

```python
# worker/jobs.py
from app.db.session import SessionLocal
from app.models.registry import Source
from app.services.backfill import backfill_source
from app.services.collection.fetcher import StaticFetcher
from app.services.collection.robots import RobotsCache
from app.services.seeding import seed

def run_seed() -> None:
    with SessionLocal() as session:
        seed(session)

def run_backfill() -> dict[str, int]:
    """Replay archive history for every enabled snapshot-mode source."""
    fetcher, robots, totals = StaticFetcher(), RobotsCache(), {"captures": 0, "claims": 0, "versions": 0}
    with SessionLocal() as session:
        sources = session.query(Source).filter_by(mode="snapshot", enabled=True).all()
        for source in sources:
            source.robots_allowed = robots.allowed(source.url)
            if not source.robots_allowed or source.requires_js:
                continue
            report = backfill_source(session, source, fetcher)
            totals["captures"] += report.captures
            totals["claims"] += report.claims_created
            totals["versions"] += report.versions_created
        session.commit()
    return totals
```

```python
# worker/main.py
from worker.jobs import run_backfill, run_seed

if __name__ == "__main__":
    run_seed()
    print(run_backfill())          # scheduler wiring arrives in Plan 2
```

- [ ] **Step 7: Add `/stats` so the milestone is observable without a UI**

Append to `backend/app/routers/health.py`:

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.models.capture import RawCapture
from app.models.ledger import Claim, ClaimVersion

@router.get("/stats")
def stats(session: Session = Depends(get_session)) -> dict[str, int]:
    return {
        "captures": session.query(RawCapture).count(),
        "claims": session.query(Claim).count(),
        "claim_versions": session.query(ClaimVersion).count(),
    }
```

- [ ] **Step 8: Run the whole suite**

Run: `docker compose run --rm api pytest -v`
Expected: every test PASSES

- [ ] **Step 9: Verify the Day 1 milestone against the real archive**

```bash
docker compose up -d db
docker compose run --rm worker python -m worker.main
docker compose up -d api
curl http://localhost:8000/stats
```

Expected: `captures` ≥ 10, `claim_versions` > 0 — a database holding real Sonatype-versus-JFrog positioning history, collected from public archives.

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/backfill.py backend/worker backend/app/routers/health.py tests/test_backfill.py tests/conftest.py
git commit -m "feat: archive backfill producing five years of cited claim history"
```

---

## Self-review notes

**Spec coverage.** This plan implements R1.1 (partial — feeds arrive in Plan 2), R1.2, R1.3, R1.4, R1.5, R1.6, R1.7, R2.2, R2.3, R2.5, and the `subject_entity`/`asserting_entity` split underpinning R5.3. Requirements R3.x (extraction), R4.x (scoring), R6.x (delivery) and R7.x (analyst control) are deliberately out of scope here and belong to Plans 2 and 3.

**Known gaps carried forward to Plan 2**, listed so they are not mistaken for oversights:
- Feed sources (`mode: feed`) are seeded but not yet collected — Task 5 builds the fetcher they will use.
- `Document` rows are not yet written; only `RawCapture` and `PageSnapshot` are. Documents are created by the normalisation step that feeds extraction.
- `Evidence` is written only for changed comparison cells, by exact substring match. The full verification gate with fuzzy fallback (`config/verification.yaml`, already validated in Task 2) is Plan 2.
- Claims created here use `claim_type="positioning"` and empty `capability_tags`; the extraction stage populates both properly.
- pgvector is enabled by the image but no vector column exists yet — that arrives with ingestion in Plan 3.

**Type consistency.** `ComparisonRow`, `RowChange`, `Element`, `FetchResult` and `Snapshot` are defined once and used with identical signatures in every later task. `diff_rows` takes and returns the same types in Tasks 9 and 11.

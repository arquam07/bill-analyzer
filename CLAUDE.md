# Bill Analyzer

## Project Overview

Bill Analyzer is an application that lets users photograph paper bills/receipts and turn them into structured, queryable expense data.

**Core user flow:**
1. User opens the app and captures a photo of a bill/receipt
2. A small (<4B parameter) OCR or vision-language model extracts line items, prices, merchant, and date
3. Extracted items are displayed for the user to review and edit
4. User chooses to either:
   - **Save to personal expenses** (single-payer flow)
   - **Split with friends** (assign items/shares to other users)
5. Spending analytics surface insights: top categories, frequently bought items, monthly trends, merchant patterns

**Primary value:** zero-friction expense tracking + spending intelligence, all from a phone camera.

---

## Tech Stack

| Layer            | Choice                                       | Why                                              |
| ---------------- | -------------------------------------------- | ------------------------------------------------ |
| Language         | Python 3.12+ (backend), TypeScript (frontend) | Modern async Python; type-safe UI                |
| Package manager  | `uv`                                         | Fast, reproducible Python dependency management  |
| API framework    | FastAPI                                      | Async, OpenAPI-native, Pydantic validation       |
| LLM/VLM runtime  | Ollama (local)                               | Privacy-preserving inference, no API key needed  |
| Agent framework  | LangChain + LangGraph                        | Stateful multi-step bill processing pipeline     |
| Database         | PostgreSQL                                   | Relational (users, bills, items, splits)         |
| Containerization | Docker + docker-compose                      | Reproducible dev + prod environments             |
| VCS              | Git + GitHub                                 | Source control + CI/CD                           |

**Model selection (under 4B params):**
- Vision: `moondream2`, `qwen2.5-vl:3b`, or `minicpm-v` via Ollama
- Decide based on benchmark accuracy on receipt OCR — see `docs/model-eval.md` (to be created)

---

## Repository Structure

```
bill-analyzer/
├── backend/                  # FastAPI service
│   ├── src/
│   │   ├── api/              # Route handlers (thin)
│   │   ├── services/         # Business logic
│   │   ├── agents/           # LangGraph pipelines (OCR → parse → categorize)
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── db/               # Session, migrations
│   │   └── core/             # Config, logging, security
│   ├── tests/
│   ├── pyproject.toml        # uv-managed
│   └── Dockerfile
├── frontend/                 # TypeScript app (framework TBD)
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docs/
└── CLAUDE.md
```

Keep `api/` thin — route handlers should call into `services/`. Business logic does not belong in route functions.

---

## Common Commands

**Backend (run from `backend/`):**
```bash
uv sync                              # install deps from lockfile
uv run uvicorn src.main:app --reload # dev server on :8000
uv run pytest                        # run tests
uv run pytest -k bill_parsing -xvs   # focused test run
uv run ruff check src/               # lint
uv run ruff format src/              # format
uv run mypy src/                     # type check
uv run alembic upgrade head          # apply migrations
uv run alembic revision --autogenerate -m "description"  # new migration
```

**Frontend (run from `frontend/`):**
```bash
npm install
npm run dev
npm run build
npm run typecheck
npm run lint
```

**Full stack:**
```bash
docker compose up --build            # all services
docker compose logs -f backend       # tail backend logs
docker compose down -v               # tear down + drop volumes
```

**Ollama:**
```bash
ollama pull qwen2.5-vl:3b            # download VLM
ollama list                          # see local models
ollama run qwen2.5-vl:3b             # interactive test
```

---

## Code Style & Conventions

### Python
- **Type hints everywhere.** No untyped function signatures. `mypy --strict` should pass.
- **Pydantic v2** for all request/response models and config. No raw dicts crossing API boundaries.
- **Async by default** for I/O (DB, HTTP, Ollama calls). Use `asyncpg` driver for Postgres via SQLAlchemy 2.0 async.
- **Ruff** for linting and formatting (replaces black + isort + flake8). Config in `pyproject.toml`.
- **Imports:** absolute imports from `src.` package root. No relative imports beyond one level.
- **Errors:** raise typed exceptions from `src/core/exceptions.py`; catch and convert at the API boundary, never in services.
- **Logging:** structured logs via `structlog`. Never use `print()` outside of scripts.
- **No magic values.** Constants live in `src/core/constants.py` or as Pydantic Settings fields.

### TypeScript
- **Strict mode on** in `tsconfig.json` (`strict: true`, `noUncheckedIndexedAccess: true`).
- No `any`. Use `unknown` and narrow.
- Generate API types from FastAPI's OpenAPI spec — do not hand-write request/response types.
- Prefer functional components and hooks (if React); composition over inheritance regardless of framework.

### General
- **One concern per file.** If a file approaches 300 lines, split it.
- **No dead code.** Delete commented-out blocks; git history is the archive.
- **Conventional commits:** `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

---

## Architectural Patterns

### Bill processing pipeline (LangGraph)
The OCR-to-storage flow is a graph, not a linear chain. Define it in `src/agents/bill_pipeline.py`:

```
[image] → ocr_node → parse_items_node → categorize_node → validate_node → [structured bill]
                          ↓ (if low confidence)
                    request_user_review
```

Each node is a pure function over state. State is a Pydantic model. The graph handles retries and conditional branches (e.g., re-prompt the VLM if item count looks wrong).

### Database access
- One SQLAlchemy session per request, injected via FastAPI dependency.
- Repositories in `src/services/repositories/` wrap query logic. Routes never touch the session directly.
- Migrations are mandatory — no schema changes without an Alembic revision.

### Configuration
- All config via environment variables, validated by `pydantic-settings`.
- `.env.example` is checked in; `.env` is gitignored.
- Never read `os.environ` directly outside `src/core/config.py`.

### Models / VLM calls
- All Ollama interaction goes through `src/services/vision_service.py`. Routes and agents call the service, not Ollama directly.
- Always set a timeout. Always handle the case where Ollama is unreachable — degrade gracefully with a clear error to the user.
- Cache identical image hashes (the user might re-upload) — small Redis or even an in-process LRU is fine for v1.

---

## Database Schema (initial)

Core entities — refine as we build:

- `users` — id, email, name, created_at
- `bills` — id, user_id, image_path, merchant, total, currency, billed_at, raw_ocr_text, created_at
- `bill_items` — id, bill_id, name, quantity, unit_price, total_price, category
- `splits` — id, bill_id, created_by_user_id, status
- `split_participants` — id, split_id, user_id (nullable for non-users), share_amount, settled
- `categories` — id, name, parent_id (for hierarchy: "Groceries > Produce")

Indexes on `bills.user_id`, `bills.billed_at`, `bill_items.bill_id`, `bill_items.category`.

---

## Testing

- **Unit tests** for services and agent nodes. Mock Ollama at the `vision_service` boundary.
- **Integration tests** spin up a real Postgres via `testcontainers`. No SQLite-pretending-to-be-Postgres.
- **End-to-end tests** for the bill-upload flow against a stubbed Ollama response.
- Target: every PR maintains or increases coverage on touched files. No coverage gate on the whole repo (gameable), but no untested service methods either.
- Test fixtures for sample receipts live in `backend/tests/fixtures/receipts/`. Use real-world messy examples — crumpled, rotated, partially obscured.

---

## Security & Privacy

- **Bill images contain PII.** Store under user-scoped paths; never log image contents or full OCR text at INFO level.
- All endpoints except auth require a valid session/JWT.
- SQL: parameterized queries only — SQLAlchemy ORM or `text()` with bound params, never f-strings.
- Validate file uploads: max size, MIME sniffing (don't trust the extension), strip EXIF before storage.
- Rate-limit the bill-upload endpoint — VLM calls are expensive.
- Local-first: Ollama runs on the user's machine or our infra, not a third-party API. Make sure no PII leaks to external services in logs, error reporting, or telemetry.

---

## Workflow Rules for Claude

When working on this project:

1. **Plan before implementing.** For any feature touching more than two files, enter Plan Mode first and produce a written plan I can review.
2. **Read before writing.** Use `@` references to load relevant files into context before proposing changes. Don't guess at existing structure.
3. **Migrations are non-optional.** If you change a SQLAlchemy model, generate an Alembic migration in the same change. Never edit a model without one.
4. **Write the test first** for bug fixes — reproduce the bug as a failing test, then fix.
5. **One logical change per commit.** Don't bundle a refactor with a feature. Don't bundle frontend with backend unless they're a single contract change.
6. **Never commit secrets.** Check `.env` is gitignored before any `git add`.
7. **No new dependencies without justification.** If you add a package to `pyproject.toml` or `package.json`, mention why in the commit message and consider whether stdlib or an existing dep covers it.
8. **Prefer editing existing files** over creating new ones. New files require a clear reason (new module boundary, new layer).
9. **When uncertain, ask.** If a requirement is ambiguous (e.g., "should split shares default to equal or proportional?"), ask before coding rather than guessing.
10. **No stubs that lie.** If you can't fully implement something, raise `NotImplementedError` with a clear message — don't return fake data that looks real.

---

## Out of Scope (for now)

Document what we're explicitly NOT doing so Claude doesn't drift into it:

- Multi-currency conversion (assume single currency per user for v1)
- Receipt forgery/fraud detection
- Tax categorization for accounting export
- Real-time collaborative split editing (async only)
- Native mobile apps (web-first; PWA is fine)

---

## Open Questions

Track unresolved decisions here so they don't get lost:

- [ ] Frontend framework — React, SvelteKit, or Solid?
- [ ] Auth — magic link, OAuth (Google), or password?
- [ ] How to handle multi-user splits where some participants don't have accounts?
- [ ] Image storage — local disk, S3-compatible (MinIO in dev), or DB blob?
- [ ] Which VLM benchmarks best on real receipts under 4B? Need to evaluate.

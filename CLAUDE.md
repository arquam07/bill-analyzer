# Bill Analyzer

## Project Overview

Bill Analyzer lets users photograph paper bills/receipts and turn them into structured, queryable expense data with bill splitting support.

**Core user flow:**
1. User uploads a photo of a bill/receipt
2. A VLM (qwen3-vl:235b-cloud via Ollama Cloud) extracts line items, prices, merchant, and date
3. Extracted items are displayed for the user to review and edit
4. User finalizes the bill (status → `reviewed`), which locks it and adds it to analytics
5. Optionally, user splits the bill (full or selected items) with other users by username
6. Spending analytics surface insights: KPIs, spend over time, category/merchant breakdown, top items

**Primary value:** zero-friction expense tracking + spending intelligence, all from a phone camera.

---

## Tech Stack

| Layer            | Choice                                                | Why                                              |
| ---------------- | ----------------------------------------------------- | ------------------------------------------------ |
| Language         | Python 3.12+ (backend), TypeScript (frontend)         | Modern async Python; type-safe UI                |
| Package manager  | `uv`                                                  | Fast, reproducible Python dependency management  |
| API framework    | FastAPI                                               | Async, OpenAPI-native, Pydantic validation       |
| VLM              | `qwen3-vl:235b-cloud` via Ollama Cloud API            | High accuracy; cloud hosted, no local GPU needed |
| Database         | PostgreSQL                                            | Relational (users, bills, items, splits)         |
| ORM / migrations | SQLAlchemy 2.0 async + Alembic                        | Typed queries, migration history                 |
| Frontend         | React + Vite + TanStack Router v1 + TanStack Query v5 | File-based routing, server-state caching         |
| Styling          | Tailwind CSS                                          | Utility-first, zero config                       |
| Charts           | Recharts                                              | Composable React charts                          |
| Containerization | Docker + docker-compose                               | Reproducible dev + prod environments             |

**VLM details:**
- Endpoint: `https://ollama.com/api/chat`, model `qwen3-vl:235b-cloud`
- Auth: `OLLAMA_API_KEY` env var
- Images are downscaled to max 1536px before sending (reduces payload ~18×)
- Timeout: `OLLAMA_TIMEOUT_SECONDS` (default 300s)
- All interaction goes through `src/services/vision_service.py`

---

## Repository Structure

```
bill-analyzer/
├── backend/                        # FastAPI service (run from here)
│   ├── src/
│   │   ├── api/                    # Route handlers (thin — call into services)
│   │   │   ├── auth.py             # /auth/register, /auth/login, /auth/logout
│   │   │   ├── me.py               # /me
│   │   │   ├── bills.py            # /bills CRUD + /extract + /finalize
│   │   │   ├── splits.py           # /bills/{id}/split (old item-assignment split)
│   │   │   ├── split_requests.py   # /bills/{id}/split-requests, /split-requests/*, /balances, /settlements
│   │   │   ├── insights.py         # /insights/* (overview, timeseries, breakdown, items)
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── repositories/       # All DB queries live here
│   │   │   ├── auth_service.py
│   │   │   ├── bill_service.py
│   │   │   ├── split_service.py
│   │   │   ├── split_request_service.py
│   │   │   ├── insights_service.py
│   │   │   ├── vision_service.py   # All VLM calls
│   │   │   ├── image_processing.py # Resize + JPEG encode before VLM
│   │   │   └── storage/            # StorageBackend abstraction (local disk)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── db/                     # Session factory, Alembic env
│   │   ├── agents/                 # Bill extraction pipeline (wraps vision_service)
│   │   └── core/                   # Config, logging, security, exceptions
│   ├── alembic/versions/           # Migration history
│   ├── tests/                      # pytest + testcontainers (real Postgres)
│   ├── pyproject.toml
│   └── .env                        # gitignored; copy from .env.example
├── frontend/
│   ├── src/
│   │   ├── routes/                 # TanStack Router file-based routes
│   │   │   ├── __root.tsx          # Nav shell
│   │   │   ├── index.tsx
│   │   │   ├── login.tsx
│   │   │   ├── register.tsx
│   │   │   ├── dashboard.tsx       # Insights / History / Splits tabs
│   │   │   ├── upload.tsx
│   │   │   └── bills.$billId.tsx   # Bill detail + extraction + split modal
│   │   ├── features/
│   │   │   ├── insights/           # KPI cards, charts, breakdown, top items
│   │   │   └── splits/             # SplitModal, SplitsTab, api hooks
│   │   ├── api/
│   │   │   ├── fetcher.ts          # Raw fetch wrapper + ApiError + token mgmt
│   │   │   ├── endpoints.ts        # Typed API calls (auth, bills, insights, splitRequests)
│   │   │   ├── types.ts            # Hand-maintained types for insights + splits
│   │   │   └── types.gen.ts        # Auto-generated from OpenAPI (auth/bill schemas)
│   │   └── auth/
│   │       └── AuthContext.tsx     # User state + login/register/logout
│   └── package.json
├── docker-compose.yml
└── CLAUDE.md
```

Keep `api/` thin — route handlers call into `services/`. Business logic does not belong in route functions.

---

## Common Commands

**Backend (run from `backend/`):**
```bash
uv sync                              # install deps from lockfile
uv run uvicorn src.main:app --reload # dev server on :8000
uv run pytest                        # run tests (requires Docker for testcontainers)
uv run pytest tests/test_auth.py -xvs  # focused test run
uv run ruff check src/               # lint
uv run ruff format src/              # format
uv run mypy src/ --ignore-missing-imports  # type check
uv run alembic upgrade head          # apply migrations
uv run alembic revision --autogenerate -m "description"  # new migration
```

**Frontend (run from `frontend/`):**
```bash
npm install
npm run dev        # dev server on :5173
npm run build
npm run typecheck  # tsc -b --noEmit
npm run lint
```

**Full stack:**
```bash
docker compose up --build            # all services
docker compose logs -f backend       # tail backend logs
docker compose down -v               # tear down + drop volumes
```

---

## Database Schema (current)

All tables use UUID primary keys. Migrations live in `alembic/versions/`.

| Table | Key columns |
|---|---|
| `users` | id, email (unique), **username** (unique, `[a-z0-9]{3,50}`), password_hash, name, created_at |
| `user_sessions` | id, user_id→users, token_hash, created_at |
| `bills` | id, user_id→users, image_path, content_hash, status (`uploaded`/`extracted`/`reviewed`), merchant, total, currency, billed_at, raw_ocr_text, extracted_at, reviewed_at |
| `bill_items` | id, bill_id→bills, position, name, quantity, unit_price, total_price, category |
| `splits` | id, bill_id→bills (unique), created_by_user_id→users — old manual split-assignment system |
| `split_participants` | id, split_id→splits, user_id (nullable), display_name, settled_at |
| `split_item_shares` | id, split_id, bill_item_id, participant_id, weight |
| `split_requests` | id, bill_id→bills, from_user_id→users, to_user_id→users, amount, status (`pending`/`accepted`/`rejected`), note, responded_at — **new user-to-user split flow** |
| `split_settlements` | id, from_user_id→users, to_user_id→users, amount, note, created_at |

Key indexes: `bills.user_id`, `bills.billed_at`, `bill_items.bill_id`, `split_requests.from_user_id`, `split_requests.to_user_id`.

---

## API Endpoints (current)

```
POST   /auth/register           body: {email, password, username, name?}
POST   /auth/login              body: {email, password}
POST   /auth/logout
GET    /me

GET    /bills                   ?limit&offset
POST   /bills                   multipart image upload
GET    /bills/{id}
PATCH  /bills/{id}              body: {merchant?, total?, currency?, billed_at?}
POST   /bills/{id}/extract      triggers VLM extraction
POST   /bills/{id}/finalize     status → reviewed (locks bill)
POST   /bills/{id}/items        add item
PATCH  /bills/{id}/items/{iid}
DELETE /bills/{id}/items/{iid}

GET    /bills/{id}/split        (old item-assignment split)
POST   /bills/{id}/split/participants
...

GET    /users/by-username/{username}   lookup by username (auth required)
POST   /bills/{id}/split-requests     body: {usernames[], total_to_split?}
GET    /split-requests/incoming       pending requests addressed to me
GET    /split-requests/outgoing       all requests I sent
POST   /split-requests/{id}/accept
POST   /split-requests/{id}/reject
GET    /balances                      net balances per counterparty
POST   /settlements                   body: {username, amount, note?}

GET    /insights/overview       ?from&to  (spend deducted by accepted split amounts)
GET    /insights/timeseries     ?from&to&granularity
GET    /insights/breakdown      ?from&to&dimension&limit
GET    /insights/items          ?from&to&order_by&limit
GET    /insights/items/{name}/timeseries  ?from&to&granularity

GET    /health
```

---

## Bill FSM

```
uploaded  →(POST /extract)→  extracted  →(POST /finalize)→  reviewed
             ↑ (re-extract allowed)
```

- Only `reviewed` bills with non-null `billed_at` appear in insights.
- Editing (PATCH bill, add/update/delete items) is locked once `reviewed`.
- Insights deduct accepted outgoing split amounts from spend totals so the owner only sees their portion.

---

## Split Request Flow

1. Bill owner opens bill detail, clicks **Split bill** (visible when `bill.total` is set).
2. `SplitModal` shows all priced items with checkboxes (all selected by default).
3. Owner selects items to split and adds recipients by username (validated via `/users/by-username`).
4. Amount per recipient = `Σ(selected items) / (n_recipients + 1)`. Falls back to `bill.total` if no items have prices.
5. `POST /bills/{id}/split-requests` creates one `SplitRequest` per recipient (status `pending`).
6. Recipients see pending requests in **Dashboard → Splits tab** and can Accept or Decline.
7. Accepted requests affect both users' net balances (`GET /balances`).
8. Either party records a manual payment via `POST /settlements` to settle the balance.

**Business rules:**
- Shares are always equal (no manual allocation).
- Username format: `[a-z0-9]{3,50}`.
- Rejected requests appear in a "Declined" section (not deleted).
- One bill can be split with multiple users simultaneously.
- Duplicate pending requests for the same bill+pair are rejected (409).

---

## Frontend Architecture

- **TanStack Router**: File-based routes in `src/routes/`. `validateSearch` on dashboard for URL-synced tab/range state.
- **TanStack Query**: `gcTime: 0, staleTime: 0` globally — cache discarded immediately when no observers, every navigation fetches fresh data.
- **Auth**: Token stored in `localStorage`. `AuthProvider` wraps the tree. Login/register navigate via `useEffect` watching `user` state (not inline `navigate()` calls).
- **API types**: `types.gen.ts` is auto-generated from OpenAPI for auth+bills; insights+splits types are hand-maintained in `types.ts` until the next gen run.

---

## Code Style & Conventions

### Python
- **Type hints everywhere.** `mypy --ignore-missing-imports` must pass on `src/`.
- **Pydantic v2** for all request/response models and config. No raw dicts crossing API boundaries.
- **Async by default** for I/O. Use `asyncpg` driver via SQLAlchemy 2.0 async.
- **Ruff** for linting and formatting.
- **Imports:** absolute from `src.` root. No relative imports beyond one level.
- **Errors:** typed exceptions from `src/core/exceptions.py`; caught and converted at the API boundary only.
- **No magic values.** Constants in `src/core/constants.py` or Pydantic Settings.

### TypeScript
- **Strict mode** (`strict: true`, `noUncheckedIndexedAccess: true`).
- No `any`. Use `unknown` and narrow.
- Functional components and hooks only.

### General
- **One concern per file.** Split at ~300 lines.
- **No dead code.** Delete commented-out blocks.
- **Conventional commits:** `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

---

## Testing

- **Integration tests** spin up real Postgres via `testcontainers`. No SQLite fakes.
- All register calls in tests must include `username`.
- Test fixtures: `_make_jpeg()` creates a minimal valid JPEG. VisionService is replaced with `_NullVisionService` in conftest; extraction tests inject a `_FakeVision` override.
- Target: no untested service methods in touched files.

---

## Workflow Rules for Claude

1. **Read before writing.** Load relevant files before proposing changes.
2. **Migrations are non-optional.** Any SQLAlchemy model change needs an Alembic revision in the same change. Run `alembic revision --autogenerate` then review the generated file.
3. **Keep `api/` thin.** Route handlers call services. No business logic in routes.
4. **Frontend types.gen.ts** is auto-generated — don't edit it for insights/splits types; add those to `types.ts` instead. Re-run `npm run gen-types` after backend schema changes to regenerate auth/bill types.
5. **`gcTime: 0` is intentional.** Do not add per-query caching without discussion — stale data caused bugs.
6. **Split amounts use `total_to_split` from the frontend**, not `bill.total`. The backend trusts the value the frontend sends (computed from checked items).
7. **No stubs that lie.** Raise `NotImplementedError` with a message rather than returning fake data.
8. **Never commit secrets.** `.env` is gitignored.

---

## Security & Privacy

- Bill images contain PII. Store under user-scoped paths; never log image contents at INFO level.
- All endpoints except `/auth/*` and `/health` require a valid session token (Bearer).
- SQL: parameterized queries only via SQLAlchemy ORM. Never f-strings in queries.
- File uploads: max size enforced, MIME sniffed (don't trust extension), EXIF stripped.
- Rate-limit the bill-upload endpoint — VLM calls are expensive.

---

## Resolved Decisions

| Question | Decision |
|---|---|
| Frontend framework | React + Vite + TanStack Router/Query + Tailwind |
| Auth | Session tokens (password-based, no OAuth yet) |
| VLM | `qwen3-vl:235b-cloud` via Ollama Cloud for dev/testing |
| Image storage | Local filesystem via `StorageBackend` abstraction |
| Multi-user splits | Supported; always equal shares |
| Username format | `[a-z0-9]{3,50}` |
| Split participants without accounts | Not supported; all recipients must have a username |
| CI | Deferred to later milestone |

---

## Out of Scope (for now)

- Multi-currency conversion (single currency per user)
- Receipt forgery/fraud detection
- Tax categorization / accounting export
- Real-time collaborative editing
- Native mobile apps (web-first; PWA acceptable)
- OAuth / magic link auth
- Proportional (non-equal) split allocation

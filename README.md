# Bill Analyzer

Turn a phone photo of any paper bill or receipt into structured, queryable expense data — with multi-user bill splitting and spending analytics on top.

Snap a receipt → a vision-language model extracts merchant, date, line items, prices and tax → you review and finalize → the bill flows into spending insights and can be split with friends by username.

> **AI/ML at a glance:** A two-stage LLM pipeline on **GCP Vertex AI** (Gemini 2.5 Flash). Stage 1 is multimodal OCR + structured extraction from the receipt image; stage 2 canonicalizes item names so analytics can group `"oat milk"`, `"2% milk"` and `"whole milk"` into one `milk` series. Both stages emit schema-validated JSON, run async, retry on malformed output, and degrade gracefully. We are currently **fine-tuning a small language model (SLM)** to replace the hosted Gemini calls for faster, cheaper inference at the same accuracy.

---

## Table of Contents

- [Architecture overview](#architecture-overview)
- [The vision / extraction pipeline](#the-vision--extraction-pipeline) ← AI/ML core
- [Item normalization for analytics](#item-normalization-for-analytics)
- [Model strategy & the SLM fine-tuning roadmap](#model-strategy--the-slm-fine-tuning-roadmap)
- [Authentication](#authentication)
- [Friend requests & deferred splits](#friend-requests--deferred-splits)
- [Spending insights](#spending-insights)
- [Tech stack](#tech-stack)
- [Backend layout](#backend-layout)
- [Data model](#data-model)
- [API surface](#api-surface)
- [Running locally](#running-locally)
- [Testing & quality gates](#testing--quality-gates)

---

## Architecture overview

```
                         ┌──────────────────────────────────────────────┐
   React + Vite SPA      │                FastAPI (async)               │
   TanStack Router/Query │                                              │
        │  Bearer token  │   api/ (thin handlers) → services/ → repos/  │
        └───────────────►│            │                  │              │
                         │            ▼                  ▼              │
                         │   ┌─────────────────┐   ┌──────────────┐     │
                         │   │  GCP Vertex AI  │   │ PostgreSQL   │     │
                         │   │  Gemini 2.5     │   │ SQLAlchemy 2 │     │
                         │   │  Flash (genai)  │   │ + Alembic    │     │
                         │   └─────────────────┘   └──────────────┘     │
                         │            │                                 │
                         │   ┌─────────────────┐                        │
                         │   │ Object storage  │  Local disk (dev)      │
                         │   │ (StorageBackend)│  GCS bucket (prod)     │
                         │   └─────────────────┘                        │
                         └──────────────────────────────────────────────┘
```

The backend is a layered async FastAPI service. **Route handlers are deliberately thin** — they validate input, call a service, and translate typed domain exceptions into HTTP status codes. All business logic lives in `services/`, and all SQL lives in `services/repositories/`. This keeps the AI/ML surface (`vision_service.py`, `normalization_service.py`) isolated, independently testable, and swappable.

---

## The vision / extraction pipeline

This is the heart of the product. A user uploads a photo; we return a fully structured bill.

```
 upload ──► image_processing ──► VisionService.extract_bill ──► tax correction ──► persist
            (sniff, strip EXIF,   (Vertex AI / Gemini 2.5      (deterministic     (bill +
             downscale to 1536px,  Flash, JSON-mode, T=0,       reconciliation     items,
             re-encode JPEG q85)   3× retry on bad output)      vs. bill total)    status=extracted)
```

### 1. Image preprocessing (`services/image_processing.py`)

Before a byte ever reaches the model we:

- **Sniff the real format** with Pillow (we never trust the file extension or client-supplied MIME).
- **Strip EXIF / metadata** by fully re-encoding — receipts carry PII and GPS data we don't want to persist or send out.
- **Downscale to 1536 px** on the long edge. Receipt OCR sees no accuracy gain above this, and it cuts model latency and payload size by roughly an order of magnitude.
- Re-encode JPEG at quality 85 (`optimize=True`), converting to RGB as needed.

This step is a cost/latency lever: smaller, clean images mean cheaper, faster, more reliable extraction.

### 2. Structured extraction (`services/vision_service.py`)

`VisionService` wraps the **Google GenAI SDK against Vertex AI** (`genai.Client(vertexai=True, project=…, location=…)`). Authentication is via **Application Default Credentials** — no API keys in the codebase.

Key design choices:

| Concern | Approach |
|---|---|
| **Structured output** | `response_mime_type="application/json"` + a strict, hand-tuned system prompt defining the exact JSON shape (merchant, total, currency, `billed_at`, per-item name/qty/price/tax_rate/category, plus `raw_text`). |
| **Determinism** | `temperature=0.0` — extraction is a transcription task, not a creative one. |
| **Validation** | Every response is parsed and validated against a **Pydantic** schema (`RawBillExtraction`). Invalid JSON or schema mismatch is a typed error, not a silent bad row. |
| **Resilience** | Up to **3 attempts** with backoff on malformed/invalid output. Timeouts are treated as non-retryable (too expensive) and surface as `503`. |
| **Localization** | The prompt translates `merchant` and item names into the user's `preferred_language` while preserving `raw_text` verbatim in the source language. |
| **Multilingual tax logic** | The prompt encodes real-world receipt rules — e.g. Japanese 外税 (tax-exclusive) pricing where `※`-marked items carry the 8% reduced food rate and unmarked items carry 10%. |

### 3. Deterministic tax reconciliation (`_correct_tax_rates`)

LLMs sometimes double-count tax — applying a rate to prices that were already tax-inclusive. Rather than trusting the model blindly, we **reconcile against ground truth**: we compute the item sum both tax-exclusive and tax-inclusive, compare each to the model-reported bill total, and if the exclusive sum is closer we strip the spurious tax rates. This is a small, deterministic guardrail layered on top of the probabilistic model — a pattern worth noting: *use the LLM for perception, use code for arithmetic you can verify.*

The extracted bill lands in `extracted` status for the user to review and edit before finalizing.

---

## Item normalization for analytics

Raw receipt text is hostile to analytics: `"FRSH BRWN EGGS L"`, `"halal eggs"` and `"free-range eggs"` are all just *eggs*. A second, lighter LLM pass solves this.

`NormalizationService` (`services/normalization_service.py`) runs **on finalize, as a FastAPI background task** so it never blocks the user:

```
finalize bill ──► (response returned immediately)
                  └─ background: load un-normalized items
                       + last 30 days of this user's canonical names
                       └─► Gemini 2.5 Flash (JSON map: raw name → canonical noun)
                            └─► UPDATE bill_items.normalized_name
```

- It primes the model with the user's **existing canonical names from the last 30 days**, so naming stays stable over time (new canonicals are only minted when nothing matches).
- It's **best-effort by design**: any failure is logged and swallowed, and insights fall back to raw item names via SQL. A flaky model call never corrupts a finalized bill.
- Output is strict JSON `{ "raw name": "canonical" | null }`, parsed defensively.

The result powers the **"top items" analytics** — spend and purchase frequency grouped by canonical product across all of a user's receipts.

---

## Model strategy & the SLM fine-tuning roadmap

**Today:** Both pipeline stages call **Gemini 2.5 Flash on GCP Vertex AI** (region `asia-northeast1`). Vertex was chosen for managed multimodal inference, ADC-based auth (no key management), data-residency control, and a single billing/observability plane.

**In progress:** We are **fine-tuning a small language model (SLM)** to take over OCR extraction and item normalization. The motivation:

- **Cost** — per-receipt inference on a self-hosted/distilled SLM is a fraction of hosted frontier-model pricing at our volume.
- **Latency** — a task-specialized small model returns structured JSON faster than a general-purpose large model.
- **Specialization** — extraction and canonicalization are narrow, well-defined tasks. Gemini 2.5 Flash currently doubles as our *teacher* to generate and label training data; the fine-tuned SLM is the *student*.

The architecture makes this swap low-risk: all model interaction is funneled through `VisionService` / `NormalizationService`, the I/O contract is a Pydantic schema, and the deterministic tax-reconciliation and SQL-fallback guardrails catch regressions regardless of which model is behind the interface.

---

## Authentication

Two credential paths, one unified session model.

```
 ┌─ Password ─────────────────────────────────────────────┐
 │ register/login → Argon2 hash (argon2-cffi)             │
 │                  verify → issue session token          │
 └────────────────────────────────────────────────────────┘
 ┌─ Google OAuth ─────────────────────────────────────────┐
 │ client sends Google id_token                           │
 │   POST /auth/google                                    │
 │     verify id_token against GOOGLE_CLIENT_ID (google-auth)
 │     ├─ known google_id / email → link & issue token    │
 │     └─ new user → { needs_onboarding: true }           │
 │   POST /auth/google/complete (pick username)           │
 │     create user (password_hash = NULL) → issue token   │
 └────────────────────────────────────────────────────────┘
                          │
                          ▼
        opaque token = secrets.token_urlsafe(32)
        store ONLY sha256(token) in user_sessions
        client sends it as `Authorization: Bearer <token>`
```

Design notes (`core/security.py`, `services/auth_service.py`):

- **Passwords** are hashed with **Argon2** (memory-hard, the current best practice), never reversible.
- **Session tokens are opaque and random** (`secrets.token_urlsafe(32)`) — not JWTs. We store only the **SHA-256 hash** of the token in `user_sessions`, so a database leak doesn't expose usable credentials. Lookup hashes the presented token and matches.
- **Google sign-in** verifies the `id_token` server-side against the configured `GOOGLE_CLIENT_ID` via Google's official library. New Google users go through a lightweight **onboarding step to claim a unique username**; existing email accounts are transparently **linked** to their Google identity (`password_hash` stays `NULL` for Google-only accounts).
- Every endpoint except `/auth/*` and `/health` requires a valid Bearer token, resolved by a shared `get_current_user` dependency.

---

## Friend requests & deferred splits

Splitting a bill requires a relationship between two users. The friendship layer (`services/friendship_service.py`, `models/friendship.py`) is a standard request/accept graph — with one notable twist: **you can attach a split to a friend request before the recipient is even your friend.**

### State machine

```
        send_request
  (none) ─────────────► pending ──accept──► accepted   (you are now friends)
     ▲                    │
     │                    └──reject──► rejected ──send_request──► pending
     └──────────────────────────────────────────────┘  (re-request allowed)
```

A `Friendship` row stores `requester_id`, `addressee_id`, and `status` (`pending` / `accepted` / `rejected`). Re-requesting after a rejection reactivates the same row rather than creating duplicates. Sending to an already-`accepted` pair returns `409 already friends`; an existing `pending` pair returns `409 already pending`.

### Deferred splits — the twist

When the bill owner wants to split with someone they aren't friends with yet, the split can't exist until the friendship does. So we **defer it**:

```
 Owner splits a bill with @bob (not yet a friend)
        │
        ▼
 POST /friends/requests  { username: "bob", deferred_split: {bill_id, amount, bill_item_ids} }
        │
        ├─ create Friendship(pending)
        └─ attach DeferredSplitRequest row(s)  (parked, not yet a real split)
        │
        ▼
 @bob accepts the friend request
        │
        ├─ Friendship → accepted
        └─ for each deferred split:  promote → real SplitRequest(pending)   ◄── atomic, idempotent
        │
        ▼
 @bob sees a pending split request and can Accept / Decline
        │
        └─ accepted splits update both users' net balances
```

The promotion happens **inside the accept transaction** and is **idempotent** (it checks for an existing split request for the same bill+pair before creating one), so a double-accept or retry can't create duplicate debts. `DeferredSplitRequest` carries the `bill_id`, the precomputed `amount`, and the optional list of `bill_item_ids` that were selected, so the eventual split reflects exactly what the owner chose at request time.

This means a brand-new user can be invited and have a bill split with them in a single flow, with no orphaned or premature financial records along the way.

---

## Spending insights

Only **finalized (`reviewed`) bills with a known date** feed analytics. `InsightsService` (backed by SQL aggregations in `insights_repository.py`) serves:

- **Overview** — total spend, bill count, average bill, top merchant/category, and a **period-over-period delta** (compares the selected window against the immediately preceding equal-length window).
- **Time series** — spend bucketed by day/week/month.
- **Breakdown** — spend by merchant or category.
- **Top items** — spend and purchase frequency by **normalized** product name, plus per-item time series.

Ranges are validated and capped at 12 months. Accepted outgoing split amounts are deducted from the owner's spend, so each user only sees their own share.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12+ (backend), TypeScript (frontend) | Modern async Python; type-safe UI |
| Package manager | `uv` | Fast, reproducible dependency resolution |
| API framework | FastAPI | Async, OpenAPI-native, Pydantic validation |
| AI / inference | **GCP Vertex AI — Gemini 2.5 Flash** via `google-genai` | Managed multimodal inference, ADC auth, JSON mode |
| Database | PostgreSQL | Relational (users, bills, items, splits, friendships) |
| ORM / migrations | SQLAlchemy 2.0 async + Alembic | Typed queries, migration history |
| Object storage | `StorageBackend` abstraction → local disk (dev) / **GCS** (prod) | Pluggable, PII-scoped paths |
| Auth | Argon2 password hashing + Google OAuth (`google-auth`) | Hashed opaque session tokens |
| Frontend | React + Vite + TanStack Router/Query + Tailwind | File-based routing, server-state caching |
| Charts | Recharts | Composable React charts |
| Containerization | Docker + docker-compose | Reproducible dev + prod |

---

## Backend layout

```
backend/src/
├── api/                  # Thin route handlers (validate → call service → map errors)
│   ├── auth.py           # register/login/logout + Google OAuth
│   ├── bills.py          # CRUD, /extract (VLM), /finalize (→ background normalization)
│   ├── friends.py        # friend requests + deferred splits
│   ├── split_requests.py # user-to-user splits, balances, settlements
│   ├── insights.py       # analytics endpoints
│   └── me.py, health.py
├── services/
│   ├── vision_service.py        # ◄ AI: Vertex AI multimodal OCR + extraction
│   ├── normalization_service.py # ◄ AI: item-name canonicalization
│   ├── image_processing.py      # resize / strip EXIF / re-encode pre-inference
│   ├── auth_service.py          # password + Google flows, session issuance
│   ├── bill_service.py          # bill FSM + ownership enforcement
│   ├── friendship_service.py    # friendships + deferred-split promotion
│   ├── split_request_service.py # splits, balances, settlements
│   ├── insights_service.py      # range validation + analytics orchestration
│   ├── repositories/            # all SQL lives here
│   └── storage/                 # StorageBackend: local disk / GCS
├── models/               # SQLAlchemy ORM models
├── schemas/              # Pydantic request/response + extraction schemas
├── core/                 # config, logging, security, typed exceptions, constants
└── db/                   # async session factory, Alembic env
```

**Conventions:** type hints everywhere (`mypy --strict`), Ruff for lint/format, Pydantic v2 at every boundary (no raw dicts cross the API), absolute imports from `src.`, typed exceptions converted to HTTP only at the API edge.

---

## Data model

UUID primary keys throughout. Selected tables:

| Table | Key columns |
|---|---|
| `users` | id, email (unique), username (unique, `[a-z0-9]{3,50}`), `google_id` (nullable), `password_hash` (nullable for Google-only), preferred_language |
| `user_sessions` | id, user_id, **token_hash** (sha256), created_at |
| `bills` | id, user_id, image_path, content_hash, status (`uploaded`→`extracted`→`reviewed`), merchant, total, currency, billed_at, raw_ocr_text |
| `bill_items` | id, bill_id, position, name, **normalized_name**, quantity, unit_price, total_price, tax_rate, category |
| `friendships` | id, requester_id, addressee_id, status (`pending`/`accepted`/`rejected`), responded_at |
| `deferred_split_requests` | id, friendship_id, bill_id, from_user_id, to_user_id, amount, bill_item_ids (JSON) |
| `split_requests` | id, bill_id, from_user_id, to_user_id, amount, status, note |
| `split_settlements` | id, from_user_id, to_user_id, amount, note, created_at |

Any model change ships with an Alembic migration in the same commit.

### Bill FSM

```
uploaded ──POST /extract──► extracted ──POST /finalize──► reviewed
              ▲ (re-extract allowed)                       (locked; enters insights)
```

Editing is locked once a bill is `reviewed`. Only `reviewed` bills with a non-null `billed_at` appear in insights.

---

## API surface

```
# Auth
POST   /auth/register | /auth/login | /auth/logout
POST   /auth/google            verify id_token → token or needs_onboarding
POST   /auth/google/complete   claim username → token
GET    /me

# Bills
GET    /bills                  ?limit&offset
POST   /bills                  multipart image upload
POST   /bills/manual           create without an image
GET    /bills/{id}
PATCH  /bills/{id}             merchant/total/currency/billed_at/category
POST   /bills/{id}/extract     ◄ trigger Vertex AI extraction
POST   /bills/{id}/finalize    lock + kick off background item normalization
POST   /bills/{id}/items  ·  PATCH/DELETE /bills/{id}/items/{iid}

# Friends & splits
POST   /friends/requests           { username, deferred_split? }
GET    /friends/requests/incoming | /outgoing
POST   /friends/requests/{id}/accept | /reject
GET    /friends
POST   /bills/{id}/split-requests
GET    /split-requests/incoming | /outgoing
POST   /split-requests/{id}/accept | /reject
GET    /balances
POST   /settlements                { username, amount, note? }

# Insights
GET    /insights/overview | /timeseries | /breakdown | /items
GET    /insights/items/{name}/timeseries

GET    /health
```

---

## Running locally

**Backend** (from `backend/`):

```bash
uv sync                                  # install from lockfile
# .env: DATABASE_URL, VERTEX_PROJECT/LOCATION/MODEL, GOOGLE_CLIENT_ID, (GCS_BUCKET in prod)
# Vertex AI auth via Application Default Credentials:
gcloud auth application-default login
uv run alembic upgrade head              # apply migrations
uv run uvicorn src.main:app --reload     # http://localhost:8000  (/docs for OpenAPI)
```

**Frontend** (from `frontend/`):

```bash
npm install
npm run dev                              # http://localhost:5173
```

**Full stack:**

```bash
docker compose up --build
```

---

## Testing & quality gates

- **Integration tests run against a real PostgreSQL** via `testcontainers` — no SQLite fakes, so async SQLAlchemy and Postgres-specific behavior are exercised for real.
- The Vertex AI client is **dependency-injected**, so tests swap in a fake vision/normalization implementation and never hit the network or incur model cost.
- Quality gates: `uv run ruff check src/`, `uv run ruff format src/`, `uv run mypy src/` (strict), `uv run pytest`.

```bash
uv run pytest                            # full suite (needs Docker)
uv run pytest tests/test_auth.py -xvs    # focused run
```

---

## Security & privacy highlights

- Bill images contain PII → stored under **user-scoped paths**, EXIF stripped, never logged at INFO.
- Passwords hashed with **Argon2**; session tokens stored **only as SHA-256 hashes**.
- **Parameterized queries only** via SQLAlchemy ORM — no string-built SQL.
- Uploads are **size-capped and MIME-sniffed** (extension never trusted); the expensive extraction endpoint is intended to be rate-limited.
- Secrets live in gitignored `.env`; Vertex AI uses ADC, not committed keys.
```
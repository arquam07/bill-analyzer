# Graph Report - .  (2026-04-29)

## Corpus Check
- Corpus is ~18,610 words - fits in a single context window. You may not need a graph.

## Summary
- 562 nodes · 1070 edges · 38 communities detected
- Extraction: 77% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 240 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Bill & Split Domain|Bill & Split Domain]]
- [[_COMMUNITY_Auth Flow|Auth Flow]]
- [[_COMMUNITY_Project Architecture Overview|Project Architecture Overview]]
- [[_COMMUNITY_Bill Review Tests|Bill Review Tests]]
- [[_COMMUNITY_Extraction Schemas|Extraction Schemas]]
- [[_COMMUNITY_DB Layer & Models|DB Layer & Models]]
- [[_COMMUNITY_LangGraph Bill Pipeline|LangGraph Bill Pipeline]]
- [[_COMMUNITY_Image Upload & Storage|Image Upload & Storage]]
- [[_COMMUNITY_Project Rules (CLAUDE.md)|Project Rules (CLAUDE.md)]]
- [[_COMMUNITY_Auth Schemas|Auth Schemas]]
- [[_COMMUNITY_Bill Upload Tests|Bill Upload Tests]]
- [[_COMMUNITY_Auth & Health Route Tests|Auth & Health Route Tests]]
- [[_COMMUNITY_App Config & Bootstrap|App Config & Bootstrap]]
- [[_COMMUNITY_Bill Extraction Tests|Bill Extraction Tests]]
- [[_COMMUNITY_Vision Service Tests|Vision Service Tests]]
- [[_COMMUNITY_Frontend Auth Client|Frontend Auth Client]]
- [[_COMMUNITY_Bills API Routes|Bills API Routes]]
- [[_COMMUNITY_Splits API Routes|Splits API Routes]]
- [[_COMMUNITY_Storage Backend Interface|Storage Backend Interface]]
- [[_COMMUNITY_Migration create_bills|Migration: create_bills]]
- [[_COMMUNITY_Migration bill_extraction_fields|Migration: bill_extraction_fields]]
- [[_COMMUNITY_Migration splits_participants_item_shares|Migration: splits_participants_item_shares]]
- [[_COMMUNITY_Migration create_users_and_sessions|Migration: create_users_and_sessions]]
- [[_COMMUNITY_Frontend Bill Detail Page|Frontend Bill Detail Page]]
- [[_COMMUNITY_Health Endpoint|Health Endpoint]]
- [[_COMMUNITY_Me Endpoint|Me Endpoint]]
- [[_COMMUNITY_Frontend Login Page|Frontend Login Page]]
- [[_COMMUNITY_Frontend Register Page|Frontend Register Page]]
- [[_COMMUNITY_Frontend Root Layout|Frontend Root Layout]]
- [[_COMMUNITY_Config Rationale|Config Rationale]]
- [[_COMMUNITY_Misc Async-by-default IO|Misc: Async-by-default I/O]]
- [[_COMMUNITY_Git + GitHub|Git + GitHub]]
- [[_COMMUNITY_Parameterized Queries Only|Parameterized Queries Only]]
- [[_COMMUNITY_Ruff (lint + format)|Ruff (lint + format)]]
- [[_COMMUNITY_mypy --strict typing|mypy --strict typing]]
- [[_COMMUNITY_Pydantic v2 models|Pydantic v2 models]]
- [[_COMMUNITY_Structured logs via structlog|Structured logs via structlog]]
- [[_COMMUNITY_Conventional Commits|Conventional Commits]]

## God Nodes (most connected - your core abstractions)
1. `SplitService` - 32 edges
2. `BillService` - 28 edges
3. `_setup_extracted_bill()` - 23 edges
4. `_upload()` - 22 edges
5. `_extract()` - 19 edges
6. `_sample_extraction()` - 19 edges
7. `AuthService` - 18 edges
8. `AppError` - 17 edges
9. `BillRepository` - 17 edges
10. `Base` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Validate, sniff format, strip EXIF/metadata by re-encoding.      Returns (re-enc` --uses--> `UnsupportedImageFormat`  [INFERRED]
  C:\home\bill-analyzer\backend\src\services\image_processing.py → C:\home\bill-analyzer\backend\src\core\exceptions.py
- `Root README.md (empty)` --references--> `Bill Analyzer Project`  [AMBIGUOUS]
  README.md → CLAUDE.md
- `Backend README.md (empty)` --references--> `backend/ directory (FastAPI service)`  [AMBIGUOUS]
  backend/README.md → CLAUDE.md
- `Run migrations in 'offline' mode.      This configures the context with just a U` --uses--> `Base`  [INFERRED]
  C:\home\bill-analyzer\backend\alembic\env.py → C:\home\bill-analyzer\backend\src\db\base.py
- `Run migrations in 'online' mode.      In this scenario we need to create an Engi` --uses--> `Base`  [INFERRED]
  C:\home\bill-analyzer\backend\alembic\env.py → C:\home\bill-analyzer\backend\src\db\base.py

## Hyperedges (group relationships)
- **LangGraph Bill Processing Pipeline** — claudemd_ocr_node, claudemd_parse_items_node, claudemd_categorize_node, claudemd_validate_node, claudemd_request_user_review, claudemd_bill_pipeline_py [EXTRACTED 1.00]
- **Bill + Items + Splits Data Model** — claudemd_db_bills, claudemd_db_bill_items, claudemd_db_splits, claudemd_db_split_participants, claudemd_db_users [EXTRACTED 1.00]
- **Privacy-First Local Inference Pattern** — claudemd_ollama, claudemd_local_first, claudemd_pii_handling, claudemd_vision_service [EXTRACTED 0.95]

## Communities

### Community 0 - "Bill & Split Domain"
Cohesion: 0.06
Nodes (39): Bill, BillItem, BillRepository, BillService, _to_decimal(), _utcnow(), Exception, AppError (+31 more)

### Community 1 - "Auth Flow"
Cohesion: 0.08
Nodes (14): login(), logout(), register(), AuthService, get_current_user(), get_db(), get_storage(), get_vision_service() (+6 more)

### Community 2 - "Project Architecture Overview"
Cohesion: 0.07
Nodes (35): Bill Analyzer Project, bill_items table, bills table, categories table (hierarchical), split_participants table, splits table, users table, Docker + docker-compose (+27 more)

### Community 3 - "Bill Review Tests"
Cohesion: 0.24
Nodes (27): _extract(), _FakeVision, _jpeg(), _override_vision(), _sample_extraction(), test_add_item_after_finalize_returns_409(), test_add_item_appends_to_end(), test_delete_item_after_finalize_returns_409() (+19 more)

### Community 4 - "Extraction Schemas"
Cohesion: 0.17
Nodes (26): LineItem, RawBillExtraction, _FakeVision, _jpeg(), _override_vision(), Returns (bill_id, [item_id, ...])., _setup_extracted_bill(), test_add_participant_links_user_by_email() (+18 more)

### Community 5 - "DB Layer & Models"
Cohesion: 0.09
Nodes (13): Base, Base, DeclarativeBase, Run migrations in 'offline' mode.      This configures the context with just a U, Run migrations in 'online' mode.      In this scenario we need to create an Engi, run_migrations_offline(), run_migrations_online(), UserSession (+5 more)

### Community 6 - "LangGraph Bill Pipeline"
Cohesion: 0.09
Nodes (27): src/agents/bill_pipeline.py (LangGraph), categorize_node, docs/model-eval.md (planned), End-to-end Tests (stubbed Ollama), Image Hash Cache (Redis or LRU), JWT/Session Auth Required, LangChain + LangGraph, Local-first (No PII to third parties) (+19 more)

### Community 7 - "Image Upload & Storage"
Cohesion: 0.13
Nodes (10): auth(), client(), _NullVisionService, postgres_url(), Default stand-in: tests that exercise extraction must override the dep., storage_root(), process_image(), Validate, sniff format, strip EXIF/metadata by re-encoding.      Returns (re-enc (+2 more)

### Community 8 - "Project Rules (CLAUDE.md)"
Cohesion: 0.12
Nodes (19): Alembic Migrations (mandatory), backend/ directory (FastAPI service), src/core/constants.py, frontend/ directory (TypeScript app), Rule: No stubs that lie (use NotImplementedError), Rule: Plan before implementing, Repository Structure, Repositories Pattern (src/services/repositories/) (+11 more)

### Community 9 - "Auth Schemas"
Cohesion: 0.23
Nodes (14): LoginRequest, RegisterRequest, TokenResponse, UserResponse, BaseModel, BillItemCreateRequest, BillItemResponse, BillItemUpdateRequest (+6 more)

### Community 10 - "Bill Upload Tests"
Cohesion: 0.2
Nodes (16): _jpeg_with_exif(), _png_bytes(), png_image(), MIME sniffing trumps the declared content type., Real image bytes are accepted regardless of declared MIME / filename., test_two_uploads_create_two_bills_with_distinct_paths(), test_upload_empty_returns_400(), test_upload_jpeg_returns_201_and_metadata() (+8 more)

### Community 11 - "Auth & Health Route Tests"
Cohesion: 0.21
Nodes (13): test_login_with_unknown_email_returns_401(), test_login_with_valid_credentials_returns_token(), test_login_with_wrong_password_returns_401(), test_logout_invalidates_token(), test_logout_one_session_does_not_affect_other(), test_me_with_invalid_token_returns_401(), test_me_with_valid_token_returns_user(), test_me_without_token_returns_401() (+5 more)

### Community 12 - "App Config & Bootstrap"
Cohesion: 0.16
Nodes (7): BaseSettings, get_settings(), Settings, configure_logging(), lifespan(), make_engine(), make_sessionmaker()

### Community 13 - "Bill Extraction Tests"
Cohesion: 0.36
Nodes (10): _FakeVision, _jpeg(), _override(), test_extract_other_users_bill_returns_404(), test_extract_propagates_invalid_vlm_response_as_502(), test_extract_propagates_ollama_unavailable_as_503(), test_extract_returns_parsed_extraction(), test_extract_unknown_bill_returns_404() (+2 more)

### Community 14 - "Vision Service Tests"
Cohesion: 0.46
Nodes (11): _make_service(), test_extract_attaches_bearer_when_api_key_set(), test_extract_handles_partial_extraction(), test_extract_omits_bearer_when_no_key(), test_extract_parses_full_response(), test_extract_raises_on_non_200(), test_extract_raises_on_timeout(), test_extract_raises_when_content_fails_schema() (+3 more)

### Community 15 - "Frontend Auth Client"
Cohesion: 0.28
Nodes (8): AuthProvider(), ApiError, apiRequest(), apiVoid(), clearToken(), getToken(), rawRequest(), setToken()

### Community 16 - "Bills API Routes"
Cohesion: 0.44
Nodes (10): add_item(), delete_item(), extract_bill(), finalize_bill(), get_bill(), list_bills(), _service(), update_bill() (+2 more)

### Community 17 - "Splits API Routes"
Cohesion: 0.58
Nodes (8): add_participant(), _bill_404_or_409(), get_split(), remove_participant(), _service(), set_item_participants(), settle_participant(), unsettle_participant()

### Community 18 - "Storage Backend Interface"
Cohesion: 0.46
Nodes (6): ABC, delete(), exists(), read(), StorageBackend, write()

### Community 19 - "Migration: create_bills"
Cohesion: 0.6
Nodes (3): downgrade(), create bills  Revision ID: 2b5a44e75983 Revises: 90a13ec22c7c Create Date: 2026-, upgrade()

### Community 20 - "Migration: bill_extraction_fields"
Cohesion: 0.6
Nodes (3): downgrade(), add_bill_extraction_fields_and_bill_items  Revision ID: 378472662208 Revises: 2b, upgrade()

### Community 21 - "Migration: splits_participants_item_shares"
Cohesion: 0.6
Nodes (3): downgrade(), add_splits_participants_item_shares  Revision ID: 3f19de8605c2 Revises: 37847266, upgrade()

### Community 22 - "Migration: create_users_and_sessions"
Cohesion: 0.6
Nodes (3): downgrade(), create users and user_sessions  Revision ID: 90a13ec22c7c Revises:  Create Date:, upgrade()

### Community 23 - "Frontend Bill Detail Page"
Cohesion: 0.7
Nodes (3): asNumber(), BillFields(), submit()

### Community 24 - "Health Endpoint"
Cohesion: 0.67
Nodes (1): health()

### Community 25 - "Me Endpoint"
Cohesion: 0.67
Nodes (1): me()

### Community 26 - "Frontend Login Page"
Cohesion: 0.67
Nodes (1): LoginPage()

### Community 27 - "Frontend Register Page"
Cohesion: 0.67
Nodes (1): RegisterPage()

### Community 28 - "Frontend Root Layout"
Cohesion: 0.67
Nodes (1): onUnauth()

### Community 29 - "Config Rationale"
Cohesion: 0.67
Nodes (3): src/core/config.py (sole env reader), .env.example (checked in), pydantic-settings env validation

### Community 30 - "Misc: Async-by-default I/O"
Cohesion: 1.0
Nodes (2): Async-by-default I/O, asyncpg + SQLAlchemy 2.0 async

### Community 79 - "Git + GitHub"
Cohesion: 1.0
Nodes (1): Git + GitHub

### Community 80 - "Parameterized Queries Only"
Cohesion: 1.0
Nodes (1): Parameterized Queries Only

### Community 81 - "Ruff (lint + format)"
Cohesion: 1.0
Nodes (1): Ruff (lint + format)

### Community 82 - "mypy --strict typing"
Cohesion: 1.0
Nodes (1): mypy --strict typing

### Community 83 - "Pydantic v2 models"
Cohesion: 1.0
Nodes (1): Pydantic v2 models

### Community 84 - "Structured logs via structlog"
Cohesion: 1.0
Nodes (1): Structured logs via structlog

### Community 85 - "Conventional Commits"
Cohesion: 1.0
Nodes (1): Conventional Commits

## Ambiguous Edges - Review These
- `Bill Analyzer Project` → `Root README.md (empty)`  [AMBIGUOUS]
  README.md · relation: references
- `backend/ directory (FastAPI service)` → `Backend README.md (empty)`  [AMBIGUOUS]
  backend/README.md · relation: references

## Knowledge Gaps
- **55 isolated node(s):** `Base error for application-level exceptions.`, `Raised when a write is attempted on a finalized (reviewed) bill.`, `Raised when finalize is called before extraction has produced data.`, `Raised when a participant name collides within a split.`, `List view — no items, no raw_ocr_text.` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Health Endpoint`** (3 nodes): `health.py`, `health.py`, `health()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Me Endpoint`** (3 nodes): `me.py`, `me.py`, `me()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Login Page`** (3 nodes): `login.tsx`, `login.tsx`, `LoginPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Register Page`** (3 nodes): `register.tsx`, `register.tsx`, `RegisterPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Frontend Root Layout`** (3 nodes): `__root.tsx`, `__root.tsx`, `onUnauth()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Misc: Async-by-default I/O`** (2 nodes): `Async-by-default I/O`, `asyncpg + SQLAlchemy 2.0 async`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Git + GitHub`** (1 nodes): `Git + GitHub`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Parameterized Queries Only`** (1 nodes): `Parameterized Queries Only`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Ruff (lint + format)`** (1 nodes): `Ruff (lint + format)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `mypy --strict typing`** (1 nodes): `mypy --strict typing`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Pydantic v2 models`** (1 nodes): `Pydantic v2 models`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Structured logs via structlog`** (1 nodes): `Structured logs via structlog`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Conventional Commits`** (1 nodes): `Conventional Commits`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Bill Analyzer Project` and `Root README.md (empty)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `backend/ directory (FastAPI service)` and `Backend README.md (empty)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `BillService` connect `Bill & Split Domain` to `Extraction Schemas`, `DB Layer & Models`, `Image Upload & Storage`, `Auth Schemas`, `Bills API Routes`, `Storage Backend Interface`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `SplitService` connect `Bill & Split Domain` to `Auth Flow`, `Auth & Health Route Tests`, `DB Layer & Models`, `Splits API Routes`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `RawBillExtraction` connect `Extraction Schemas` to `Bill & Split Domain`, `Auth Schemas`, `Bill Review Tests`, `Bill Extraction Tests`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `SplitService` (e.g. with `BillItemNotFound` and `BillNotEditable`) actually correct?**
  _`SplitService` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `BillService` (e.g. with `BillItemNotFound` and `BillNotEditable`) actually correct?**
  _`BillService` has 15 INFERRED edges - model-reasoned connections that need verification._
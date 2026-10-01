# Architecture

## Layered design

```
Presentation : textual TUI  ·  FastAPI skeleton
Services     : brand / channel / planning / analytics / media / publishing / scheduler
Agents (ADK) : root (router) → positioning / planning / content / publishing
Tools (ADK)  : wrap services as JSON tools
Domain       : SQLAlchemy models + pydantic schemas + enums
External     : LiteLLM (multi-provider LLM) · media providers · publisher adapters
```

Rule: **no business logic in the UI.** Both the TUI and a future dashboard call the same
services; agents reach services through tools; persistence is behind repositories.

## Data flow across agents

```
Positioning Agent ─▶ brands.* (positioning, pillars, voice)
Planning Agent   ─▶ plans.* + posts.*  ◀── insights_tools + history_tools
Content Agent    ─▶ assets.* (copy + media_spec, budget-enforced)
Publishing Agent─▶ posts.status draft→scheduled→published (+ metrics via mock)
Scheduler        ─▶ publishes due "scheduled" posts on an interval
```

## Storage notes

- SQLite (aiosqlite) sekarang, Postgres-ready (kontrol `HEADSOF_DB_URL`).
- Relasi di-`selectinload` secara default di repos agar tidak memicu lazy-load dalam sesi
  asyncio (yang memicu `MissingGreenlet`).

## Multi-provider LLM

`llm/models.py#role_model_string` memetakan peran ke string model LiteLLM (dari `.env`).
Ganti provider = edit env, bukan kode. Roles: positioning, planning, content, publishing,
orchestrator, default.

## Budget media

Batas keras di `config.py`: `MAX_IMAGES_PER_ASSET=5`, `MAX_VIDEOS_PER_ASSET=2`.
`media_service.check_media_budget` menolak spec yang melebihi; `media_tools.check_media_budget`
mengekspos ke agent. Depth konten men-deskripsikan berapa media yang direncanakan.

## Publishing abstraction

`publisher/Publisher` protocol → `publish(post, asset) -> PublishResult`. Phase 1 semua
platform diarahkan ke `MockPublisher` (mencatat metrics simulasi). Stub nyata
(IG/Threads/LinkedIn) siap diganti drop-in di phase 4.

## Scheduling

`PublishingScheduler` (APScheduler) memanggil `publish_due` tiap beberapa detik, menscan
post berstatus `scheduled` dan sudah lewat `scheduled_at`. Dihidupkan TUI dan lifespan API.
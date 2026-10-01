# DESIGN_SPEC.md — Head of Social Media Agent

## Overview

Multi-agent system yang mengelola branding (personal/business/product) secara end-to-end:
rekomendasi positioning, perencanaan konten bulanan, pembuatan konten per-channel, dan
publishing terjadwal multi-channel (Instagram, Threads, LinkedIn). Dibangun di atas Google
ADK, dengan model LLM multi-provider melalui LiteLLM, antarmuka TUI (Textual), dan service
layer yang siap untuk dashboard web (FastAPI).

## Example Use Cases

1. **Positioning** — User membangun brand bisnis kopi. Agent bertanya soal audience & diferensiasi
   (atau membaca file `company-profile.pdf`), lalu menyimpan positioning statement, pillars,
   dan voice ke brand.
2. **Monthly planning** — User minta "buat rencana konten bulan ini". Planning Agent membaca
   insights + history, menyusun theme/weeks/cadence/content-mix, lalu fan-out menjadi slot posting.
3. **Content creation** — Agent menulis caption native per channel (IG lebih visual+emoji,
   Threads pendek+diskusi, LinkedIn profesional). Memilih depth konten dan generate media
   (mock; image phase 2, video phase 3), dalam budget maks 5 gambar / 2 video.
4. **Publishing** — Agent menjadwalkan posting, scheduler mempublish saat jatuh tempo via
   publisher adapter (mock), mencatat simulated metrics.

## Tools Required

- **LiteLLM** — multi-provider LLM (Gemini/OpenAI/Anthropic/Ollama) via ADK `LiteLlm`.
- **SQLAlchemy asyncio + aiosqlite** — penyimpanan (Postgres-ready).
- **Textual** — TUI.
- **APScheduler** — scheduling posting.
- **pypdf / python-docx** — ekstraksi dokumen positioning.
- API key provider sesuai model yang dipakai (lihat `.env.example`).

## Constraints & Safety Rules

- **Media budget hard-capped**: maks 5 gambar dan 2 video per asset — tidak bisa dilewati.
- **Image generation (Phase 2)**: provider nyata via LiteLLM (`HEADSOF_MEDIA_PROVIDER=litellm`,
  model `HEADSOF_MEDIA_IMAGE_MODEL`, mis. `gemini/imagen-3.0-generate-002` atau
  `openai/gpt-image-1`). Default `mock` menulis file placeholder tanpa jaringan. Video = Phase 3.
  File media disajikan FastAPI di `/media/`.
- Positioning & planning **wajib evidence-driven**: Planning Agent harus memanggil insights
  dan history sebelum menyusun rencana (bukan menebak).
- Tidak ada posting ke platform nyata di phase 1; hanya mock publisher. Sisa stubs
  (IG/Threads/LinkedIn) melempar `NotImplementedError` sampai phase 4.
- Utility jail: tools harus return dict JSON-serializable; define docstring + tipe untuk LLM.

## Success Criteria

- E2E: buat brand → positioning → rencana bulanan → fan-out → isi konten per-channel →
  jadwalkan → publish due → timbul metrics → insights bisa dibaca agent.
- Media budget: 6 gambar atau 3 video ditolak; 5/2 diterima.
- Copy berbeda native antara IG, Threads, LinkedIn untuk pillar yang sama.
- Rencana bulan kedua merujuk history bulan pertama (tidak duplikasi, angkat winner).
- `uv run pytest` hijau; `uv run ruff check .` bersih; API `/healthz` 200.

## Edge Cases to Handle

1. Brand tanpa positioning lengkap → Positioning Agent interview Q&A dulu.
2. Post tanpa asset → jangan publish; laporkan butuh konten.
3. Media spec melebihi budget → ditolak dengan pesan jelas.
4. Post jatuh tempo tanpa kahir bulan (scheduled_at null) → dibiarkan draft.
5. Dokumen kosong/unsupported → tool return error, agent lanjut interview.
6. Scheduler gagal di satu post → tandai failed, lanjut ke post lain.

## Structure

```
src/headofsocial/
  config.py            # settings + media budget + LLM role map
  domain/              # enums, SQLAlchemy models, pydantic schemas
  storage/             # async engine/session, repos (eager-loaded)
  channels/styles.py   # per-platform style profiles
  publishing/          # Publisher protocol + mock/stubs
  services/            # brand, channel, planning, analytics, media, publishing, scheduler
  tools/               # ADK tools wrapping services
  agents/              # root + positioning/planning/content/publishing
  tui/                 # Textual screens (composer, brands, calendar)
  api/                 # FastAPI: healthz + dashboard REST + SSE chat + serve SPA
web/                   # React + Vite SPA (Composer/Brands/Channels/Calendar/Insights)
tests/
  unit/                # media budget, publishing, analytics, planning
  integration/         # tool round-trip, publish_due, media generation
```

## Web Dashboard

React + Vite SPA di `web/`, memakai service layer & REST API yang sama dengan TUI.

- REST: `/api/dashboard/*` (brands, channels, plans, posts, insights, assets/media).
- Chat agent live: SSE `GET /api/chat/stream?message=...` (event `start`/`token`/`done`).
- `services/chat_service.py` — satu ChatService (ADK Runner) dipakai TUI & web.
- Dev: `make web` (API :8080 + Vite :5173 proxy /api). Prod: `make web-build`, SPA
  disajikan FastAPI di `/app/`.

Dokumen detail: `docs/architecture.md` dan rencana lengkap di `~/.commandcode/plans/head-of-social-media-agent.md`.
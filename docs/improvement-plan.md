# Improvement Plan — HeadOfSocialMediaAgent

> Status: DRAFT · Tanggal: 2026-09-30
> Tujuan: membuat agent cukup kuat untuk personal branding end-to-end.
> Prinsip: perbaiki rantai putus dulu (Fase A), baru fitur bernilai (Fase B), baru integrasi eksternal (Fase C).

---

## 1. Ringkasan Analisa

### Kondisi sekarang
- Stack: Google ADK + LiteLLM, FastAPI + SSE, SQLAlchemy async + SQLite, APScheduler, Textual TUI.
- Pipeline desain: `root → positioning → planning → content → publishing`.
- Yang sudah bagus: brand/positioning persist di DB, style per-channel (`channels/styles.py`), media budget enforcement, fan-out plan → slot posts, scheduler polling.

### Skor
| Aspek | Nilai | Catatan |
|---|---|---|
| Arsitektur | 7/10 | Layer bersih (agents/tools/services/storage) |
| Eksekusi pipeline | 4/10 | Rantai asset→post putus, pipeline tidak jalan end-to-end |
| Personal branding fit | 3/10 | Tidak ada voice samples, revision loop, repurposing |
| Data/learning loop | 2/10 | Semua metrics random (mock) |

### Verdict
**Belum siap dipakai.** Bug fatal: konten yang digenerate tidak pernah terhubung ke jadwal, sehingga publish selalu gagal. Setelah Fase A → "berfungsi". Setelah Fase B → "kuat untuk personal branding".

---

## 2. Daftar Masalah

### P0 — Fatal (pipeline mati)

| ID | Masalah | Lokasi | Dampak |
|---|---|---|---|
| P0-1 | `create_asset` tidak set `post.asset_id`; tidak ada tool linking asset↔post | `tools/media_tools.py`, `domain/models.py` | Konten yatim piatu. Publishing agent cek "jangan publish tanpa asset" → selalu gagal. |
| P0-2 | Prompt content_agent panggil `get_post(post_id)` yang tidak exist | `agents/prompts.py:64` | Content agent tidak bisa baca detail slot (pillar, channel, waktu) → konten generik, tool call error. |
| P0-3 | `approve_post` tidak validasi `scheduled_at` padahal prompt bilang wajib | `tools/calendar_tools.py`, `services/publishing_service.py` | Post approved tanpa waktu → scheduler skip selamanya, silent. |

### P1 — Serius (foot-gun, single-user)

| ID | Masalah | Lokasi | Dampak |
|---|---|---|---|
| P1-1 | `.env.example` pakai `LLM_ROLE_*` tanpa prefix `HEADSOF_` | `.env.example`, `config.py` | Model per-role diabaikan diam-diam. |
| P1-2 | `InMemorySessionService` + session_id hardcode `"chat"`, user_id `"web-user"` | `services/chat_service.py:24`, `api/routes/chat.py:15` | Restart = amnesia chat. Tidak multi-user. Concurrent request tabrakan di global `_chat`. |
| P1-3 | `generate_media` pakai prompt pertama untuk semua n item | `services/media_service.py` | Carousel 5 gambar = 5 gambar sama. |
| P1-4 | README/Makefile drift: `make web`, frontend React didokumentasi tapi tidak ada | `README.md`, `Makefile` | Onboarding menyesatkan. |

### P2 — Kualitas (perbaiki saat lewat)

| ID | Masalah | Lokasi |
|---|---|---|
| P2-1 | `_estimate_slot` crude: semua slot per channel/minggu timestamp sama; `posts_per_week` fallback hardcode 3 | `services/planning_service.py:~100` |
| P2-2 | CORS `allow_origins=["*"]`, tanpa auth | `api/app.py` |
| P2-3 | `Channel.credentials` plaintext JSON di SQLite | `domain/models.py` |
| P2-4 | Tidak ada Alembic; `create_all` only | `storage/db.py` |
| P2-5 | Naive datetime `.replace(tzinfo=None)` tersebar → risiko tz bug | multiple |
| P2-6 | `_deps.run()` tanpa rollback-on-error; double-commit di `create_asset` | `tools/_deps.py` |
| P2-7 | Test wipe shared sqlite file, tidak in-memory isolated | `tests/conftest.py` |

### GAP — Fitur personal branding yang belum ada

| ID | Gap | Kenapa penting untuk personal branding |
|---|---|---|
| G-1 | Voice samples / few-shot dari tulisan asli user | `voice_tone` 1 field teks tidak cukup. Tanpa contoh nyata, output terdengar AI, bukan "seperti saya". Ini pembeda #1. |
| G-2 | Revision loop (draft → feedback → regenerate) | Personal brand = reputasi pribadi. Approve binary tidak cukup; user harus bisa koreksi nada sebelum tayang. |
| G-3 | Repurposing 1 ide → multi format | Inti efisiensi personal branding: 1 pilar → thread Threads + carousel IG + artikel LinkedIn. Sekarang tiap channel digenerate terpisah. |
| G-4 | Trend/topical input | Agent buta dunia luar. Personal branding hidup dari relevansi. |
| G-5 | Real publishing + analytics | Semua mock, metrics random → planning "evidence-driven" analisa noise. Tanpa data asli tidak ada learning loop. |

---

## 3. Roadmap

```
Fase A (fix pipeline)  →  Fase B (fitur PB)  →  Fase C (dunia nyata)
   1-2 hari                 3-5 hari              1-2 minggu
   WAJIB                    NILAI UTAMA           SETELAH ADA USER
```

---

## 4. Fase A — Perbaiki Rantai Putus

Estimasi: 1-2 hari. Tanpa fitur baru. Setiap task punya acceptance test.

### A1. Tool `get_post` + `attach_asset` (fix P0-1, P0-2)
- File: `tools/calendar_tools.py` (get_post), `tools/media_tools.py` atau calendar (attach_asset)
- `get_post(post_id)` → return id, brand_id, channel, pillar, status, scheduled_at, asset_id, depth_hint.
- `attach_asset(post_id, asset_id)` → set `post.asset_id`, validasi post & asset exist + brand sama.
- Daftarkan ke `content_agent`; update `agents/prompts.py` CONTENT_INSTRUCTION: step baca slot pakai `get_post`, step akhir wajib `attach_asset`.
- **Acceptance**: integration test — fan_out plan → content agent flow (service-level) → post punya `asset_id` → `publish_now` sukses.

### A2. Validasi `approve_post` (fix P0-3)
- File: `tools/calendar_tools.py` / `services/publishing_service.py`
- Reject dengan pesan jelas jika `scheduled_at` null ATAU `asset_id` null.
- **Acceptance**: unit test 3 kasus (no schedule, no asset, valid).

### A3. Fix `.env.example` (fix P1-1)
- Semua `LLM_ROLE_*` → `HEADSOF_LLM_ROLE_*`. Verifikasi tiap key di `.env.example` match field `config.py`.
- **Acceptance**: script/test kecil load `.env.example` via pydantic-settings → semua key dikenali.

### A4. Session persistence + multi-user (fix P1-2)
- File: `services/chat_service.py`, `api/routes/chat.py`
- Ganti `InMemorySessionService` → `DatabaseSessionService` (ADK bawaan, pakai SQLite yang sama).
- `user_id` + `session_id` dari request (query param / header), fallback default untuk TUI.
- Hilangkan state global `_chat` yang tidak thread-safe; ganti dependency FastAPI.
- **Acceptance**: restart server → riwayat session tetap ada; 2 user_id beda → session terpisah.

### A5. Fix `generate_media` multi-prompt (fix P1-3)
- File: `services/media_service.py`
- Loop per prompt, bukan prompt[0] × n.
- **Acceptance**: unit test — 3 prompt → 3 media call beda.

### A6. Sinkronkan README/Makefile (fix P1-4)
- Hapus/koreksi `make web`, referensi frontend React. Dokumentasikan yang benar-benar ada (API, TUI).

---

## 5. Fase B — Fitur Personal Branding

Estimasi: 3-5 hari. Urutan = urutan nilai.

### B1. Voice Samples (G-1) — dampak terbesar
- **Schema**: tabel `writing_samples` (id, brand_id, channel opsional, text, note, created_at). Migrasi: karena belum ada Alembic, tambah ke `create_all` (lihat C4 untuk Alembic).
- **Tools**: `add_writing_sample(brand_id, text, channel?, note?)`, `list_writing_samples(brand_id)` di `tools/brand_tools.py`.
- **Injeksi**: content_agent — saat generate, ambil 3-5 sample brand (prioritas channel sama) → masuk prompt sebagai few-shot: "Tulis dengan gaya seperti contoh berikut: …".
- **Flow user**: positioning_agent di akhir interview minta user paste 3-5 tulisan asli (post lama, email, apapun).
- **Acceptance**: unit test tools; manual eval — bandingkan output dengan/tanpa samples.

### B2. Revision Loop (G-2) — inti trust
- **Schema**: `Post.status` tambah `in_review`; tabel `post_revisions` (post_id, feedback, previous_asset_id, created_at) untuk audit trail.
- **Flow status**: `draft → in_review → approved → published` (+ `in_review → draft` saat revisi diminta).
- **Tools**:
  - `submit_for_review(post_id)` — content_agent panggil setelah attach_asset.
  - `request_revision(post_id, feedback)` — publishing_agent/user; simpan feedback, status balik `draft`.
  - `get_revision_feedback(post_id)` — content_agent baca feedback sebelum regenerate.
- **Prompt**: CONTENT_INSTRUCTION — jika post punya feedback pending, WAJIB baca dan address di versi baru.
- **Acceptance**: integration test — draft → review → revisi dengan feedback → regenerate → approve.

### B3. Repurposing (G-3) — murah, reuse infra
- **Tool**: `repurpose_post(post_id, target_channel)` di `tools/calendar_tools.py`:
  1. Ambil source post + asset.
  2. Buat post baru target channel (pillar & topik sama, scheduled_at kosong → user tentukan).
  3. Return konten sumber + `get_channel_style(target)` → content_agent transform.
- **Prompt**: tambah alur "repurpose" di CONTENT_INSTRUCTION — pertahankan ide inti, tulis ulang native untuk channel target (bukan copy-paste + potong).
- **Acceptance**: integration test — post IG → repurpose LinkedIn → post baru linked ke source (kolom `source_post_id`).

### B4. Slot scheduling lebih baik (P2-1, pendukung B1-B3)
- `_estimate_slot`: sebar slot dalam minggu (hari berbeda), pakai `best_times` dari insights jika ada.
- `posts_per_week` dari channel config, bukan hardcode 3.
- **Acceptance**: unit test — 3 post/minggu → 3 hari berbeda.

---

## 6. Fase C — Dunia Nyata

Estimasi: 1-2 minggu. Mulai HANYA setelah A+B stabil dan dipakai.

### C1. Real publisher: Threads dulu (G-5)
- Alasan: API gratis, OAuth sederhana, personal-brand friendly.
- Implement `publishing/threads.py` (sekarang `NotImplementedError`): OAuth token per channel, publish text/image, fetch metrics (views, likes, replies).
- Registry (`publishing/base.py`): map `threads` → real publisher via env flag `HEADSOF_PUBLISHER_THREADS=real|mock`.
- **Prasyarat keamanan** (dari P2-3): enkripsi `Channel.credentials` — minimal Fernet dengan key dari env `HEADSOF_SECRET_KEY`. JANGAN simpan token plaintext.
- **Acceptance**: post test ke akun Threads sandbox; metrics masuk DB; insights_tools baca data asli.

### C2. Analytics loop asli
- Scheduler job kedua: tiap 6 jam fetch metrics post published (yang punya real publisher).
- `simulate_metrics` hanya untuk channel mock — tandai metrics `is_simulated` agar planning bisa filter/downweight.
- **Acceptance**: planning_agent prompt update — sebut sumber data; test aggregasi campur real+simulated.

### C3. Trend input (G-4)
- Mulai minimal: tool `add_topic_idea(brand_id, topic, source?)` + `list_topic_ideas` — user/eksternal feed ide topikal manual.
- Planning_agent wajib cek topic ideas saat buat plan.
- Scraping/API trend = di luar scope sampai ada kebutuhan nyata (YAGNI).

### C4. Hardening (P2 sisa)
- Alembic init + migrasi awal (sebelum schema berubah lagi di production).
- Auth API: minimal bearer token statis dari env; CORS whitelist.
- Timezone: simpan UTC aware di DB, konversi di edge; hapus `.replace(tzinfo=None)`.
- `_deps.run()`: try/except → rollback; hapus double-commit.
- Tests: conftest pakai in-memory sqlite (`sqlite+aiosqlite:///:memory:` + StaticPool).

---

## 7. Yang Sengaja TIDAK Dikerjakan (YAGNI)

| Ide | Kenapa tidak |
|---|---|
| Frontend web React | TUI + API cukup untuk 1 user. Bangun setelah ada >1 user nyata. |
| Instagram/LinkedIn real publisher | API approval berat. Threads dulu, buktikan loop-nya. |
| Auto trend scraping | Rapuh, ToS risk. Manual topic input dulu. |
| Multi-tenant auth penuh | Single bearer token cukup untuk personal use. |
| A/B testing konten | Butuh volume post yang belum ada. |
| Vector DB untuk voice | 3-5 few-shot samples di prompt cukup; embed/retrieval = overkill. |

---

## 8. Urutan Eksekusi & Dependensi

```
A1 ──► A2 ──► (A3, A5, A6 paralel) ──► A4
                                        │
              B1 ◄──────────────────────┘
              B2 (butuh A1)
              B3 (butuh A1, B1)
              B4 (independen)
                       │
              C1 ──► C2
              C3 (independen)
              C4 (kapan saja, prioritas Alembic sebelum B1 schema change*)
```
\* Catatan: idealnya Alembic (C4) masuk SEBELUM B1/B2 menambah tabel. Jika ingin cepat, `create_all` masih aman selama development single-user; wajib Alembic sebelum deploy.

## 9. Definisi Selesai per Fase

- **Fase A selesai** = flow lengkap jalan tanpa error: buat brand → positioning → plan → fan-out → content + asset ter-attach → approve (tervalidasi) → scheduler publish (mock) → metrics tercatat. Dibuktikan 1 integration test end-to-end.
- **Fase B selesai** = user bisa: paste writing samples & output terasa berbeda; minta revisi dengan feedback & hasil address feedback; repurpose 1 post ke channel lain.
- **Fase C selesai** = minimal 1 post tayang asli di Threads, metrics asli masuk planning bulan berikutnya, credentials terenkripsi.

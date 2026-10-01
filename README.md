<div align="center">

# 🎬 Head of Social Media Agent

**Sistem multi-agent yang menjalankan branding media sosial Anda secara end-to-end.**

Dari strategi positioning, perencanaan konten bulanan, penulisan caption native per
channel, sampai publishing terjadwal — semua dijalankan oleh satu orkestra agent.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![uv](https://img.shields.io/badge/uv-managed-7C3AED?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-multi--provider-0F172A)](https://docs.litellm.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

**Head of Social Media Agent** adalah *AI Head of Social Media* yang menggantikan
rutinitas manual mengelola media sosial: ia mewawancarai Anda untuk membangun positioning,
menyusun kalender konten berbasis data, menulis copy yang terasa *native* di tiap platform
(Instagram, Threads, LinkedIn), membuat visual yang konsisten dengan identitas brand, lalu
menjadwalkan dan mempublikasikannya.

Dibangun di atas **Google ADK** (Agent Development Kit), model LLM multi-provider lewat
**LiteLLM** (Gemini, OpenAI, Anthropic, OpenRouter, Ollama, dst.), antarmuka **TUI** (Textual)
dan **Web Dashboard** (React + FastAPI).

---

## ✨ Fitur

| Agent | Tugas |
| --- | --- |
| 🧭 **Positioning Agent** | Interview interaktif + baca dokumen → positioning statement, target audience, differentiators, voice, content pillars, dan identitas visual terkunci. |
| 📅 **Planning Agent** | Menyusun rencana editorial bulanan *evidence-driven* (insights + history + riset), lalu *fan-out* jadi slot posting. |
| ✍️ **Content Agent** | Menulis caption native per channel dengan budget media yang ditegakkan keras (maks 5 gambar / 2 video). |
| 🎨 **Media Generation Agent** | Generate gambar/video dari brief + foto referensi brand, dengan *fidelity* ketat (identitas wajah/logo/produk terjaga). |
| 🚀 **Publishing Agent** | Jadwalkan, approve, dan publish via adapter publisher (mock dulu, adapter nyata siap dipasang). |

**Sorotan:**

- 🔀 **Multi-brand** — kelola banyak brand (personal/business/product) dengan bahasa per brand/channel.
- 🗓️ **Publishing terjadwal** — scheduler otomatis mempublish posting yang jatuh tempo.
- 🎯 **Copy native per channel** — gaya berbeda untuk IG (visual+emoji), Threads (pendek+diskusi), LinkedIn (profesional).
- 🔒 **Identitas visual terkunci** — kode yang memegang style, LLM hanya mengisi bagian kreatif, sehingga setiap post konsisten.
- 💬 **Web Dashboard + TUI** — Composer streaming, Brands, Channels, Studio, Calendar, Insights.

---

## 🧠 Arsitektur Agent

```
User ──▶ Root Agent (router)
              │  transfer
              ▼
   ┌────────────────────────────────────────────┐
   │ Positioning ─▶ Planning ─▶ Content ─▶ Publishing │
   │      │             │           │            │      │
   │      ▼             ▼           ▼            ▼      │
   │  brands.*     plans/posts   assets.*    posts.status│
   └────────────────────────────────────────────┘
              │
              ▼
   Media Generation Agent (parallel per item)
```

Alur data: **Positioning** membangun brand → **Planning** membuat rencana bulanan → **Content**
menulis caption + mendelegasikan media → **Publishing** menjadwalkan & mempublikasikan.

*Detail lengkap: [docs/architecture.md](docs/architecture.md) dan [DESIGN_SPEC.md](DESIGN_SPEC.md).*

---

## 🚀 Quickstart

### Prasyarat

- **Python 3.12+** dan **[uv](https://docs.astral.sh/uv/)**
- API key provider LLM (opsional — lihat [.env.example](.env.example))

### Instalasi

```bash
git clone <repo-url> && cd HeadOfSocialMediaAgent
uv sync
cp .env.example .env      # isi API key yang kamu pakai
```

### Menjalankan

```bash
make install   # uv sync
make tui       # TUI (streaming root agent + CRUD brand/kalender)
make api       # FastAPI (REST API + SSE chat, /api/healthz)
make web       # Web dashboard (FastAPI + Vite dev server)
make test      # pytest
make lint      # ruff
```

Tanpa API key pun aplikasi tetap bisa dijalankan (media provider default `mock` menghasilkan
placeholder tanpa jaringan).

---

## 📦 Contoh (Contoh Data)

Untuk melihat bentuk nyata dari *output* sistem, repo ini menyertakan contoh yang siap dibaca
langsung oleh agent di dalam folder `data/`:

| Path | Isi |
| --- | --- |
| [`data/docs/company-profile.md`](data/docs/company-profile.md) | Contoh dokumen positioning yang bisa dibaca Positioning Agent. |
| [`data/examples/positioning.json`](data/examples/positioning.json) | Contoh output rekomendasi positioning (lengkap dengan visual style). |
| [`data/examples/monthly-plan.json`](data/examples/monthly-plan.json) | Contoh rencana konten bulanan. |
| [`data/examples/captions/`](data/examples/captions/) | Contoh caption native untuk pillar yang sama di Instagram, Threads, dan LinkedIn. |
| [`data/media/README.md`](data/media/README.md) | Struktur & konvensi nama media hasil generate + contoh creative brief. |

Lihat [`data/examples/README.md`](data/examples/README.md) untuk penjelasan lengkap.

---

## 🏗️ Struktur Proyek

```
src/headofsocial/
  config.py            # settings + media budget + LLM role map
  domain/              # enums, SQLAlchemy models, pydantic schemas
  storage/             # async engine/session, repos
  channels/styles.py   # per-platform style profiles (IG/Threads/LinkedIn)
  publishing/          # Publisher protocol + mock/stubs
  services/            # brand, channel, planning, analytics, media, publishing, scheduler
  tools/               # ADK tools wrapping services
  agents/              # root + positioning/planning/content/media/publishing
  media/               # prompt builder, postprocess, vision
  tui/                 # Textual screens
  api/                 # FastAPI: REST + SSE chat + SPA
web/                   # React + Vite SPA
data/                  # database, dokumen, media, contoh (sebagian di-commit)
tests/                 # unit + integration
```

---

## 🧪 Testing

```bash
uv run pytest           # semua test
uv run ruff check .     # lint
```

---

## 📚 Dokumentasi

- [DESIGN_SPEC.md](DESIGN_SPEC.md) — spesifikasi & kriteria sukses.
- [docs/architecture.md](docs/architecture.md) — arsitektur berlapis & alur data.
- [docs/agent-architecture-plan.md](docs/agent-architecture-plan.md) — rencana arsitektur agent.
- [docs/chat-ux-plan.md](docs/chat-ux-plan.md) — desain UX composer.

---

## 🤝 Kontribusi

Kontribusi sangat diterima. Silakan buka issue untuk diskusi atau kirim pull request.

---

## 📄 Lisensi

[MIT](LICENSE)

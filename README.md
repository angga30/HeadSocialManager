# Head of Social Media Agent

Multi-agent system yang mengelola branding (personal / business / product) secara end-to-end:
rekomendasi positioning, perencanaan konten bulanan, pembuatan konten yang disesuaikan
per-channel (Instagram, Threads, LinkedIn), dan publishing terjadwal multi-channel.

Dibangun di atas **Google ADK** (Agent Development Kit) dengan model multi-provider via
LiteLLM, antarmuka **TUI** (Textual) untuk sekarang, dan service layer yang siap dipakai
dashboard web (FastAPI) nanti.

## Fitur Utama

- **Positioning Agent** — interview interaktif + baca dokumen, menghasilkan positioning
  statement, target audience, differentiators, voice, dan content pillars.
- **Planning Agent** — menyusun rencana editorial bulanan berbasis data (insights +
  history konten), lalu fan-out menjadi jadwal posting.
- **Content Agent** — menulis copy yang sesuai gaya tiap channel, dengan kedalaman konten
  dan budget media (maks 5 gambar / 2 video per konten).
- **Publishing Agent** — menjadwalkan & mempublikasikan posting via publisher adapter
  (mock dulu, adapter IG/Threads/LinkedIn siap diganti).
- **Multi-brand**, bahasa konten per brand/channel, publishing terjadwal.

## Prasyarat

- Python 3.12+ dan [uv](https://docs.astral.sh/uv/)
- API key untuk provider LLM yang dipakai (Optional — Lihat `.env.example`)

## Setup

```bash
uv sync
cp .env.example .env      # lalu isi API key yang kamu pakai
```

## Menjalankan

```bash
make install   # uv sync
make tui       # jalankan TUI (streaming root agent + CRUD brand/kalender)
make api       # jalankan FastAPI (REST API + SSE chat, /api/healthz)
make web       # jalankan web dashboard (FastAPI + Vite dev server)
make test      # pytest
```

## Web Dashboard

- `make web` — API di `http://localhost:8080`, frontend React (Vite) membuka browser.
- Halaman: Composer, Brands, Channels, Studio, Calendar, Insights.
- Build untuk produksi: `make web-build` (Vite build disajikan FastAPI di `/app/`).

### Composer

- **Multi-conversation** — banyak percakapan; pindah/buka halaman lain tidak menghentikan
  proses yang sedang jalan. Riwayat & konteks agent disimpan di server (tahan restart).
- **Streaming & transparansi** — balasan mengalir kata-per-kata; nama agent aktif, langkah
  tool (collapsible, ala "steps"), dan indikator status tampil selama agent bekerja.
- **Kontrol** — **Stop** benar-benar menghentikan run di server (balasan parsial ditandai
  `(dihentikan)`); **ulangi/retry** pesan terakhir atau dari **banner error**; judul
  percakapan otomatis dari pesan pertama.
- **Status** — `sedang memproses` / `siap` / `berhenti·error` per percakapan.
- **Markdown** — balasan agent dirender (list, tabel, bold, link) dengan **syntax highlight**
  dan tombol **copy** per code block; hover pesan untuk copy seluruh balasan.
- **Auto-scroll** — mengikuti stream selama user di bawah, plus tombol ↓ saat scroll ke atas,
  dan **suggested prompts** di percakapan kosong.
- **Mention** — ketik `@` untuk menyebut brand/channel/post; entitas itu jadi konteks agent.

TUI (`make tui`) memakai protokol stream yang sama: balasan streaming + indikator status, dan
memuat riwayat percakapan terakhir saat dibuka.

## Log & Observability

Setiap run agent mencatat jejak prosesnya (agent apa, memanggil tool apa, iterasi ke berapa,
transfer antar-agent, dan ringkasan durasi) lewat plugin `AgentTracePlugin`.

```bash
tail -f data/logs/app.log        # TUI: log ke file saja
# make api / make web: juga tampil di konsol
```

Contoh keluaran:

```
▶ RUN start | session=conv-1 inv=e-c1ad82
  ▶ agent: root_agent
    · llm call #1 (agent=root_agent, iterasi ke-1)
    · tool: transfer_to_agent(agent_name='content_agent')
    ⇄ transfer: root_agent → content_agent
    ▶ agent: content_agent
      · llm call #2 (agent=content_agent, iterasi ke-1)
      · tool: get_post(post_id=1)
      ← get_post (0.01s) → ok (2 field)
      · tool: create_asset(brand_id=1, depth='visual', image_briefs=[1 item])
      ← create_asset (0.00s) → id=1, status=draft
      · tool: generate_media(asset_id=1)
      ← generate_media (6.29s) → asset_id=1
      · tool: attach_asset(post_id=1, asset_id=1)
      ← attach_asset (0.01s) → ok (2 field)
    ◀ agent: content_agent
✅ RUN done in 31.0s | llm=8 | tool=7 | agents=[root_agent → content_agent]
```

Logger: `headofsocial.agent_trace` (lihat `src/headofsocial/agents/trace_plugin.py`).

### Troubleshooting

- **`attempt to write a readonly database`** — SQLite tidak bisa menulis. Penyebab umum:
  folder `data/` tidak writable, **atau file DB dihapus/dipindah saat server masih berjalan**
  (handle-nya menunjuk file yang sudah hilang). Perbaikan: hentikan server, pastikan `data/`
  bisa ditulis (atau `rm -rf data && mkdir data`), lalu jalankan ulang. Jangan menghapus
  `data/` selama server jalan.
- Path DB selalu absolut (`data/headofsocial.db` di root project), jadi tidak bergantung CWD.
- SQLite memakai **WAL + busy_timeout** karena ada dua engine yang menulis file yang sama
  (engine aplikasi + `DatabaseSessionService` milik ADK).

## Dokumentasi

- `DESIGN_SPEC.md` — spesifikasi lengkap dan arsitektur.
- `docs/architecture.md` — detail arsitektur berlapis.# HeadSocialManager

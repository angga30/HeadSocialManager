# Agent Architecture & Media Consistency Plan

> Status: DRAFT · Tanggal: 2026-10-01
> Scope: arsitektur agent, web research (Tavily), identitas visual brand, konsistensi media.
> Keputusan produk (dari diskusi): provider media **fleksibel/agnostic**, aset brand **campur** (sebagian upload nyata, sebagian full AI), web search untuk **trend + kompetitor**.

---

## 1. Analisa Arsitektur Sekarang

### Pola
- ADK `sub_agents` LLM-driven transfer: `root → {positioning, planning, content, publishing}` (`root_agent.py:16-32`).
- Konteks antar-agent: **hanya conversation + DB via tools**. Tidak pakai `session.state`, artifacts, atau memory ADK.
- `DatabaseSessionService` hanya untuk persist percakapan.

### Yang sehat ✅
| Hal | Bukti |
|---|---|
| Separation agents/tools/services/storage | struktur `src/headofsocial/` |
| Planning evidence-driven (wajib 5 tools dulu) | `prompts.py:40-63` |
| Depth system + budget keras (5 img/2 vid) | `media_service.counts_for_depth`, enforce di 3 titik |
| Channel style per platform | `channels/styles.py` |
| Video capability dicek sebelum generate | `media_service.generate_media` |

### Yang lemah ❌
| ID | Masalah | Bukti | Dampak |
|---|---|---|---|
| AR-1 | **Zero identitas visual brand** — Brand model tidak punya warna/logo/foto/style | `models.py` Brand fields | Image prompt tanpa grounding → tiap post beda gaya total. Akar masalah konsistensi. |
| AR-2 | **Media prompt 100% karangan LLM per-item, tanpa anchor** | `media_tools.py` media_spec verbatim | Konsistensi mustahil; LLM tiap kali "kreatif ulang". |
| AR-3 | **Tidak ada aspect ratio per platform** | hanya global `media_image_size`, `config.py` | IG butuh 4:5/1:1, LinkedIn 1.91:1 — sekarang semua sama. |
| AR-4 | **Tidak ada web search / data eksternal** | nihil di seluruh codebase | Planning & positioning buta trend dan kompetitor. |
| AR-5 | `positioning_formatter` + output_schema = dead code | `positioning_agent.py:32-42`, tak pernah di-wire | Output positioning tidak terstruktur-tervalidasi. |
| AR-6 | `_VIDEO_OK` dihitung saat import module | `prompts.py:5` | Ganti provider runtime → prompt basi. |
| AR-7 | Provider interface tanpa reference-image/seed | `media_providers.py` Protocol | Tidak bisa pakai fitur consistency provider modern. |
| AR-8 | Transfer antar-agent LLM-only tanpa state passing | root_agent | Sub-agent sering re-fetch brand dari DB; brand aktif tidak "menempel" di sesi. |

### Penilaian pola orchestration
Pola `sub_agents` transfer **sudah tepat** untuk use case ini — jangan ganti ke SequentialAgent/graph. Alur user non-linear (kadang langsung minta konten, kadang revisi plan). Yang perlu diperbaiki bukan polanya, tapi **grounding** (AR-1/2/3) dan **input eksternal** (AR-4).

---

## 2. Jawaban 3 Pertanyaan

### Q1: Apakah Tavily membantu? → **Ya, signifikan. Dua titik injeksi.**

Tanpa data eksternal, "Head of Social Media" ini bekerja dalam ruang hampa: plan bulanan hanya dari engagement history (yang saat ini mock/random) dan positioning hanya dari interview. Social media real hidup dari relevansi.

| Titik | Agent | Nilai |
|---|---|---|
| **Trend/topik niche** | planning + content | Plan bulanan punya hook aktual ("minggu ini ramai X di industri Anda"); konten tidak evergreen-hambar semua. |
| **Riset kompetitor/market** | positioning | Interview positioning diperkaya: "kompetitor Anda positioning-nya Y, celah Anda di Z". Differentiators berbasis fakta, bukan klaim user semata. |

Kenapa Tavily (bukan scraping/SerpAPI): API search-for-LLM, hasil sudah bersih + ringkas, free tier 1000 req/bulan — cukup untuk cadence bulanan planning. Alternatif setara: Exa. Keduanya satu interface `search(query) → results` — abstraksi tipis saja.

**Bukan** untuk: real-time trending-tab scraping per platform (rapuh, ToS risk — tetap YAGNI sesuai improvement-plan C3).

### Q2: Apakah foto (personal) / logo (business) / foto produk membantu? → **Ya, ini kunci #1 konsistensi.**

Brand model sudah punya `type: personal/business/product` (`models.py`) tapi tidak dipakai untuk visual apa pun. Padahal:

- **Personal brand**: wajah = brand. Gambar tanpa wajah konsisten = feed terasa anonim. Reference photo → provider modern (gemini image, gpt-image-1) bisa jaga likeness.
- **Business**: logo + warna = pengenal 80% konsistensi feed. Logo overlay bahkan bisa **tanpa AI** (compositing deterministik — lihat §4.3).
- **Product**: foto produk asli >> AI-generated product (AI melenceng bentuk/label → merusak trust). Reference image produk wajib.

Keputusan "campur" (sebagian brand punya aset, sebagian tidak) → sistem **dua mode**:
1. **Anchored**: ada aset upload → jadi reference image + compositing.
2. **Synthetic**: tanpa aset → konsistensi via Visual Style Guide + prompt prefix terkunci (§4.2).

### Q3: Bagaimana jaga konsistensi media & gaya render? → **4 lapis, dari murah ke mahal:**

```
Lapis 1  Visual Style Guide per brand (teks terstruktur, dikunci)     ← grounding
Lapis 2  Prompt scaffold terpusat di kode, bukan karangan LLM bebas   ← determinisme
Lapis 3  Reference images (foto/logo/produk) ke provider yang support ← likeness
Lapis 4  Compositing deterministik (logo overlay, template, warna)    ← jaminan 100%
```

Prinsip: **jangan andalkan LLM untuk konsistensi — kunci di kode apa yang bisa dikunci.** LLM hanya isi slot kreatif (subjek, komposisi), bukan gaya.

---

## 3. Roadmap

```
Fase M (media consistency)   →   Fase R (research/Tavily)   →   Fase S (arch cleanup)
     4-6 hari                        2-3 hari                       1-2 hari
     NILAI UTAMA                     NILAI TINGGI                   HYGIENE
```

Prasyarat: Fase A improvement-plan (pipeline fix) selesai. Fase M jalan sebelum R karena konsistensi visual = keluhan yang terlihat user setiap post; trend research nilainya per-bulan.

---

## 4. Fase M — Identitas Visual & Konsistensi Media

### M1. Brand Visual Identity (fix AR-1)

**Schema** — tabel baru `brand_assets` + kolom baru di Brand:

```
brand_assets:  id, brand_id, kind, file_path, label, is_primary, created_at
   kind: face_photo | logo | logo_dark | product_photo | reference_style
Brand (kolom baru):
   visual_style: JSON {
     palette: ["#1A1A2E", "#E94560", ...],      # 2-4 hex
     style_keywords: ["minimalist", "warm natural light", "editorial"],
     image_tone: "bright|dark|muted|vibrant",
     typography_hint: "clean sans-serif",        # untuk gambar ber-teks
     avoid: ["stock-photo look", "neon"],
     render_style: "photography|flat-illustration|3d|mixed"
   }
```

**Tools baru** (`tools/brand_tools.py`):
- `upload_brand_asset(brand_id, kind, file_path, label?)` — via API upload endpoint → simpan ke `data/brand_assets/`, validasi tipe file.
- `list_brand_assets(brand_id)`
- `set_visual_style(brand_id, visual_style)` — dipanggil positioning_agent.

**Alur positioning diperluas** (`prompts.py` POSITIONING):
- Setelah positioning verbal selesai, lanjut **interview visual** sesuai `brand.type`:
  - `personal` → minta upload 1-3 foto wajah/aktivitas + preferensi gaya foto.
  - `business` → minta logo (+varian dark) + warna brand (atau ekstrak dari logo) + tone.
  - `product` → minta foto produk per produk utama + konteks penggunaan.
- Jika user tidak punya aset → tetap wajib isi `visual_style` (mode synthetic).
- `apply_positioning` diperluas simpan `visual_style`.

**API/Web**: endpoint `POST /api/brands/{id}/assets` (multipart), galeri aset di halaman Brands SPA.

**Acceptance**: brand personal dengan foto ter-upload; `visual_style` terisi; `list_brand_assets` kembalikan path valid.

### M2. Prompt Scaffold Terpusat (fix AR-2) — perubahan paling berdampak

Sekarang: content_agent mengarang prompt bebas per media item → chaos.
Target: **kode membangun prompt final; LLM hanya isi slot kreatif.**

File baru `src/headofsocial/media/prompt_builder.py`:

```
build_image_prompt(brand, channel, creative_brief) → str
  = [STYLE PREFIX dari brand.visual_style — dikunci, identik setiap post]
  + [FORMAT: aspect ratio + komposisi per channel]
  + [CREATIVE BRIEF dari LLM: subjek, adegan, mood spesifik post]
  + [NEGATIVE/avoid dari visual_style]
```

Perubahan kontrak: `media_spec` item berubah dari `prompt` (final) → `creative_brief` (hanya bagian kreatif). `media_service.generate_media` panggil `build_image_prompt` saat eksekusi. CONTENT_INSTRUCTION diubah: "tulis creative brief singkat per item (subjek/adegan/mood), JANGAN tulis gaya visual — gaya diambil dari brand".

Konsistensi carousel: semua item 1 asset share style prefix + tambahan "part N of M, same visual series" otomatis dari builder.

**Acceptance**: unit test — 2 post beda brief, prefix identik; carousel 3 item → 3 prompt dengan seri marker. Visual check: 5 gambar 1 brand terasa satu feed.

### M3. Aspect Ratio per Platform (fix AR-3)

Tambah ke `ChannelStyle` (`channels/styles.py`): `image_aspect: str`, `image_size: str`.
- Instagram: `4:5` (1080x1350) feed; carousel sama.
- Threads: `1:1` (1080x1080).
- LinkedIn: `1.91:1` (1200x627).

`media_service` pakai size dari channel post terkait (bukan global `media_image_size`; global jadi fallback). Provider yang tak support size → crop/pad deterministik via Pillow (sudah tersedia transitively; jika belum, satu dependency kecil yang justru dipakai M5 juga).

**Acceptance**: unit test — post IG → request 1080x1350; LinkedIn → 1200x627.

### M4. Reference Image Support, Provider-Agnostic (fix AR-7)

Karena keputusan provider = fleksibel, perluas Protocol dengan **capability flags**:

```
MediaProvider Protocol (media_providers.py):
  supports_video: bool
  supports_reference_images: bool          # BARU
  generate_image(prompt, *, size, reference_images: list[Path] = []) → Path
```

Perilaku per provider:
- **Mock**: terima & abaikan references (log saja).
- **LiteLLM/aimage_generation** (Imagen dll): `supports_reference_images=False` → `media_service` otomatis fallback: references dideskripsikan tekstual ke prompt ("wajah sesuai foto profil: pria 30-an, rambut pendek…" — deskripsi digenerate SEKALI saat upload aset, disimpan di `brand_assets.label`, bukan per-post).
- **Provider multimodal** (gemini image via acompletion path, gpt-image-1): kirim reference images langsung.

`media_service.generate_media` pilih references otomatis dari `brand_assets` sesuai `brand.type` (personal→face_photo primary, product→product_photo yang di-mention di brief, business→reference_style jika ada).

**Acceptance**: test — provider tanpa support → prompt mengandung deskripsi aset; provider dengan support → references diteruskan.

### M5. Compositing Deterministik (jaminan 100%, khusus business/logo)

Logo TIDAK digenerate AI (selalu rusak). Pipeline pasca-generate di `media_service`:
- Brand punya `logo` + flag `visual_style.logo_overlay: {position: "bottom-right", opacity, margin}` → Pillow paste logo ke tiap gambar final.
- Opsional nanti: color-grade tipis ke palette brand. **Mulai dari logo overlay saja** — paling tinggi nilai/effort.

**Acceptance**: test — gambar hasil punya logo di posisi benar; brand tanpa logo → no-op.

### Yang sengaja TIDAK dipakai untuk konsistensi (YAGNI)
| Teknik | Alasan skip |
|---|---|
| Seed pinning | Tidak portable antar provider; banyak API tidak expose seed |
| Fine-tune/LoRA per brand | Mahal, lambat, overkill sebelum ada volume |
| IP-Adapter/ComfyUI self-host | Ops berat; reference-image API provider sudah cukup |
| Embedding similarity check pasca-generate | Tambah biaya per gambar; review manusia (revision loop B2) sudah menangkap outlier |

---

## 5. Fase R — Web Research (Tavily)

### R1. Research tool layer
- Dependency: `tavily-python` (atau HTTP langsung — client resmi tipis, pakai saja).
- Config: `HEADSOF_TAVILY_API_KEY`, `HEADSOF_RESEARCH_PROVIDER=tavily|none` (none = tools report "tidak tersedia", agent lanjut tanpa riset — graceful).
- File `tools/research_tools.py`:
  - `search_web(query, max_results=5)` — generik, return title+url+snippet.
  - `research_trends(brand_id, focus?)` — compose query dari brand.industry + pillars + focus; return ringkasan topik hangat + sumber.
  - `research_competitors(brand_id, competitor_names?)` — query positioning/konten kompetitor; return ringkasan per kompetitor.
- Cache hasil di tabel `research_notes` (brand_id, kind, query, results JSON, created_at) — planning bulanan tidak perlu query ulang; TTL 7 hari.

### R2. Wiring ke agents
- **positioning_agent**: instruksi + `research_competitors` — saat user sebut kompetitor atau industri, riset dulu sebelum rumuskan differentiators. Hasil riset dikutip dengan sumber.
- **planning_agent**: tambah `research_trends` ke daftar tools WAJIB (jadi 6) saat buat plan bulanan — weekly_themes harus sebut minimal 1 hook topikal bila ada temuan relevan.
- **content_agent**: opsional `search_web` untuk fact-check angka/klaim dalam konten (hindari halusinasi statistik di post).

### R3. Guardrails
- Budget: max 10 query per plan-run (hard count di service, pola sama dengan media budget).
- Semua klaim hasil riset di konten wajib bawa sumber di draft (dihapus saat publish final — untuk review manusia).

**Acceptance**: plan bulanan brand dengan industry terisi → weekly theme mengandung referensi trend + research_notes terisi; tanpa API key → plan tetap jadi tanpa error.

---

## 6. Fase S — Architecture Hygiene

| ID | Aksi | Fix |
|---|---|---|
| S1 | Wire `positioning_formatter`: positioning_agent panggil formatter (via AgentTool atau langsung `output_schema` di flow) sebelum `apply_positioning` → data tervalidasi Pydantic | AR-5 |
| S2 | `_VIDEO_OK` → evaluasi runtime: ubah CONTENT_INSTRUCTION jadi fungsi `content_instruction()` dipanggil saat buat agent / pakai ADK `instruction` callable | AR-6 |
| S3 | Active brand di `session.state`: root set `state["active_brand_id"]` saat user pilih brand → sub-agents baca dari state via instruction templating ADK (`{active_brand_id}`), hemat 1 tool-call/turn dan hilangkan ambiguitas multi-brand | AR-8 |
| S4 | Observability: aktifkan Cloud Trace / logging per agent-transfer + tool-call latency (plugin `AgentTracePlugin` sudah ada — perluas) | — |

---

## 7. Urutan & Dependensi

```
(Prasyarat: improvement-plan Fase A selesai)

M1 (brand assets + visual_style)
 └─► M2 (prompt builder)  ─► M4 (reference images)
          └─► M3 (aspect ratio — paralel ok)
                   M5 (logo overlay — butuh M1 saja)

R1 ─► R2 ─► R3   (independen dari M; bisa paralel setelah M1)

S1-S4 kapan saja, prioritas S3 sebelum R2 (state brand aktif dipakai research tools)
```

## 8. Definisi Selesai

- **Fase M**: 1 brand personal (dengan foto) + 1 brand business (dengan logo) + 1 brand tanpa aset → masing-masing generate 5 post; feed per brand terlihat satu gaya; logo selalu muncul benar; IG 4:5, LinkedIn 1.91:1. Mode anchored & synthetic dua-duanya jalan.
- **Fase R**: plan bulanan mengutip trend nyata dengan sumber; positioning menyebut temuan kompetitor; tanpa API key semua tetap jalan graceful.
- **Fase S**: positioning tervalidasi schema; video note akurat runtime; brand aktif di session state; trace per transfer terlihat.

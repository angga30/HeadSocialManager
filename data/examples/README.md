# Contoh Data

Folder ini berisi contoh nyata dari *output* dan *input* sistem, supaya Anda bisa langsung
melihat bentuk data yang dihasilkan **Head of Social Media Agent** tanpa harus menjalankan
seluruh alur.

## Daftar Contoh

| File | Menjelaskan |
| --- | --- |
| `../docs/company-profile.md` | Contoh dokumen yang dibaca **Positioning Agent** (via `list_documents` / `read_document`). |
| `positioning.json` | Contoh rekomendasi positioning — sesuai skema `PositioningRecommendation` (termasuk `visual_style`). |
| `monthly-plan.json` | Contoh rencana bulanan — sesuai skema `MonthlyPlan` (theme, weekly_themes, cadence, content_mix, key_dates). |
| `captions/instagram.md` | Caption native Instagram untuk pillar "Edukasi Seduh". |
| `captions/threads.md` | Caption native Threads untuk pillar yang sama. |
| `captions/linkedin.md` | Caption native LinkedIn untuk pillar yang sama. |

## Tentang Caption Native

Untuk **satu pillar yang sama**, sistem menulis copy berbeda sesuai gaya tiap platform
(lihat `src/headofsocial/channels/styles.py`):

- **Instagram** — visual-first, energik, emoji moderat, 1–5 hashtag, ditutup CTA.
- **Threads** — conversational, candid, emoji ringan, minim hashtag, mengundang balasan.
- **LinkedIn** — profesional, thought-leadership, paragraf pendek, 0–3 hashtag, ditutup pertanyaan.

## Cara Pakai

Contoh `positioning.json` dan `monthly-plan.json` adalah representasi skema data (bukan
langsung diimpor ke database). Untuk melihat alur penuh, jalankan aplikasi dan minta agent:

- *"Baca dokumen `company-profile.md` lalu buat positioning untuk brand saya."*
- *"Buat rencana konten bulan ini."*
- *"Tulis caption Instagram untuk pillar Edukasi Seduh."*

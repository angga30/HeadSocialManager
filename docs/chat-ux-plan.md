# Chat UX Plan — Paritas dengan Chat Agent Standar

> Status: DRAFT · Tanggal: 2026-10-01
> Tujuan: chat page (web `/app` Composer) setara fitur umum ChatGPT/Claude/Gemini.
> Prinsip: transparansi proses dulu (user harus lihat agent "hidup"), baru kontrol (stop/retry/edit), baru polish.

---

## 1. Kondisi Sekarang

### Arsitektur chat
- Server: `POST /api/chat/conversations/{id}/stream` SSE (`api/routes/chat.py:71-94`) — 3 event: `start`, `token`, `done`.
- Service: `chat_service.py` — ADK Runner + `DatabaseSessionService`; `_agent_reply` (L71-79) hanya yield `event.is_final_response()` text.
- Web: React SPA `web/` — `Composer.tsx`, `MentionInput.tsx`, `conversationsStore.ts` (AbortController stop), markdown render.
- TUI: `screens/composer.py` — blocking `ask()`, tanpa streaming/history/indicator.

### Yang sudah ada ✅
| Fitur | Lokasi |
|---|---|
| Conversation list + create/delete | `chat.py:31-52`, store |
| History persist + load | `conversation_service`, `api.ts getMessages` |
| Markdown render | `components/Markdown.tsx` |
| Mentions (@brand/@channel/@post) | `MentionInput.tsx`, `chat.py:64-68` |
| Stop (client-side saja) | `conversationsStore.ts:97-105` |
| Error → teks manusiawi (ID) | `chat_service.py:32-47` |
| Status conversation (idle/processing/error) | `chat_service.py:100-134` |

---

## 2. Benchmark — Fitur Umum Chat Agent

Standar pasar (ChatGPT, Claude, Gemini, Perplexity):

| # | Fitur | Standar pasar | Kita | Gap |
|---|---|---|---|---|
| F1 | Streaming token real-time | Teks muncul kata-per-kata | ❌ 1 chunk besar per agent turn | **KRITIS** |
| F2 | Thinking/status indicator | "Thinking…", spinner, status berubah | ❌ Tidak ada; layar diam bisa 30-60s (multi-agent) | **KRITIS** |
| F3 | Tool-call transparency | "Searching web…", collapsible step | ❌ function_call/response dibuang (`chat_service.py:71-79`) | **KRITIS** |
| F4 | Agent transfer visibility | — (khas multi-agent; Claude projects, GPTs show) | ❌ Transfer root→planning→content invisible | TINGGI |
| F5 | Bubble styling | User kanan/warna accent, agent kiri, avatar, timestamp | ⚠️ Cek `Composer.tsx` — minimal | SEDANG |
| F6 | Stop generation (server) | Stop benar-benar hentikan run | ⚠️ Client abort saja; server run lanjut | TINGGI |
| F7 | Regenerate/retry | Tombol retry di pesan terakhir/error | ❌ | TINGGI |
| F8 | Copy message | Hover → copy button; copy per code block | ❌ | SEDANG |
| F9 | Edit user message + resend | Edit → fork/resend | ❌ | RENDAH |
| F10 | Auto-title conversation | Judul dari pesan pertama (LLM/truncate) | ❌ (cek: title manual?) | SEDANG |
| F11 | Suggested prompts | Chip saran saat conversation kosong | ❌ | RENDAH |
| F12 | Feedback 👍👎 | Per pesan assistant | ❌ | RENDAH |
| F13 | Attachment/upload | File/gambar ke chat | ❌ (dokumen via `data/docs` saja) | RENDAH* |
| F14 | Auto-scroll + scroll-to-bottom button | Ikut stream; tombol muncul saat scroll up | ⚠️ Cek implementasi | SEDANG |
| F15 | Error state + inline retry | Banner error + tombol coba lagi | ⚠️ Error jadi teks biasa, tanpa retry | SEDANG |
| F16 | Markdown penuh: code block + copy, tabel | Syntax highlight, copy code | ⚠️ Markdown ada; highlight/copy-code belum | SEDANG |

\* F13 rendah karena use case kita: dokumen brand masuk via `document_tools`; upload chat belum perlu (YAGNI).

### Diagnosis akar
Satu akar untuk F1-F4: **`_agent_reply` membuang 90% event ADK**. ADK Runner sudah emit partial text, function_call, function_response, transfer — tinggal diteruskan. Ini bukan fitur baru, ini membuka keran yang sudah ada.

---

## 3. Roadmap

```
Fase CH-A (keran event + streaming)  →  Fase CH-B (kontrol)  →  Fase CH-C (polish)
      2-3 hari                             2 hari                  1-2 hari
      KRITIS                               TINGGI                  SEDANG
```

---

## 4. Fase CH-A — Transparansi Proses (F1-F4)

### CH-A1. Perluas protokol SSE
File: `api/routes/chat.py`, `services/chat_service.py`.

Event baru (tambahan, backward-compatible):
```
event: token      data: {"text": "..."}                      # partial, kata-per-kata
event: status     data: {"state": "thinking"|"idle"}         # model mulai/selesai mikir
event: agent      data: {"name": "planning_agent"}           # transfer antar agent
event: tool       data: {"name": "get_brand", "status": "start"|"done", "summary": "..."}
event: error      data: {"message": "...", "retryable": true}
event: done       data: {"message_id": "..."}
```

`chat_service.stream()` ubah `_agent_reply` → `_agent_events`:
- `event.partial` + text → `token` (aktifkan `RunConfig(streaming_mode=SSE)` di Runner).
- `part.function_call` → `tool start` (name + ringkasan args).
- `part.function_response` → `tool done`.
- Event `transfer_to_agent` / author berubah → `agent`.
- Exception → `error` event (bukan token teks); simpan teks error ke DB tetap.

**Acceptance**: curl SSE → terlihat urutan `agent → tool → token(banyak) → done` untuk prompt "buatkan plan bulan ini".

### CH-A2. Web: render streaming + indicator
File: `web/src/pages/Composer.tsx`, `conversationsStore.ts`.
- Parse event baru; append token ke pesan assistant aktif (bukan tunggu done).
- Indicator baris status di bawah pesan terakhir: `🤖 planning_agent · menjalankan get_engagement_insights…` → hilang saat token pertama datang.
- Tool steps: collapsible list kecil di atas jawaban (ala Perplexity "steps"), default collapsed.
- **Acceptance**: visual — teks mengalir, status tool terlihat, tidak ada layar diam >2s.

### CH-A3. TUI: minimal paritas
File: `tui/screens/composer.py`.
- Ganti `ask()` → consume stream; update `Markdown` widget per chunk (atau per 100ms throttle).
- `LoadingIndicator` Textual saat status thinking/tool.
- Load history saat mount (endpoint sudah ada).
- **Acceptance**: TUI tampil streaming + indicator; history muncul saat buka.

---

## 5. Fase CH-B — Kontrol (F6, F7, F15, F10)

### CH-B1. Stop server-side (F6)
File: `chat_service.py`, `chat.py`.
- Registry `asyncio.Task` per conversation_id. `POST /conversations/{id}/stop` → cancel task; status → `idle`; partial reply tersimpan dengan tanda `(dihentikan)`.
- Route stream: deteksi disconnect → cancel task juga (sekarang cuma break loop).
- **Acceptance**: stop → server berhenti <1s (log tool berhenti), status idle, partial tersimpan.

### CH-B2. Retry/regenerate (F7, F15)
- Server: `POST /conversations/{id}/retry` — hapus pesan assistant terakhir, re-run pesan user terakhir (pakai session ADK yang sama; hapus event terakhir dari session atau kirim ulang user message).
- Web: tombol ↻ di pesan assistant terakhir + di error banner. Event `error` (CH-A1) render sebagai banner dengan tombol retry, bukan teks biasa.
- **Acceptance**: error API key → banner + retry; retry sukses ganti pesan.

### CH-B3. Auto-title (F10)
- Saat pesan pertama conversation selesai: title = 40 char pertama pesan user (truncate pintar di batas kata). LLM-title = YAGNI.
- **Acceptance**: conversation baru → sidebar title bukan "New conversation".

---

## 6. Fase CH-C — Polish (F5, F8, F14, F16, F11)

### CH-C1. Bubble & layout (F5)
- User: kanan, background accent, max-width 75%. Agent: kiri, tanpa background/subtle, full width konten.
- Timestamp hover, nama agent kecil di atas bubble agent (sudah ada data dari event `agent`).
- Avatar: emoji/inisial cukup. Gambar = YAGNI.

### CH-C2. Copy + code block (F8, F16)
- Hover pesan → tombol copy (markdown mentah).
- `Markdown.tsx`: syntax highlight (`react-syntax-highlighter` atau `shiki` — pilih yang sudah/paling ringan) + tombol copy per code block.

### CH-C3. Auto-scroll (F14)
- Auto-scroll saat stream HANYA jika user sudah di bawah; tombol ↓ float saat scroll up (standar semua chat app).

### CH-C4. Suggested prompts (F11)
- Conversation kosong → 3-4 chip statis sesuai use case: "Buat positioning brand saya", "Susun plan konten bulan ini", "Lihat performa minggu lalu", "Buat konten untuk slot berikutnya". Hardcode dulu; dinamis = YAGNI.

---

## 7. Tidak Dikerjakan (YAGNI)

| Fitur | Alasan |
|---|---|
| F9 Edit message + fork | Kompleks (fork session ADK); retry cukup dulu |
| F12 Feedback 👍👎 | Belum ada pipeline pakai datanya |
| F13 Upload file di chat | Dokumen brand sudah via `data/docs`; tambah saat ada permintaan nyata |
| Voice input/output | Di luar scope |
| Share conversation link | Single user |
| LLM auto-title | Truncate cukup |

---

## 8. Dependensi & Urutan

```
CH-A1 (protokol SSE) ──► CH-A2 (web render) ──► CH-B2 (retry UI butuh event error)
        │                       │
        └──► CH-A3 (TUI)        └──► CH-C1..C4 (polish, paralel)
CH-B1 (stop server) — independen, bisa paralel dengan CH-A2
CH-B3 (auto-title) — independen, kapan saja
```

## 9. Definisi Selesai

- **CH-A**: kirim prompt kompleks (plan bulanan) → user lihat: nama agent aktif, tool yang jalan, teks mengalir real-time. Tidak ada layar diam >2 detik. Web + TUI.
- **CH-B**: stop benar-benar hentikan server; error tampil sebagai banner retry-able; conversation punya judul otomatis.
- **CH-C**: bubble jelas user vs agent, copy pesan & code, auto-scroll benar, suggested prompts di conversation kosong.

# Design Standard — Head of Social Web

Stack: **React 18 + Vite + TypeScript + Tailwind v4** (plugin `@tailwindcss/vite`), **Phosphor Icons**, **Geist / Geist Mono** (self-host via `@fontsource-variable`). Dark theme only, locked.

## Tokens (`src/index.css` → `@theme`)

| Token | Value | Pakai untuk |
|---|---|---|
| `bg` | `#0f1115` | Background halaman |
| `panel` | `#171a21` | Card, sidebar |
| `panel2` | `#1e222b` | Input, hover, bubble assistant |
| `line` | `#2a2f3a` | Semua border |
| `ink` | `#e6e8ee` | Teks utama |
| `mute` | `#9aa3b2` | Teks sekunder, label |
| `accent` | `#6ea8fe` | Aksi primer, link, aktif |
| `accent-ink` | `#0b1220` | Teks di atas accent |
| `ok` | `#7ee0a0` | Sukses, status published/idle |
| `warn` | `#e0b070` | Mention post, peringatan |
| `danger` | `#ff6b6b` | Error, status failed |

**Satu accent per app.** Warna baru? Tambah token di `@theme`, jangan hard-code hex di komponen.

## Aturan Wajib

1. **Spacing = skala Tailwind 4px.** Dilarang nilai arbitrary (`p-[9px]`, `gap-[13px]`).
2. **Radius lock:** `rounded-sm` (input kecil, thumb), `rounded-md` (button, input), `rounded-lg` (card, bubble), `rounded-full` (badge, chip). Tidak ada radius lain.
3. **Ikon = Phosphor saja** (`@phosphor-icons/react`, weight `duotone` nav / `bold` glyph kecil, size 12–17). **Dilarang emoji di UI.** Satu keluarga ikon per project.
4. **Status message pakai `<StatusMsg kind="ok"|"err">`** — state `{kind, text}`, bukan prefix emoji + `startsWith()`.
5. **Tidak ada inline `style={{}}`** kecuali nilai dinamis dari data (contoh: swatch warna dari API).
6. **Komponen UI owned di `src/components/ui/`** (Button, Card, Field, Badge class). Pakai class komponen: `.btn-primary`, `.btn-ghost`, `.btn-icon`, `.input`, `.card`, `.badge-*`, `.th`, `.td`. Jangan tulis ulang utility yang sama berulang.
7. **Kontras WCAG AA** — cek teks di atas background sebelum ship. Placeholder `mute/70` sudah aman.
8. **Interaksi:** semua button punya `active:translate-y-px` (sudah di `.btn*`), hover `transition-colors`, focus ring global via `:focus-visible`.
9. **Layout:** grid dengan `gap`, bukan margin-bottom acak. Halaman: `PageHeader` → toolbar → cards `gap-4`. Grid 2 kolom: `grid-cols-1 lg:grid-cols-[340px_1fr]`.
10. **Tabel:** `<table className="w-full text-sm">` + `.th`/`.td`, row hover `hover:bg-panel2/60`, angka `tabular-nums`.

## Anti-Slop Checklist (sebelum ship)

- [ ] Nol emoji di UI (cari regex emoji)
- [ ] Nol hex hard-code di TSX
- [ ] Nol inline style statis
- [ ] Semua status ada icon + warna token
- [ ] Empty state ada teks jelas, bukan kosong
- [ ] Font tetap Geist; jangan ganti tanpa update token `--font-sans`
- [ ] Dark-only — jangan campur section terang

## Menambah Halaman Baru

Salin pola `Channels.tsx`: `PageHeader` → `BrandPicker` toolbar → `Card` form → `Card` tabel. State msg pakai `useState<Msg | null>` + `StatusMsg`.

## Menambah Komponen UI

Taruh di `src/components/ui/`, terima `className` terakhir (merge via `cn()` dari `src/lib/cn.ts`), forward `ref`, tanpa dependency baru untuk hal yang bisa CSS.

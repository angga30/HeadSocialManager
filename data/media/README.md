# Media — Struktur & Konvensi

Folder ini adalah tempat **media hasil generate** disimpan. Secara default (`HEADSOF_MEDIA_PROVIDER=mock`),
file yang dihasilkan adalah placeholder tanpa jaringan; saat memakai provider nyata
(`litellm`, mis. `gemini/imagen-3.0-generate-002`), file di sini adalah gambar/video asli.

> Media hasil generate **tidak** di-commit ke repo (dikecualikan `.gitignore`). Folder ini
> hanya berisi README sebagai dokumentasi struktur.

## Konvensi Nama

Media dinamai oleh provider dengan pola `<jenis>_<uuid>.<ext>`, misalnya:

```
img_18e063adbd0e4c7ba67bb76173c8d862.png   # hasil generate gambar
```

Path media disimpan pada `assets.media_files` dan disajikan FastAPI di `/media/`.

## Bagaimana Media Dihasilkan

1. **Content Agent** menulis *creative brief* singkat per item (subjek/adegan/mood) — bukan gaya visual.
2. **Media Generation Agent** memanggil `generate_media_item` untuk tiap item secara paralel.
3. Gaya visual diambil dari `brand.visual_style` (terkunci), sehingga setiap post konsisten.

Contoh *creative brief* untuk carousel "Edukasi Seduh":

```json
[
  { "media_type": "image", "creative_brief": "Tangan menuang air panas dari gooseneck kettle ke V60, close-up, uap tipis, cahaya pagi dari jendela.", "position": 0 },
  { "media_type": "image", "creative_brief": "Kopi sedang bloom, permukaan bergelembung halus, shot datar dari atas.", "position": 1 },
  { "media_type": "image", "creative_brief": "Cangkir kopi jadi di atas meja kayu, disamping timbangan dan biji kopi.", "position": 2 }
]
```

## Budget Media

Budget ditegakkan keras (lihat `config.py`): **maksimal 5 gambar dan 2 video per asset**.
Spec yang melebihi batas ditolak dengan pesan jelas.

Lihat juga `src/headofsocial/media/prompt_builder.py` untuk cara prompt dirakit dari
`visual_style` + format channel + *creative brief*.

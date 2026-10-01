import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, UploadSimple } from "@phosphor-icons/react";
import { api, type Brand, type BrandAsset, type Channel } from "../lib/api";
import Button from "../components/ui/Button";
import Card, { CardTitle } from "../components/ui/Card";
import { Input, Select } from "../components/ui/Field";
import StatusMsg, { type MsgKind } from "../components/StatusMsg";

const KINDS = ["face_photo", "logo", "logo_dark", "product_photo", "reference_style"];

interface Msg {
  kind: MsgKind;
  text: string;
}

function Field({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-mute">{label}</div>
      <p className="mt-0.5 text-sm">{value}</p>
    </div>
  );
}

export default function BrandDetail() {
  const { id } = useParams();
  const brandId = Number(id);

  const [brand, setBrand] = useState<Brand | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [assets, setAssets] = useState<BrandAsset[]>([]);
  const [msg, setMsg] = useState<Msg | null>(null);
  const [busy, setBusy] = useState(false);

  const [kind, setKind] = useState<string>("face_photo");
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (!Number.isFinite(brandId)) return;
    (async () => {
      try {
        const [b, ch, as] = await Promise.all([
          api.getBrand(brandId),
          api.listChannels(brandId),
          api.listBrandAssets(brandId),
        ]);
        setBrand(b);
        setChannels(ch);
        setAssets(as);
      } catch (e) {
        setMsg({ kind: "err", text: String(e) });
      }
    })();
  }, [brandId]);

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setMsg(null);
    try {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", file);
      if (label) form.append("label", label);
      await api.uploadBrandAsset(brandId, form);
      setAssets(await api.listBrandAssets(brandId));
      setFile(null);
      setLabel("");
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
    } finally {
      setBusy(false);
    }
  };

  if (msg?.kind === "err" && !brand) {
    return (
      <div>
        <StatusMsg kind="err">{msg.text}</StatusMsg>
      </div>
    );
  }

  return (
    <div>
      <Link
        to="/brands"
        className="mb-3 inline-flex items-center gap-1.5 text-[13px] text-mute transition-colors hover:text-accent"
      >
        <ArrowLeft size={13} /> Semua brand
      </Link>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold tracking-tight">{brand?.name ?? "…"}</h2>
        {brand && (
          <>
            <span className="badge">{brand.type}</span>
            <span className="badge">{brand.language}</span>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[340px_1fr]">
        <div className="flex flex-col gap-4">
          <Card>
            <CardTitle>Profil</CardTitle>
            <div className="flex flex-col gap-3">
              <Field label="Deskripsi" value={brand?.description ?? null} />
              <Field label="Positioning" value={brand?.positioning_statement ?? null} />
              <Field label="Voice & tone" value={brand?.voice_tone ?? null} />
              {(!brand?.description && !brand?.positioning_statement && !brand?.voice_tone) && (
                <p className="text-[13px] text-mute">
                  Profil masih kosong. Lengkapi lewat chat di Composer, mis. “Buat positioning brand
                  @brand:{brandId}”.
                </p>
              )}
            </div>
          </Card>

          {brand && brand.content_pillars.length > 0 && (
            <Card>
              <CardTitle>Content pillars</CardTitle>
              <ul className="flex flex-col gap-2">
                {brand.content_pillars.map((p, i) => (
                  <li key={i} className="text-sm">
                    <span className="font-medium">{p.name ?? `Pillar ${i + 1}`}</span>
                    {p.angle && <span className="text-mute"> — {p.angle}</span>}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {brand?.visual_style && (
            <Card>
              <CardTitle>Visual style</CardTitle>
              <div className="flex flex-wrap gap-1.5">
                {brand.visual_style.palette.map((c) => (
                  <span
                    key={c}
                    title={c}
                    className="h-5 w-5 rounded-sm border border-line"
                    style={{ background: c }}
                  />
                ))}
              </div>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <span className="badge">{brand.visual_style.render_style || "no render style"}</span>
                {brand.visual_style.style_keywords.slice(0, 6).map((k) => (
                  <span key={k} className="badge">
                    {k}
                  </span>
                ))}
              </div>
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <Card>
            <CardTitle>Channels ({channels.length})</CardTitle>
            {channels.length > 0 ? (
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="th">Platform</th>
                    <th className="th">Handle</th>
                    <th className="th">Bahasa</th>
                  </tr>
                </thead>
                <tbody>
                  {channels.map((c) => (
                    <tr key={c.id} className="hover:bg-panel2/60">
                      <td className="td">
                        <span className="badge">{c.platform}</span>
                      </td>
                      <td className="td">{c.handle}</td>
                      <td className="td">{c.language ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-[13px] text-mute">
                Belum ada channel. Sambungkan di halaman Channels.
              </p>
            )}
          </Card>

          <Card>
            <CardTitle>Aset visual ({assets.length})</CardTitle>
            <div className="mb-4 flex flex-wrap items-center gap-2.5">
              <Select value={kind} onChange={(e) => setKind(e.target.value)}>
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </Select>
              <Input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-auto"
              />
              <Input
                placeholder="Label / deskripsi"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="w-auto"
              />
              <Button onClick={upload} disabled={busy || !file}>
                <UploadSimple size={15} weight="bold" /> Upload
              </Button>
            </div>
            <div className="flex flex-wrap items-start gap-3">
              {assets.map((a) => (
                <div key={a.id} className="text-center">
                  <img
                    src={a.url}
                    alt={a.kind}
                    className="h-[84px] w-[84px] rounded-md border border-line object-cover"
                  />
                  <div className="mt-1 text-[11px] text-mute">{a.kind}</div>
                </div>
              ))}
              {assets.length === 0 && (
                <span className="text-[13px] text-mute">
                  Belum ada aset. Foto wajah / logo / produk dipakai untuk konsistensi visual saat
                  generate konten.
                </span>
              )}
            </div>
          </Card>
        </div>
      </div>

      {msg && <StatusMsg kind={msg.kind} className="mt-4">{msg.text}</StatusMsg>}
    </div>
  );
}

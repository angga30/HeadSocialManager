import { useEffect, useState } from "react";
import { api, type Asset } from "../lib/api";
import { useBrands } from "../lib/useBrands";
import BrandPicker from "../components/BrandPicker";
import Button from "../components/ui/Button";
import Card, { CardTitle } from "../components/ui/Card";
import { Input, Select, Textarea } from "../components/ui/Field";
import PageHeader from "../components/PageHeader";
import MediaThumb from "../components/MediaThumb";
import StatusMsg, { type MsgKind } from "../components/StatusMsg";

const DEPTHS = ["text", "visual", "carousel", "motion", "series", "rich"];

interface Msg {
  kind: MsgKind;
  text: string;
}

export default function Studio() {
  const { brands, selectedId, select } = useBrands();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [copy, setCopy] = useState("");
  const [depth, setDepth] = useState("visual");
  const [prompt, setPrompt] = useState("");
  const [imageCount, setImageCount] = useState(1);
  const [msg, setMsg] = useState<Msg | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async (brandId: number) => {
    try {
      setAssets(await api.listAssets(brandId));
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
    }
  };

  useEffect(() => {
    if (selectedId != null) void load(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const createAndGenerate = async () => {
    if (selectedId == null) return;
    setBusy(true);
    setMsg(null);
    try {
      const media_spec =
        imageCount > 0
          ? Array.from({ length: imageCount }, (_, i) => ({
              media_type: "image",
              creative_brief: prompt || copy || "social media visual",
              position: i,
            }))
          : [];
      const asset = await api.createAsset({ brand_id: selectedId, body: copy, depth, media_spec });
      if (media_spec.length) {
        const res = await api.generateAsset(asset.id);
        setMsg({ kind: "ok", text: `Asset #${asset.id} dibuat, ${res.media.length} gambar digenerate.` });
      } else {
        setMsg({ kind: "ok", text: `Asset #${asset.id} dibuat (teks).` });
      }
      setCopy("");
      setPrompt("");
      await load(selectedId);
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader>Content Studio — image generation</PageHeader>
      <div className="mb-4">
        <BrandPicker brands={brands} selectedId={selectedId} onSelect={select} />
      </div>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[340px_1fr]">
        <Card>
          <CardTitle>Buat konten</CardTitle>
          <div className="flex flex-col gap-2.5">
            <div>
              <label htmlFor="copy" className="mb-1 block text-[13px] text-mute">
                Caption / copy
              </label>
              <Textarea id="copy" rows={3} value={copy} onChange={(e) => setCopy(e.target.value)} />
            </div>
            <div>
              <label htmlFor="depth" className="mb-1 block text-[13px] text-mute">
                Format
              </label>
              <Select
                id="depth"
                className="w-full"
                value={depth}
                onChange={(e) => setDepth(e.target.value)}
              >
                {DEPTHS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label htmlFor="brief" className="mb-1 block text-[13px] text-mute">
                Creative brief
              </label>
              <Input
                id="brief"
                placeholder="Subjek / adegan"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="count" className="mb-1 block text-[13px] text-mute">
                Jumlah gambar (maks 5)
              </label>
              <Input
                id="count"
                type="number"
                min={0}
                max={5}
                value={imageCount}
                onChange={(e) => setImageCount(Math.max(0, Math.min(5, Number(e.target.value))))}
                className="w-20"
              />
            </div>
            <Button onClick={createAndGenerate} disabled={busy || selectedId == null}>
              Buat + generate gambar
            </Button>
            {msg && <StatusMsg kind={msg.kind}>{msg.text}</StatusMsg>}
            <p className="text-[13px] text-mute">
              Catatan: hasil nyata butuh <code className="font-mono text-xs">HEADSOF_MEDIA_PROVIDER=litellm</code>{" "}
              + API key. Default mock menghasilkan file placeholder.
            </p>
          </div>
        </Card>

        <Card>
          <CardTitle>Assets ({assets.length})</CardTitle>
          <div className="divide-y divide-line">
            {assets.map((a) => (
              <div key={a.id} className="py-2.5 first:pt-0">
                <div className="flex items-center gap-2">
                  <span className="badge">{a.depth ?? a.type}</span>
                  <span className="text-[13px] text-mute">#{a.id}</span>
                </div>
                {a.body && <p className="my-1.5 text-sm">{a.body}</p>}
                <div className="flex flex-wrap gap-2">
                  {a.media.map((m) => (
                    <MediaThumb key={m.filename} media={m} />
                  ))}
                  {a.media.length === 0 && <span className="text-[13px] text-mute">tidak ada media</span>}
                </div>
              </div>
            ))}
          </div>
          {assets.length === 0 && <p className="text-[13px] text-mute">Belum ada asset.</p>}
        </Card>
      </div>
    </div>
  );
}

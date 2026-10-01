import { useEffect, useState } from "react";
import { api, type Asset } from "../lib/api";
import { useBrands } from "../lib/useBrands";

const DEPTHS = ["text", "visual", "carousel", "motion", "series", "rich"];

export default function Studio() {
  const { brands, selectedId, select } = useBrands();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [copy, setCopy] = useState("");
  const [depth, setDepth] = useState("visual");
  const [prompt, setPrompt] = useState("");
  const [imageCount, setImageCount] = useState(1);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async (brandId: number) => {
    try {
      setAssets(await api.listAssets(brandId));
    } catch (e) {
      setMsg(`⚠️ ${e}`);
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
              prompt: prompt || copy || "social media visual",
              position: i,
            }))
          : [];
      const asset = await api.createAsset({ brand_id: selectedId, body: copy, depth, media_spec });
      if (media_spec.length) {
        const res = await api.generateAsset(asset.id);
        setMsg(`✅ Asset #${asset.id} dibuat, ${res.media.length} gambar digenerate.`);
      } else {
        setMsg(`✅ Asset #${asset.id} dibuat (teks).`);
      }
      setCopy("");
      setPrompt("");
      await load(selectedId);
    } catch (e) {
      setMsg(`⚠️ ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">Content Studio — image generation</h2>
      <div className="row" style={{ marginBottom: 14 }}>
        <span className="muted">Brand:</span>
        <select value={selectedId ?? ""} onChange={(e) => select(Number(e.target.value))}>
          {brands.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3>Buat konten</h3>
          <div className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
            <textarea
              placeholder="Caption / copy"
              rows={3}
              value={copy}
              onChange={(e) => setCopy(e.target.value)}
              style={{ background: "var(--panel-2)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 8, padding: 9 }}
            />
            <select value={depth} onChange={(e) => setDepth(e.target.value)}>
              {DEPTHS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <input placeholder="Prompt gambar" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
            <label className="muted">
              Jumlah gambar (maks 5):{" "}
              <input
                type="number"
                min={0}
                max={5}
                value={imageCount}
                onChange={(e) => setImageCount(Math.max(0, Math.min(5, Number(e.target.value))))}
                style={{ width: 70 }}
              />
            </label>
            <button className="primary" onClick={createAndGenerate} disabled={busy || selectedId == null}>
              Buat + generate gambar
            </button>
            {msg && <div className={`msg ${msg.startsWith("⚠️") ? "err" : "ok"}`}>{msg}</div>}
            <p className="muted">
              Catatan: hasil nyata butuh <code>HEADSOF_MEDIA_PROVIDER=litellm</code> + API key. Default
              mock menghasilkan file placeholder.
            </p>
          </div>
        </div>

        <div className="card">
          <h3>Assets ({assets.length})</h3>
          {assets.map((a) => (
            <div key={a.id} style={{ borderTop: "1px solid var(--border)", padding: "10px 0" }}>
              <div className="row">
                <span className="badge">{a.depth ?? a.type}</span>
                <span className="muted">#{a.id}</span>
              </div>
              {a.body && <p style={{ margin: "6px 0" }}>{a.body}</p>}
              <div className="row">
                {a.media.map((m) => (
                  <img
                    key={m.filename}
                    src={m.url}
                    alt={m.filename}
                    style={{ width: 96, height: 96, objectFit: "cover", borderRadius: 8, border: "1px solid var(--border)" }}
                  />
                ))}
                {a.media.length === 0 && <span className="muted">tidak ada media</span>}
              </div>
            </div>
          ))}
          {assets.length === 0 && <p className="muted">Belum ada asset.</p>}
        </div>
      </div>
    </div>
  );
}
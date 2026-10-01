import { useState } from "react";
import { api } from "../lib/api";
import { useBrands } from "../lib/useBrands";

export default function Brands() {
  const { brands, selectedId, select, reload, error } = useBrands();
  const [name, setName] = useState("");
  const [type, setType] = useState("business");
  const [description, setDescription] = useState("");
  const [language, setLanguage] = useState("id");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setMsg(null);
    try {
      const b = await api.createBrand({ name, type_: type, description, language });
      setMsg(`✅ Brand "${b.name}" dibuat.`);
      setName("");
      await reload();
      select(b.id);
    } catch (e) {
      setMsg(`⚠️ ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">Brands</h2>
      {error && <div className="msg err">{error}</div>}
      <div className="grid-2">
        <div className="card">
          <h3>Buat brand</h3>
          <div className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
            <input placeholder="Nama brand" value={name} onChange={(e) => setName(e.target.value)} />
            <input placeholder="Deskripsi singkat" value={description} onChange={(e) => setDescription(e.target.value)} />
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="personal">personal</option>
              <option value="business">business</option>
              <option value="product">product</option>
            </select>
            <input placeholder="Bahasa (id/en)" value={language} onChange={(e) => setLanguage(e.target.value)} />
            <button className="primary" onClick={create} disabled={busy}>
              Simpan brand
            </button>
            {msg && <div className={`msg ${msg.startsWith("⚠️") ? "err" : "ok"}`}>{msg}</div>}
          </div>
        </div>

        <div className="card">
          <h3>Brand terdaftar</h3>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nama</th>
                <th>Tipe</th>
                <th>Lang</th>
                <th>Positioning</th>
              </tr>
            </thead>
            <tbody>
              {brands.map((b) => (
                <tr
                  key={b.id}
                  onClick={() => select(b.id)}
                  style={{ cursor: "pointer", background: b.id === selectedId ? "var(--panel-2)" : undefined }}
                >
                  <td>{b.id}</td>
                  <td>{b.name}</td>
                  <td>{b.type}</td>
                  <td>{b.language}</td>
                  <td>{b.positioning_statement ? "✓" : "—"}</td>
                </tr>
              ))}
              {brands.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    Belum ada brand.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
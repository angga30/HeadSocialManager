import { useEffect, useState } from "react";
import { api, type Channel } from "../lib/api";
import { useBrands } from "../lib/useBrands";

export default function Channels() {
  const { brands, selectedId, select } = useBrands();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [platform, setPlatform] = useState("instagram");
  const [handle, setHandle] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = async (brandId: number) => {
    try {
      setChannels(await api.listChannels(brandId));
    } catch (e) {
      setMsg(`⚠️ ${e}`);
    }
  };

  useEffect(() => {
    if (selectedId != null) void load(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const add = async () => {
    if (selectedId == null || !handle.trim()) return;
    try {
      await api.createChannel(selectedId, { platform, handle });
      setMsg(`✅ Channel ${platform} tersambung.`);
      setHandle("");
      await load(selectedId);
    } catch (e) {
      setMsg(`⚠️ ${e}`);
    }
  };

  return (
    <div>
      <h2 className="page-title">Channels</h2>
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

      <div className="card">
        <h3>Tambah channel</h3>
        <div className="row">
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="instagram">instagram</option>
            <option value="threads">threads</option>
            <option value="linkedin">linkedin</option>
          </select>
          <input placeholder="@handle" value={handle} onChange={(e) => setHandle(e.target.value)} />
          <button className="primary" onClick={add} disabled={selectedId == null}>
            Sambungkan
          </button>
        </div>
        {msg && <div className={`msg ${msg.startsWith("⚠️") ? "err" : "ok"}`}>{msg}</div>}
      </div>

      <div className="card">
        <h3>Channel terhubung</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Platform</th>
              <th>Handle</th>
              <th>Bahasa</th>
            </tr>
          </thead>
          <tbody>
            {channels.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>
                  <span className="badge">{c.platform}</span>
                </td>
                <td>{c.handle}</td>
                <td>{c.language ?? "—"}</td>
              </tr>
            ))}
            {channels.length === 0 && (
              <tr>
                <td colSpan={4} className="muted">
                  Belum ada channel.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
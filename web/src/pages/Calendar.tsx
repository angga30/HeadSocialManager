import { useEffect, useState } from "react";
import { api, type Plan, type Post } from "../lib/api";
import { useBrands } from "../lib/useBrands";

export default function Calendar() {
  const { brands, selectedId, select } = useBrands();
  const [posts, setPosts] = useState<Post[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [period, setPeriod] = useState("2026-10");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async (brandId: number) => {
    try {
      const [p, pl] = await Promise.all([api.listPosts(brandId), api.listPlans(brandId)]);
      setPosts(p);
      setPlans(pl);
    } catch (e) {
      setMsg(`⚠️ ${e}`);
    }
  };

  useEffect(() => {
    if (selectedId != null) void load(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const makePlan = async () => {
    if (selectedId == null) return;
    setBusy(true);
    try {
      const plan = await api.createPlan(selectedId, { period, theme: "Auto", cadence: { instagram: 3, linkedin: 2 } });
      const created = await api.fanoutPlan(plan.id);
      setMsg(`✅ Rencana ${plan.period} dibuat, ${created.length} slot posting.`);
      await load(selectedId);
    } catch (e) {
      setMsg(`⚠️ ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const approve = async (id: number) => {
    await api.approvePost(id);
    if (selectedId != null) await load(selectedId);
  };
  const publish = async (id: number) => {
    await api.publishPost(id);
    if (selectedId != null) await load(selectedId);
  };

  return (
    <div>
      <h2 className="page-title">Calendar</h2>
      <div className="row" style={{ marginBottom: 14 }}>
        <span className="muted">Brand:</span>
        <select value={selectedId ?? ""} onChange={(e) => select(Number(e.target.value))}>
          {brands.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <input style={{ width: 110 }} value={period} onChange={(e) => setPeriod(e.target.value)} />
        <button className="primary" onClick={makePlan} disabled={busy || selectedId == null}>
          Buat rencana + fan-out
        </button>
      </div>
      {msg && <div className={`msg ${msg.startsWith("⚠️") ? "err" : "ok"}`}>{msg}</div>}

      {plans.length > 0 && (
        <div className="card">
          <h3>Rencana</h3>
          <div className="row">
            {plans.map((p) => (
              <span key={p.id} className="badge">
                {p.period} · {p.theme ?? "-"}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h3>Posting ({posts.length})</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Channel</th>
              <th>Pillar</th>
              <th>Media</th>
              <th>Jadwal</th>
              <th>Status</th>
              <th>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {posts.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.channel ?? "—"}</td>
                <td>{p.pillar ?? "—"}</td>
                <td>
                  <div className="row">
                    {(p.media ?? []).map((m) => (
                      <img
                        key={m.filename}
                        src={m.url}
                        alt={m.filename}
                        style={{ width: 34, height: 34, objectFit: "cover", borderRadius: 6, border: "1px solid var(--border)" }}
                      />
                    ))}
                    {(p.media ?? []).length === 0 && <span className="muted">—</span>}
                  </div>
                </td>
                <td>{p.scheduled_at ? p.scheduled_at.slice(0, 16).replace("T", " ") : "—"}</td>
                <td>
                  <span className={`badge ${p.status}`}>{p.status}</span>
                </td>
                <td>
                  <div className="row">
                    {p.status === "draft" && (
                      <button className="ghost" onClick={() => approve(p.id)}>
                        Approve
                      </button>
                    )}
                    {p.status !== "published" && (
                      <button className="ghost" onClick={() => publish(p.id)}>
                        Publish
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {posts.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  Belum ada post.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
import { useEffect, useState } from "react";
import { api, type Insights as InsightsData } from "../lib/api";
import { useBrands } from "../lib/useBrands";

export default function Insights() {
  const { brands, selectedId, select } = useBrands();
  const [data, setData] = useState<InsightsData | null>(null);
  const [history, setHistory] = useState<{ period: string; channel: string; pillar: string; headline: string; engagement_rate: number }[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId == null) return;
    (async () => {
      try {
        const [ins, hist] = await Promise.all([api.insights(selectedId), api.history(selectedId)]);
        setData(ins);
        setHistory(hist.history);
      } catch (e) {
        setMsg(`⚠️ ${e}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  return (
    <div>
      <h2 className="page-title">Insights</h2>
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
      {msg && <div className="msg err">{msg}</div>}

      <div className="grid-2">
        <div className="card">
          <h3>Top posts</h3>
          <table>
            <thead>
              <tr>
                <th>Channel</th>
                <th>Headline</th>
                <th>Rate</th>
              </tr>
            </thead>
            <tbody>
              {(data?.top_posts ?? []).map((p) => (
                <tr key={p.post_id}>
                  <td>{p.channel}</td>
                  <td>{p.headline || "—"}</td>
                  <td>{p.engagement_rate}</td>
                </tr>
              ))}
              {(data?.top_posts ?? []).length === 0 && (
                <tr>
                  <td colSpan={3} className="muted">
                    Belum ada data (publish dulu untuk menghasilkan metrik).
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Performa per format & channel</h3>
          <table>
            <thead>
              <tr>
                <th>Dimensi</th>
                <th>Nilai</th>
                <th>Avg rate</th>
              </tr>
            </thead>
            <tbody>
              {(data?.format_performance ?? []).map((f) => (
                <tr key={`f-${f.depth}`}>
                  <td>format</td>
                  <td>{f.depth}</td>
                  <td>{f.avg_engagement_rate}</td>
                </tr>
              ))}
              {(data?.channel_notes ?? []).map((c) => (
                <tr key={`c-${c.channel}`}>
                  <td>channel</td>
                  <td>{c.channel}</td>
                  <td>{c.avg_engagement_rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Content history ({history.length})</h3>
        <table>
          <thead>
            <tr>
              <th>Tanggal</th>
              <th>Channel</th>
              <th>Pillar</th>
              <th>Headline</th>
              <th>Rate</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h, i) => (
              <tr key={i}>
                <td>{h.period}</td>
                <td>{h.channel}</td>
                <td>{h.pillar}</td>
                <td>{h.headline || "—"}</td>
                <td>{h.engagement_rate}</td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">
                  Belum ada riwayat.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
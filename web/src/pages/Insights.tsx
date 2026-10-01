import { useEffect, useState } from "react";
import { api, type Insights as InsightsData } from "../lib/api";
import { useBrands } from "../lib/useBrands";
import BrandPicker from "../components/BrandPicker";
import Card, { CardTitle } from "../components/ui/Card";
import PageHeader from "../components/PageHeader";
import StatusMsg from "../components/StatusMsg";

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
        setMsg(String(e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  return (
    <div>
      <PageHeader>Insights</PageHeader>
      <div className="mb-4">
        <BrandPicker brands={brands} selectedId={selectedId} onSelect={select} />
      </div>
      {msg && <StatusMsg kind="err" className="mb-4 mt-0">{msg}</StatusMsg>}

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
        <Card>
          <CardTitle>Top posts</CardTitle>
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="th">Channel</th>
                <th className="th">Headline</th>
                <th className="th">Rate</th>
              </tr>
            </thead>
            <tbody>
              {(data?.top_posts ?? []).map((p) => (
                <tr key={p.post_id} className="hover:bg-panel2/60">
                  <td className="td">{p.channel}</td>
                  <td className="td">{p.headline || "—"}</td>
                  <td className="td tabular-nums">{p.engagement_rate}</td>
                </tr>
              ))}
              {(data?.top_posts ?? []).length === 0 && (
                <tr>
                  <td colSpan={3} className="td text-mute">
                    Belum ada data (publish dulu untuk menghasilkan metrik).
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>

        <Card>
          <CardTitle>Performa per format & channel</CardTitle>
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="th">Dimensi</th>
                <th className="th">Nilai</th>
                <th className="th">Avg rate</th>
              </tr>
            </thead>
            <tbody>
              {(data?.format_performance ?? []).map((f) => (
                <tr key={`f-${f.depth}`} className="hover:bg-panel2/60">
                  <td className="td text-mute">format</td>
                  <td className="td">{f.depth}</td>
                  <td className="td tabular-nums">{f.avg_engagement_rate}</td>
                </tr>
              ))}
              {(data?.channel_notes ?? []).map((c) => (
                <tr key={`c-${c.channel}`} className="hover:bg-panel2/60">
                  <td className="td text-mute">channel</td>
                  <td className="td">{c.channel}</td>
                  <td className="td tabular-nums">{c.avg_engagement_rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card className="mt-4">
        <CardTitle>Content history ({history.length})</CardTitle>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="th">Tanggal</th>
              <th className="th">Channel</th>
              <th className="th">Pillar</th>
              <th className="th">Headline</th>
              <th className="th">Rate</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h, i) => (
              <tr key={i} className="hover:bg-panel2/60">
                <td className="td tabular-nums">{h.period}</td>
                <td className="td">{h.channel}</td>
                <td className="td">{h.pillar}</td>
                <td className="td">{h.headline || "—"}</td>
                <td className="td tabular-nums">{h.engagement_rate}</td>
              </tr>
            ))}
            {history.length === 0 && (
              <tr>
                <td colSpan={5} className="td text-mute">
                  Belum ada riwayat.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

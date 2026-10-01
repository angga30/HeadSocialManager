import { useEffect, useState } from "react";
import { api, type Channel } from "../lib/api";
import { useBrands } from "../lib/useBrands";
import BrandPicker from "../components/BrandPicker";
import Button from "../components/ui/Button";
import Card, { CardTitle } from "../components/ui/Card";
import { Input, Select } from "../components/ui/Field";
import PageHeader from "../components/PageHeader";
import StatusMsg, { type MsgKind } from "../components/StatusMsg";

interface Msg {
  kind: MsgKind;
  text: string;
}

export default function Channels() {
  const { brands, selectedId, select } = useBrands();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [platform, setPlatform] = useState("instagram");
  const [handle, setHandle] = useState("");
  const [msg, setMsg] = useState<Msg | null>(null);

  const load = async (brandId: number) => {
    try {
      setChannels(await api.listChannels(brandId));
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
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
      setMsg({ kind: "ok", text: `Channel ${platform} tersambung.` });
      setHandle("");
      await load(selectedId);
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
    }
  };

  return (
    <div>
      <PageHeader>Channels</PageHeader>
      <div className="mb-4">
        <BrandPicker brands={brands} selectedId={selectedId} onSelect={select} />
      </div>

      <Card className="mb-4">
        <CardTitle>Tambah channel</CardTitle>
        <div className="flex flex-wrap items-center gap-2.5">
          <Select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="instagram">instagram</option>
            <option value="threads">threads</option>
            <option value="linkedin">linkedin</option>
          </Select>
          <Input
            placeholder="@handle"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            className="w-auto"
          />
          <Button onClick={add} disabled={selectedId == null}>
            Sambungkan
          </Button>
        </div>
        {msg && <StatusMsg kind={msg.kind}>{msg.text}</StatusMsg>}
      </Card>

      <Card>
        <CardTitle>Channel terhubung</CardTitle>
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="th">ID</th>
              <th className="th">Platform</th>
              <th className="th">Handle</th>
              <th className="th">Bahasa</th>
            </tr>
          </thead>
          <tbody>
            {channels.map((c) => (
              <tr key={c.id} className="hover:bg-panel2/60">
                <td className="td">{c.id}</td>
                <td className="td">
                  <span className="badge">{c.platform}</span>
                </td>
                <td className="td">{c.handle}</td>
                <td className="td">{c.language ?? "—"}</td>
              </tr>
            ))}
            {channels.length === 0 && (
              <tr>
                <td colSpan={4} className="td text-mute">
                  Belum ada channel.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

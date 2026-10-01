import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Plus } from "@phosphor-icons/react";
import { api } from "../lib/api";
import { useBrands } from "../lib/useBrands";
import Button from "../components/ui/Button";
import Card, { CardTitle } from "../components/ui/Card";
import { Input, Select, Textarea } from "../components/ui/Field";
import PageHeader from "../components/PageHeader";
import StatusMsg, { type MsgKind } from "../components/StatusMsg";

interface Msg {
  kind: MsgKind;
  text: string;
}

const FIELD = "mb-1 block text-[13px] text-mute";

export default function Brands() {
  const { brands, reload, error } = useBrands();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [type, setType] = useState("business");
  const [description, setDescription] = useState("");
  const [language, setLanguage] = useState("id");
  const [msg, setMsg] = useState<Msg | null>(null);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    if (!name.trim()) {
      setMsg({ kind: "err", text: "Nama brand wajib diisi." });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const b = await api.createBrand({ name, type_: type, description, language });
      setName("");
      setDescription("");
      await reload();
      navigate(`/brands/${b.id}`);
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader>Brands</PageHeader>
      {error && <StatusMsg kind="err" className="mb-4 mt-0">{error}</StatusMsg>}

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[340px_1fr]">
        <Card>
          <CardTitle>Brand baru</CardTitle>
          <div className="flex flex-col gap-3">
            <div>
              <label htmlFor="b-name" className={FIELD}>
                Nama
              </label>
              <Input
                id="b-name"
                placeholder="cth. Kopi Senja"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="b-desc" className={FIELD}>
                Deskripsi
              </label>
              <Textarea
                id="b-desc"
                rows={3}
                placeholder="Apa yang dijual / ditawarkan"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="b-type" className={FIELD}>
                  Tipe
                </label>
                <Select id="b-type" className="w-full" value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="personal">personal</option>
                  <option value="business">business</option>
                  <option value="product">product</option>
                </Select>
              </div>
              <div>
                <label htmlFor="b-lang" className={FIELD}>
                  Bahasa
                </label>
                <Select
                  id="b-lang"
                  className="w-full"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="id">id</option>
                  <option value="en">en</option>
                </Select>
              </div>
            </div>
            <Button onClick={create} disabled={busy}>
              <Plus size={15} weight="bold" /> Buat brand
            </Button>
            {msg && <StatusMsg kind={msg.kind}>{msg.text}</StatusMsg>}
          </div>
        </Card>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {brands.map((b) => (
            <button
              key={b.id}
              type="button"
              onClick={() => navigate(`/brands/${b.id}`)}
              className="group rounded-lg border border-line bg-panel p-4 text-left transition-colors hover:border-accent"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold">{b.name}</span>
                <ArrowRight
                  size={15}
                  className="text-mute transition-colors group-hover:text-accent"
                />
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className="badge">{b.type}</span>
                <span className="badge">{b.language}</span>
              </div>
              {b.description && (
                <p className="mt-2 line-clamp-2 text-[13px] text-mute">{b.description}</p>
              )}
            </button>
          ))}
          {brands.length === 0 && (
            <p className="text-[13px] text-mute">Belum ada brand. Buat lewat form di samping.</p>
          )}
        </div>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import { api, type Plan, type Post } from "../lib/api";
import { useBrands } from "../lib/useBrands";
import BrandPicker from "../components/BrandPicker";
import PostDetail from "../components/PostDetail";
import Button from "../components/ui/Button";
import Card, { CardTitle } from "../components/ui/Card";
import PageHeader from "../components/PageHeader";
import StatusMsg, { type MsgKind } from "../components/StatusMsg";

interface Msg {
  kind: MsgKind;
  text: string;
}

const DOT: Record<string, string> = {
  draft: "bg-mute",
  scheduled: "bg-accent",
  published: "bg-ok",
  failed: "bg-danger",
};

const DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];
const pad = (n: number) => String(n).padStart(2, "0");
const ym = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;

// Monday-first grid of 6 weeks covering `month` (Date = first of month).
function monthGrid(month: Date): Date[] {
  const first = new Date(month);
  const offset = (first.getDay() + 6) % 7; // Mon=0
  first.setDate(first.getDate() - offset);
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(first);
    d.setDate(first.getDate() + i);
    return d;
  });
}

export default function Calendar() {
  const { brands, selectedId, select } = useBrands();
  const [posts, setPosts] = useState<Post[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [month, setMonth] = useState(() => new Date());
  const [selected, setSelected] = useState<Post | null>(null);
  const [msg, setMsg] = useState<Msg | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async (brandId: number) => {
    try {
      const [p, pl] = await Promise.all([api.listPosts(brandId), api.listPlans(brandId)]);
      setPosts(p);
      setPlans(pl);
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
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
      const plan = await api.createPlan(selectedId, {
        period: ym(month),
        theme: "Auto",
        cadence: { instagram: 3, linkedin: 2 },
      });
      const created = await api.fanoutPlan(plan.id);
      setMsg({ kind: "ok", text: `Rencana ${plan.period} dibuat, ${created.length} slot posting.` });
      await load(selectedId);
    } catch (e) {
      setMsg({ kind: "err", text: String(e) });
    } finally {
      setBusy(false);
    }
  };

  const approve = async (id: number) => {
    await api.approvePost(id);
    if (selectedId != null) await load(selectedId);
    setSelected((s) => (s ? { ...s, status: "scheduled" } : s));
  };
  const publish = async (id: number) => {
    await api.publishPost(id);
    if (selectedId != null) await load(selectedId);
    setSelected(null);
  };

  // Posts grouped by YYYY-MM-DD of scheduled_at; null-scheduled shown separately.
  const byDay = useMemo(() => {
    const map = new Map<string, Post[]>();
    const unscheduled: Post[] = [];
    for (const p of posts) {
      if (!p.scheduled_at) {
        unscheduled.push(p);
        continue;
      }
      const key = p.scheduled_at.slice(0, 10);
      const arr = map.get(key);
      if (arr) arr.push(p);
      else map.set(key, [p]);
    }
    return { map, unscheduled };
  }, [posts]);

  const grid = useMemo(() => monthGrid(month), [month]);
  const today = new Date().toISOString().slice(0, 10);
  const inMonth = (d: Date) => d.getMonth() === month.getMonth();

  return (
    <div>
      <PageHeader>Calendar</PageHeader>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <BrandPicker brands={brands} selectedId={selectedId} onSelect={select} />
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button
              type="button"
              aria-label="Bulan sebelumnya"
              onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
              className="btn btn-icon"
            >
              <CaretLeft size={14} weight="bold" />
            </button>
            <span className="min-w-36 text-center text-sm font-medium capitalize">
              {month.toLocaleDateString("id-ID", { month: "long", year: "numeric" })}
            </span>
            <button
              type="button"
              aria-label="Bulan berikutnya"
              onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
              className="btn btn-icon"
            >
              <CaretRight size={14} weight="bold" />
            </button>
          </div>
          <Button onClick={makePlan} disabled={busy || selectedId == null}>
            Buat rencana {ym(month)}
          </Button>
        </div>
      </div>

      {msg && <StatusMsg kind={msg.kind} className="mb-4 mt-0">{msg.text}</StatusMsg>}

      {plans.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {plans.map((p) => (
            <span key={p.id} className="badge">
              {p.period} · {p.theme ?? "-"}
            </span>
          ))}
        </div>
      )}

      <Card className="overflow-hidden p-0">
        <div className="grid grid-cols-7 border-b border-line">
          {DAYS.map((d) => (
            <div key={d} className="px-2 py-2 text-center text-xs font-medium text-mute">
              {d}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {grid.map((d) => {
            const key = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
            const dayPosts = byDay.map.get(key) ?? [];
            return (
              <div
                key={key}
                className={`min-h-24 border-b border-r border-line/60 p-1.5 [&:nth-child(7n)]:border-r-0 ${
                  inMonth(d) ? "" : "opacity-40"
                }`}
              >
                <div
                  className={`mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs tabular-nums ${
                    key === today ? "bg-accent font-semibold text-accent-ink" : "text-mute"
                  }`}
                >
                  {d.getDate()}
                </div>
                <div className="flex flex-col gap-1">
                  {dayPosts.slice(0, 3).map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setSelected(p)}
                      title={p.headline}
                      className="flex items-center gap-1.5 rounded-sm border border-line bg-panel2 px-1.5 py-1 text-left text-[11px] leading-tight text-ink transition-colors hover:border-accent"
                    >
                      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[p.status] ?? "bg-mute"}`} />
                      <span className="truncate">{p.headline || `#${p.id}`}</span>
                    </button>
                  ))}
                  {dayPosts.length > 3 && (
                    <button
                      type="button"
                      onClick={() => setSelected(dayPosts[3])}
                      className="px-1 text-left text-[11px] text-mute hover:text-accent"
                    >
                      +{dayPosts.length - 3} lainnya
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {byDay.unscheduled.length > 0 && (
        <Card className="mt-4">
          <CardTitle>Belum dijadwalkan ({byDay.unscheduled.length})</CardTitle>
          <div className="flex flex-wrap gap-2">
            {byDay.unscheduled.map((p) => (
              <button key={p.id} type="button" onClick={() => setSelected(p)} className="badge hover:border-accent">
                <span className={`h-1.5 w-1.5 rounded-full ${DOT[p.status] ?? "bg-mute"}`} />
                {p.headline || `#${p.id}`}
              </button>
            ))}
          </div>
        </Card>
      )}

      {selected && (
        <PostDetail
          post={posts.find((p) => p.id === selected.id) ?? selected}
          onClose={() => setSelected(null)}
          onApprove={approve}
          onPublish={publish}
        />
      )}
    </div>
  );
}

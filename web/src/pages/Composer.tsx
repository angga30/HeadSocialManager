import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ArrowDown, Plus, X } from "@phosphor-icons/react";
import ChatMessage from "../components/ChatMessage";
import MentionInput, { parseMentions } from "../components/MentionInput";
import Button from "../components/ui/Button";
import { convStore } from "../lib/conversationsStore";

const STATUS_LABEL: Record<string, string> = {
  idle: "siap",
  processing: "sedang memproses",
  error: "berhenti / error",
};

const SUGGESTIONS = [
  "Buat positioning brand saya",
  "Susun plan konten bulan ini",
  "Lihat performa minggu lalu",
  "Buat konten untuk slot berikutnya",
];

export default function Composer() {
  const { convs, selected } = useSyncExternalStore(convStore.subscribe, convStore.getSnapshot);
  const [draft, setDraft] = useState("");
  const [atBottom, setAtBottom] = useState(true);
  const logRef = useRef<HTMLDivElement>(null);

  const current = convs.find((c) => c.id === selected) ?? null;
  const messages = current?.messages ?? [];
  const processing = current?.status === "processing";

  useEffect(() => {
    void convStore.load();
  }, []);

  // Follow the stream only while the user is already pinned to the bottom.
  useEffect(() => {
    if (!atBottom) return;
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, atBottom]);

  const onScroll = () => {
    const el = logRef.current;
    if (!el) return;
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80);
  };

  const scrollToBottom = () => {
    const el = logRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setAtBottom(true);
  };

  const send = () => {
    const text = draft.trim();
    if (!text || !current || processing) return;
    convStore.startStream(current.id, text, parseMentions(text));
    setDraft("");
    setAtBottom(true);
  };

  const suggest = (text: string) => {
    if (!current || processing) return;
    convStore.startStream(current.id, text, []);
    setAtBottom(true);
  };

  return (
    <div className="grid h-[calc(100dvh-48px)] grid-cols-[250px_1fr] items-start gap-4">
      <aside className="flex min-h-0 flex-col gap-2.5">
        <Button className="w-full" onClick={() => void convStore.create()}>
          <Plus size={15} weight="bold" /> Percakapan baru
        </Button>
        <div className="flex flex-col gap-1 overflow-auto">
          {convs.map((c) => (
            <div
              key={c.id}
              role="button"
              tabIndex={0}
              onClick={() => void convStore.select(c.id)}
              onKeyDown={(e) => e.key === "Enter" && void convStore.select(c.id)}
              className={`flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-2 text-[13px] transition-colors ${
                c.id === selected
                  ? "border-accent bg-panel2"
                  : "border-transparent bg-panel hover:bg-panel2"
              }`}
            >
              <span className={`dot ${c.status}`} title={STATUS_LABEL[c.status]} />
              <span className="flex-1 truncate">{c.title}</span>
              <button
                type="button"
                title="Hapus"
                aria-label={`Hapus ${c.title}`}
                onClick={(e) => {
                  e.stopPropagation();
                  void convStore.remove(c.id);
                }}
                className="shrink-0 text-mute transition-colors hover:text-danger"
              >
                <X size={13} weight="bold" />
              </button>
            </div>
          ))}
          {convs.length === 0 && <p className="text-[13px] text-mute">Belum ada percakapan.</p>}
        </div>
      </aside>

      <section className="relative flex min-h-0 flex-col">
        <div className="mb-3 flex items-center gap-3">
          <h2 className="text-lg font-semibold tracking-tight">{current?.title ?? "Composer"}</h2>
          {current && (
            <span
              className={`rounded-full border px-2.5 py-0.5 text-xs ${
                current.status === "processing"
                  ? "border-accent text-accent"
                  : current.status === "error"
                    ? "border-danger text-danger"
                    : "border-line text-mute"
              }`}
            >
              {STATUS_LABEL[current.status]}
            </span>
          )}
        </div>

        <div
          ref={logRef}
          onScroll={onScroll}
          className="flex flex-1 flex-col gap-4 overflow-auto px-3 py-2"
        >
          {messages.map((m, i) => (
            <ChatMessage
              key={i}
              msg={m}
              isLast={i === messages.length - 1}
              processing={!!processing}
              onRetry={() => current && convStore.retry(current.id)}
            />
          ))}

          {current && messages.length === 0 && (
            <div className="my-auto text-center">
              <p className="text-sm text-mute">Mulai dengan salah satu ide ini:</p>
              <div className="mt-2.5 flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => suggest(s)}
                    className="rounded-full border border-line bg-panel px-3.5 py-2 text-[13px] text-ink transition-colors hover:border-accent hover:text-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {!current && <p className="text-[13px] text-mute">Pilih atau buat percakapan untuk mulai.</p>}
        </div>

        {!atBottom && messages.length > 0 && (
          <button
            type="button"
            onClick={scrollToBottom}
            title="Ke bawah"
            aria-label="Gulir ke bawah"
            className="absolute bottom-[74px] right-5 z-10 flex h-9 w-9 items-center justify-center rounded-full border border-line bg-panel2 text-ink shadow-lg shadow-black/40 transition-colors hover:border-accent"
          >
            <ArrowDown size={16} weight="bold" />
          </button>
        )}

        <div className="mt-3 flex items-end gap-2.5">
          <MentionInput
            value={draft}
            onChange={setDraft}
            onSubmit={send}
            disabled={!current || processing}
          />
          {processing ? (
            <Button variant="ghost" onClick={() => current && convStore.stop(current.id)}>
              Stop
            </Button>
          ) : (
            <Button onClick={send} disabled={!current}>
              Kirim
            </Button>
          )}
        </div>
      </section>
    </div>
  );
}

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import ChatMessage from "../components/ChatMessage";
import MentionInput, { parseMentions } from "../components/MentionInput";
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
    <div className="composer-layout">
      <aside className="conv-sidebar">
        <button className="primary new-conv" onClick={() => void convStore.create()}>
          + Percakapan baru
        </button>
        <div className="conv-list">
          {convs.map((c) => (
            <div
              key={c.id}
              className={`conv-item ${c.id === selected ? "active" : ""}`}
              onClick={() => void convStore.select(c.id)}
            >
              <span className={`dot ${c.status}`} title={STATUS_LABEL[c.status]} />
              <span className="conv-title">{c.title}</span>
              <button
                className="conv-del"
                title="Hapus"
                onClick={(e) => {
                  e.stopPropagation();
                  void convStore.remove(c.id);
                }}
              >
                ×
              </button>
            </div>
          ))}
          {convs.length === 0 && <p className="muted">Belum ada percakapan.</p>}
        </div>
      </aside>

      <section className="chat">
        <div className="chat-head">
          <h2 className="page-title">{current?.title ?? "Composer"}</h2>
          {current && (
            <span className={`status-pill ${current.status}`}>{STATUS_LABEL[current.status]}</span>
          )}
        </div>

        <div className="chat-log" ref={logRef} onScroll={onScroll}>
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
            <div className="suggestions">
              <p className="muted">Mulai dengan salah satu ide ini:</p>
              <div className="suggestion-chips">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip-btn" onClick={() => suggest(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {!current && <p className="muted">Pilih atau buat percakapan untuk mulai.</p>}
        </div>

        {!atBottom && messages.length > 0 && (
          <button className="scroll-bottom" onClick={scrollToBottom} title="Ke bawah">
            ↓
          </button>
        )}

        <div className="chat-input">
          <MentionInput
            value={draft}
            onChange={setDraft}
            onSubmit={send}
            disabled={!current || processing}
          />
          {processing ? (
            <button className="ghost" onClick={() => current && convStore.stop(current.id)}>
              Stop
            </button>
          ) : (
            <button className="primary" onClick={send} disabled={!current}>
              Kirim
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

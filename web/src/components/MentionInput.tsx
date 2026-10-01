import { useEffect, useRef, useState } from "react";
import { api, type Mention, type MentionCandidates, type MentionType } from "../lib/api";

interface Option {
  type: MentionType;
  id: number;
  label: string;
}

const EMPTY: MentionCandidates = { brands: [], channels: [], posts: [] };

export function parseMentions(text: string): Mention[] {
  const out: Mention[] = [];
  const re = /@(brand|channel|post):(\d+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    out.push({ type: m[1] as MentionType, id: Number(m[2]) });
  }
  return out;
}

function flatten(c: MentionCandidates): Option[] {
  return [
    ...c.brands.map((b) => ({ type: "brand" as const, id: b.id, label: b.label })),
    ...c.channels.map((c2) => ({ type: "channel" as const, id: c2.id, label: c2.label })),
    ...c.posts.map((p) => ({ type: "post" as const, id: p.id, label: p.label })),
  ];
}

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export default function MentionInput({ value, onChange, onSubmit, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [options, setOptions] = useState<Option[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [triggerAt, setTriggerAt] = useState<number | null>(null);

  // Query text right after the last "@" before the caret, if any.
  const currentQuery = (): { at: number; q: string } | null => {
    const el = ref.current;
    if (!el) return null;
    const before = value.slice(0, el.selectionStart ?? value.length);
    const at = before.lastIndexOf("@");
    if (at < 0) return null;
    const q = before.slice(at + 1);
    if (/\s/.test(q)) return null;
    return { at, q };
  };

  useEffect(() => {
    const cur = currentQuery();
    if (!cur) {
      setOpen(false);
      setOptions([]);
      return;
    }
    setTriggerAt(cur.at);
    const t = setTimeout(async () => {
      try {
        const res = await api.searchMentions(cur.q);
        const opts = flatten(res ?? EMPTY);
        setOptions(opts);
        setOpen(opts.length > 0);
        setActive(0);
      } catch {
        setOptions([]);
        setOpen(false);
      }
    }, 180);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const insert = (opt: Option) => {
    if (triggerAt == null) return;
    const token = `@${opt.type}:${opt.id} `;
    const next = value.slice(0, triggerAt) + token + value.slice(ref.current?.selectionStart ?? value.length);
    onChange(next);
    setOpen(false);
    const pos = triggerAt + token.length;
    requestAnimationFrame(() => {
      ref.current?.focus();
      ref.current?.setSelectionRange(pos, pos);
    });
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (open) {
      if (e.key === "ArrowDown") return (e.preventDefault(), setActive((a) => (a + 1) % options.length));
      if (e.key === "ArrowUp") return (e.preventDefault(), setActive((a) => (a - 1 + options.length) % options.length));
      if (e.key === "Enter" || e.key === "Tab") return (e.preventDefault(), insert(options[active]));
      if (e.key === "Escape") return (e.preventDefault(), setOpen(false));
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="mention-wrap">
      <textarea
        ref={ref}
        className="mention-input"
        rows={1}
        placeholder="Ketik pesan… @ untuk mention brand/channel/post"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
      />
      {open && (
        <div className="mention-popover">
          {options.map((o, i) => (
            <button
              key={`${o.type}:${o.id}`}
              className={i === active ? "active" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                insert(o);
              }}
            >
              <span className={`mention-badge ${o.type}`}>{o.type}</span> {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
// Module-level conversation store.
//
// Streams live here (not inside a React component), so switching conversation or leaving
// the Composer page does NOT abort an in-flight agent run — state keeps flowing and is
// reflected when the user returns.

import { api, streamChat, type ChatEvent, type Mention } from "./api";

export type ConvStatus = "idle" | "processing" | "error";

export interface UIToolStep {
  name: string;
  summary: string;
  status: "start" | "done";
}

export interface UIMsg {
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
  error?: boolean;
  stopped?: boolean;
  agent?: string;
  steps?: UIToolStep[];
  activity?: string; // live status line while the agent works
  /** Intermediate "thinking" text segments (closed by tool calls / agent handoffs). */
  thoughts?: string[];
  /** Final response text, promoted from the last thought segment on done. */
  answer?: string;
  /** Internal: is the last thought segment still accepting tokens? */
  segOpen?: boolean;
}

export interface UIConv {
  id: number;
  title: string;
  status: ConvStatus;
  messages: UIMsg[];
  loaded: boolean;
}

interface State {
  convs: UIConv[];
  selected: number | null;
  ready: boolean;
}

let state: State = { convs: [], selected: null, ready: false };
const listeners = new Set<() => void>();
const controllers = new Map<number, AbortController>();

const DEFAULT_TITLE = "Percakapan baru";
const STOP_MARKER = "\n\n_(dihentikan)_";

// Mirror of the server's title heuristic (conversation_service._title_from).
function titleFrom(text: string): string {
  const clean = text.trim().replace(/\s+/g, " ");
  return clean.length > 60 ? clean.slice(0, 57) + "…" : clean || DEFAULT_TITLE;
}

function set(next: Partial<State>) {
  state = { ...state, ...next };
  listeners.forEach((l) => l());
}

function patchConv(id: number, fn: (c: UIConv) => UIConv) {
  set({ convs: state.convs.map((c) => (c.id === id ? fn(c) : c)) });
}

// Apply one SSE event to the trailing assistant message of a conversation.
function handleEvent(id: number, event: ChatEvent) {
  patchConv(id, (c) => {
    const msgs = [...c.messages];
    const idx = msgs.length - 1;
    const last = msgs[idx];
    if (!last || last.role !== "assistant") return c;
    const next: UIMsg = { ...last };
    switch (event.type) {
      case "token": {
        const chunk = event.text ?? "";
        next.text = last.text + chunk;
        next.activity = undefined;
        if (last.answer) {
          // Late tokens after done — append to the final answer.
          next.answer = last.answer + chunk;
        } else {
          const segs = [...(last.thoughts ?? [])];
          if (!last.segOpen || segs.length === 0) segs.push(chunk);
          else segs[segs.length - 1] += chunk;
          next.thoughts = segs;
          next.segOpen = true;
        }
        break;
      }
      case "status":
        next.activity = event.state === "thinking" ? "berpikir…" : undefined;
        break;
      case "agent":
        next.agent = event.name;
        next.segOpen = false; // handoff → next text starts a new thought segment
        break;
      case "tool": {
        const steps = [...(last.steps ?? [])];
        if (event.status === "start") {
          steps.push({ name: event.name ?? "", summary: event.summary ?? "", status: "start" });
          next.activity = `menjalankan ${event.name}…`;
        } else {
          const i = steps.findIndex((s) => s.name === event.name && s.status === "start");
          if (i >= 0) steps[i] = { ...steps[i], status: "done", summary: event.summary || steps[i].summary };
          else steps.push({ name: event.name ?? "", summary: event.summary ?? "", status: "done" });
        }
        next.steps = steps;
        next.segOpen = false; // tool call separates thinking from what follows
        break;
      }
      case "error":
        next.error = true;
        next.text = event.message ?? "Terjadi error.";
        next.activity = undefined;
        break;
      case "done": {
        next.pending = false;
        next.stopped = event.stopped;
        next.activity = undefined;
        // The last thought segment IS the final response — promote it.
        const segs = [...(last.thoughts ?? [])];
        if (segs.length > 0) {
          next.answer = segs.pop();
          next.thoughts = segs;
        }
        break;
      }
    }
    msgs[idx] = next;
    return { ...c, messages: msgs };
  });
}

function finish(id: number) {
  patchConv(id, (c) => {
    const msgs = [...c.messages];
    const last = msgs[msgs.length - 1];
    if (last && last.role === "assistant") {
      msgs[msgs.length - 1] = {
        ...last,
        pending: false,
        activity: undefined,
        text: last.text || "_Agent tidak menghasilkan respons._",
        answer: last.answer || last.text || "_Agent tidak menghasilkan respons._",
      };
    }
    return { ...c, status: last?.error ? "error" : "idle", messages: msgs };
  });
}

// POST an SSE run (send or retry) and keep the last assistant message in sync.
function consume(id: number, path: string, body: unknown, controller: AbortController) {
  void streamChat(path, body, (event) => handleEvent(id, event), controller.signal)
    .then(() => finish(id))
    .catch((err) => {
      if (!controller.signal.aborted) {
        const message = err instanceof Error ? err.message : String(err);
        handleEvent(id, { type: "error", message: `⚠️ ${message}` });
      }
      finish(id);
    })
    .finally(() => {
      controllers.delete(id);
    });
}

export const convStore = {
  subscribe(l: () => void) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  getSnapshot(): State {
    return state;
  },

  async load() {
    const list = await api.listConversations();
    const existing = new Map(state.convs.map((c) => [c.id, c]));
    const convs: UIConv[] = list.map((c) => {
      const prev = existing.get(c.id);
      return prev
        ? { ...prev, title: c.title, status: c.status }
        : { id: c.id, title: c.title, status: c.status, messages: [], loaded: false };
    });
    const selected = state.selected ?? (convs.length ? convs[0].id : null);
    set({ convs, selected, ready: true });
    if (selected != null) await convStore.ensureMessages(selected);
  },

  async select(id: number) {
    set({ selected: id });
    await convStore.ensureMessages(id);
  },

  async ensureMessages(id: number) {
    const conv = state.convs.find((c) => c.id === id);
    if (!conv || conv.loaded || conv.status === "processing") return;
    const msgs = await api.getMessages(id);
    patchConv(id, (c) => ({
      ...c,
      loaded: true,
      messages: msgs.map((m) => ({ role: m.role, text: m.text })),
    }));
  },

  async create(): Promise<number> {
    const created = await api.createConversation();
    const conv: UIConv = {
      id: created.id,
      title: created.title,
      status: "idle",
      messages: [],
      loaded: true,
    };
    set({ convs: [conv, ...state.convs], selected: created.id });
    return created.id;
  },

  async remove(id: number) {
    controllers.get(id)?.abort();
    controllers.delete(id);
    await api.deleteConversation(id);
    const convs = state.convs.filter((c) => c.id !== id);
    set({ convs, selected: state.selected === id ? (convs[0]?.id ?? null) : state.selected });
  },

  /** Ask the server to cancel the run, then stop reading the stream. */
  stop(id: number) {
    void api.stopConversation(id).catch(() => undefined);
    controllers.get(id)?.abort();
    controllers.delete(id);
    patchConv(id, (c) => {
      const msgs = [...c.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        const marker = last.text ? STOP_MARKER : STOP_MARKER.trim();
        const text = last.text + marker;
        msgs[msgs.length - 1] = {
          ...last,
          text,
          answer: (last.answer ?? "") + marker,
          pending: false,
          stopped: true,
          activity: undefined,
        };
      }
      return { ...c, status: "idle", messages: msgs };
    });
  },

  /** Start an agent run for a conversation; keeps streaming even if the UI unmounts. */
  startStream(id: number, text: string, mentions: Mention[]) {
    if (controllers.has(id)) return; // already processing
    const controller = new AbortController();
    controllers.set(id, controller);

    patchConv(id, (c) => ({
      ...c,
      status: "processing",
      loaded: true,
      title: c.title === DEFAULT_TITLE ? titleFrom(text) : c.title,
      messages: [...c.messages, { role: "user", text }, { role: "assistant", text: "", pending: true }],
    }));

    consume(id, `/chat/conversations/${id}/stream`, { message: text, mentions }, controller);
  },

  /** Re-run the last user message: drop the trailing assistant reply, then re-stream. */
  retry(id: number) {
    if (controllers.has(id)) return;
    const controller = new AbortController();
    controllers.set(id, controller);

    patchConv(id, (c) => {
      const msgs = [...c.messages];
      if (msgs.length && msgs[msgs.length - 1].role === "assistant") msgs.pop();
      msgs.push({ role: "assistant", text: "", pending: true });
      return { ...c, status: "processing", messages: msgs };
    });

    consume(id, `/chat/conversations/${id}/retry`, {}, controller);
  },

  reset() {
    state = { convs: [], selected: null, ready: false };
    listeners.forEach((l) => l());
  },
};

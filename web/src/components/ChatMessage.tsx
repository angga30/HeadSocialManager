import type { UIMsg } from "../lib/conversationsStore";
import { ArrowClockwise, Robot } from "@phosphor-icons/react";
import CopyButton from "./CopyButton";
import Markdown from "./Markdown";
import ThinkingBlock from "./ThinkingBlock";
import ToolSteps from "./ToolSteps";

// Render @type:id tokens as chips; the rest as plain text.
function renderMentions(text: string) {
  const parts = text.split(/(@(?:brand|channel|post):\d+)/g);
  return parts.map((p, i) => {
    const m = /^@(brand|channel|post):(\d+)$/.exec(p);
    if (m) {
      return (
        <span key={i} className={`mention-badge ${m[1]}`}>
          {m[1]}#{m[2]}
        </span>
      );
    }
    return <span key={i}>{p}</span>;
  });
}

interface Props {
  msg: UIMsg;
  isLast: boolean;
  processing: boolean;
  onRetry: () => void;
}

export default function ChatMessage({ msg, isLast, processing, onRetry }: Props) {
  if (msg.role === "user") {
    return (
      <div className="flex flex-col items-end">
        <div className="max-w-[75%] self-end rounded-lg rounded-br-sm bg-accent px-3.5 py-2 text-sm leading-relaxed text-accent-ink">
          {renderMentions(msg.text)}
        </div>
        <div className="msg-actions">
          <CopyButton text={msg.text} label="Copy pesan" />
        </div>
      </div>
    );
  }

  const steps = msg.steps ?? [];
  const thoughts = msg.thoughts ?? [];
  const answer = msg.answer ?? (thoughts.length === 0 ? msg.text : "");
  const showActivity = msg.pending && (msg.activity || (!answer && thoughts.length === 0));

  return (
    <div className="flex flex-col items-start gap-2">
      {thoughts.length > 0 && <ThinkingBlock thoughts={thoughts} live={!!msg.pending} />}

      {answer || msg.error ? (
        <div
          className={`w-full rounded-lg rounded-bl-sm border bg-panel2 px-3.5 py-2.5 text-sm leading-relaxed ${
            msg.error ? "border-danger" : "border-line"
          }`}
        >
          <div className="mb-1.5 flex items-center gap-2">
            <span className="flex items-center gap-1 text-[11px] uppercase tracking-wider text-mute">
              <Robot size={12} /> {msg.agent || "agent"}
            </span>
            {msg.stopped && (
              <span className="rounded-full border border-danger px-2 py-px text-[11px] text-danger">
                dihentikan
              </span>
            )}
          </div>
          {steps.length > 0 && <ToolSteps steps={steps} live={!!msg.pending} />}
          {showActivity && (
            <div className="flex items-center gap-2 py-0.5 text-[13px] text-mute">
              <span className="dots">
                <i />
                <i />
                <i />
              </span>
              <span>{msg.activity || "berpikir…"}</span>
            </div>
          )}
          {msg.error ? (
            <div className="flex flex-col items-start gap-2">
              <div className="whitespace-pre-wrap text-[13px] text-danger">{msg.text}</div>
              <button
                type="button"
                onClick={onRetry}
                disabled={processing}
                className="btn-ghost px-2 py-1 text-xs disabled:opacity-50"
              >
                <ArrowClockwise size={13} /> Coba lagi
              </button>
            </div>
          ) : (
            <Markdown>{answer}</Markdown>
          )}
        </div>
      ) : (
        <div className="w-full">
          {steps.length > 0 && <ToolSteps steps={steps} live={!!msg.pending} />}
          {showActivity && (
            <div className="flex items-center gap-2 py-0.5 text-[13px] text-mute">
              <span className="dots">
                <i />
                <i />
                <i />
              </span>
              <span>{msg.activity || "berpikir…"}</span>
            </div>
          )}
        </div>
      )}

      <div className="msg-actions">
        {answer && !msg.error && <CopyButton text={answer} label="Copy jawaban" />}
        {isLast && !processing && (
          <button
            type="button"
            title="Ulangi"
            aria-label="Ulangi"
            onClick={onRetry}
            className="btn btn-icon h-6 w-6"
          >
            <ArrowClockwise size={13} />
          </button>
        )}
      </div>
    </div>
  );
}

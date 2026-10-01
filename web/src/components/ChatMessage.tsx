import type { UIMsg } from "../lib/conversationsStore";
import CopyButton from "./CopyButton";
import Markdown from "./Markdown";
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
      <div className="msg-row user">
        <div className="bubble user">
          <div className="bubble-body">{renderMentions(msg.text)}</div>
        </div>
        <div className="msg-actions">
          <CopyButton text={msg.text} label="Copy pesan" />
        </div>
      </div>
    );
  }

  const steps = msg.steps ?? [];
  const showActivity = msg.pending && (msg.activity || !msg.text);

  return (
    <div className="msg-row assistant">
      <div className={`bubble assistant ${msg.error ? "has-error" : ""}`}>
        <div className="bubble-head">
          <span className="agent-name">🤖 {msg.agent || "agent"}</span>
          {msg.stopped && <span className="chip stopped">dihentikan</span>}
        </div>
        {steps.length > 0 && <ToolSteps steps={steps} live={!!msg.pending} />}
        {showActivity && (
          <div className="activity">
            <span className="dots">
              <i />
              <i />
              <i />
            </span>
            <span className="activity-text">{msg.activity || "berpikir…"}</span>
          </div>
        )}
        {msg.error ? (
          <div className="error-banner">
            <div className="error-text">{msg.text}</div>
            <button className="ghost" onClick={onRetry} disabled={processing}>
              ↻ Coba lagi
            </button>
          </div>
        ) : msg.text ? (
          <div className="bubble-body">
            <Markdown>{msg.text}</Markdown>
          </div>
        ) : null}
      </div>
      <div className="msg-actions">
        {msg.text && !msg.error && <CopyButton text={msg.text} label="Copy pesan" />}
        {isLast && !processing && (
          <button className="act-btn" title="Ulangi" aria-label="Ulangi" onClick={onRetry}>
            ↻
          </button>
        )}
      </div>
    </div>
  );
}

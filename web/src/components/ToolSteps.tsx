import { useState } from "react";
import type { UIToolStep } from "../lib/conversationsStore";

// Collapsible "steps" list above an answer (Perplexity-style); collapsed by default.
export default function ToolSteps({ steps, live }: { steps: UIToolStep[]; live: boolean }) {
  const [open, setOpen] = useState(false);
  const done = steps.filter((s) => s.status === "done").length;
  const running = live && steps.some((s) => s.status === "start");

  return (
    <div className={`steps ${open ? "open" : ""}`}>
      <button type="button" className="steps-head" onClick={() => setOpen((o) => !o)}>
        <span className="steps-caret">{open ? "▾" : "▸"}</span>
        {running ? <span className="spinner" /> : <span className="steps-icon">🧰</span>}
        <span>{steps.length} langkah</span>
        <span className="steps-count">
          {done}/{steps.length}
        </span>
      </button>
      {open && (
        <ul className="steps-list">
          {steps.map((s, i) => (
            <li key={i} className={s.status}>
              <span className="step-status">{s.status === "done" ? "✓" : "…"}</span>
              <span className="step-name">{s.name}</span>
              {s.summary && <span className="step-summary">{s.summary}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

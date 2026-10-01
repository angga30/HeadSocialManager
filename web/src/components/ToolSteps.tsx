import { useState } from "react";
import { CaretDown, CaretRight, Check } from "@phosphor-icons/react";
import type { UIToolStep } from "../lib/conversationsStore";

// Collapsible "steps" list above an answer (Perplexity-style); collapsed by default.
export default function ToolSteps({ steps, live }: { steps: UIToolStep[]; live: boolean }) {
  const [open, setOpen] = useState(false);
  const done = steps.filter((s) => s.status === "done").length;
  const running = live && steps.some((s) => s.status === "start");

  return (
    <div className="mb-2 overflow-hidden rounded-md border border-line bg-bg">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-xs text-mute transition-colors hover:text-ink"
      >
        {open ? <CaretDown size={11} /> : <CaretRight size={11} />}
        {running ? (
          <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-line border-t-accent" />
        ) : (
          <Check size={12} weight="bold" className="text-ok" />
        )}
        <span>{steps.length} langkah</span>
        <span className="ml-auto tabular-nums">
          {done}/{steps.length}
        </span>
      </button>
      {open && (
        <ul className="flex flex-col gap-1 pb-2 pl-7 pr-2.5">
          {steps.map((s, i) => (
            <li key={i} className="flex items-baseline gap-2 text-xs text-mute">
              <span className={s.status === "done" ? "text-ok" : ""}>
                {s.status === "done" ? <Check size={11} weight="bold" /> : "…"}
              </span>
              <span className={`font-mono text-xs ${s.status === "done" ? "text-ok" : "text-ink"}`}>
                {s.name}
              </span>
              {s.summary && <span className="truncate opacity-80">{s.summary}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

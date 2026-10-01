import { useState } from "react";
import { Brain, CaretDown, CaretRight } from "@phosphor-icons/react";
import { cn } from "../lib/cn";

// Collapsible chain-of-thought section. Expanded by default (stays open after the
// answer arrives); user can collapse it manually.
export default function ThinkingBlock({
  thoughts,
  live,
}: {
  thoughts: string[];
  live: boolean;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="w-full">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-md px-1 py-1 text-xs text-mute transition-colors hover:text-ink"
      >
        {open ? <CaretDown size={11} /> : <CaretRight size={11} />}
        <Brain size={13} className={live ? "text-accent" : ""} />
        <span className={cn(live && "text-accent")}>
          {live ? "Berpikir…" : `Proses berpikir (${thoughts.length} bagian)`}
        </span>
      </button>
      {open && (
        <div className="mt-1 max-h-48 space-y-2.5 overflow-y-auto border-l-2 border-line pl-3">
          {thoughts.map((t, i) => (
            <p key={i} className="whitespace-pre-wrap text-[12.5px] leading-relaxed text-mute">
              {t.trim() || "…"}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

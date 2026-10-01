import { useState } from "react";
import { Check, Copy } from "@phosphor-icons/react";
import { cn } from "../lib/cn";

// Small clipboard button used per code block and per message.
export default function CopyButton({
  text,
  label = "Copy",
  className,
}: {
  text: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard API unavailable (non-secure context) — fall back to a temp textarea.
      const el = document.createElement("textarea");
      el.value = text;
      el.style.position = "fixed";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      try {
        document.execCommand("copy");
      } finally {
        document.body.removeChild(el);
      }
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={copy}
      className={cn(
        "inline-flex items-center gap-1 rounded-sm border border-line bg-panel px-2 py-0.5 text-[11px] text-mute transition-colors hover:border-accent hover:text-ink",
        className
      )}
    >
      {copied ? (
        <>
          <Check size={11} weight="bold" className="text-ok" /> tersalin
        </>
      ) : (
        <>
          <Copy size={11} /> copy
        </>
      )}
    </button>
  );
}

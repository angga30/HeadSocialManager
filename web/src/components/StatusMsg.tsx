import { CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { cn } from "../lib/cn";

export type MsgKind = "ok" | "err";

// Replaces emoji-prefix string sniffing (msg.startsWith("⚠️")).
export default function StatusMsg({
  kind,
  children,
  className,
}: {
  kind: MsgKind;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      role={kind === "err" ? "alert" : "status"}
      className={cn(
        "mt-1 flex items-center gap-1.5 text-[13px]",
        kind === "err" ? "text-danger" : "text-ok",
        className
      )}
    >
      {kind === "err" ? <WarningCircle size={14} weight="fill" /> : <CheckCircle size={14} weight="fill" />}
      <span>{children}</span>
    </p>
  );
}

import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export default function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("card", className)} {...rest} />;
}

export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("mb-3 text-sm font-semibold text-ink", className)} {...rest} />;
}

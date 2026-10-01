import type { HTMLAttributes } from "react";
import { cn } from "../lib/cn";

export default function PageHeader({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("mb-4 text-lg font-semibold tracking-tight", className)} {...rest} />;
}

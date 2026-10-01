import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

type Variant = "primary" | "ghost";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

// primary = solid accent CTA, ghost = outlined secondary action.
const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", className, type = "button", ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(variant === "primary" ? "btn-primary" : "btn-ghost", className)}
      {...rest}
    />
  );
});

export default Button;

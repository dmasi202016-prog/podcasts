import { type HTMLAttributes } from "react";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "source" | "emotion" | "speaker";
  color?: string;
}

const VARIANT_STYLES = {
  default: "bg-zinc-700 text-zinc-200",
  source: "bg-blue-900/60 text-blue-300",
  emotion: "bg-amber-900/60 text-amber-300",
  speaker: "bg-violet-900/60 text-violet-300",
};

export function Badge({
  variant = "default",
  className = "",
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${VARIANT_STYLES[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}

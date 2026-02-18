import { type HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  selected?: boolean;
  hoverable?: boolean;
}

export function Card({
  selected = false,
  hoverable = false,
  className = "",
  children,
  ...props
}: CardProps) {
  const base = "rounded-2xl border bg-zinc-900 p-5 transition-all";
  const border = selected
    ? "border-violet-500 ring-2 ring-violet-500/30"
    : "border-zinc-700/50";
  const hover = hoverable ? "hover:border-zinc-500 cursor-pointer" : "";

  return (
    <div className={`${base} ${border} ${hover} ${className}`} {...props}>
      {children}
    </div>
  );
}

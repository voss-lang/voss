import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
  className?: string;
};

export default function Terminal({ title = "voss", children, className = "" }: Props) {
  return (
    <div
      className={`overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_30px_80px_-30px_rgba(0,0,0,0.7)] ${className}`}
    >
      <div className="flex items-center border-b border-[var(--border)] bg-[var(--background)] px-4 py-3">
        <span className="truncate font-mono text-xs text-[var(--muted)]">{title}</span>
      </div>
      {children}
    </div>
  );
}

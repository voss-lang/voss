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
      <div className="flex items-center gap-2 border-b border-[var(--border)] bg-[var(--background)] px-4 py-3">
        <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
        <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
        <span className="h-3 w-3 rounded-full bg-[#28c840]" />
        <span className="ml-3 truncate font-mono text-xs text-[var(--muted)]">{title}</span>
      </div>
      {children}
    </div>
  );
}

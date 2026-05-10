"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";
import type { CliExample } from "@/content/cli-examples";

export type RenderedExample = CliExample & { html: string };

export default function CliShowcaseTabs({ examples }: { examples: RenderedExample[] }) {
  const [activeId, setActiveId] = useState<string | undefined>(examples[0]?.id);
  const active = examples.find((e) => e.id === activeId) ?? examples[0];
  if (!active) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex flex-wrap items-center gap-1 border-b border-[var(--border)] bg-[var(--surface-2)] px-2 py-2">
        {examples.map((ex) => (
          <button
            key={ex.id}
            type="button"
            onClick={() => setActiveId(ex.id)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              ex.id === activeId
                ? "bg-[var(--background)] text-[var(--foreground)] shadow-sm"
                : "text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {ex.label}
          </button>
        ))}
      </div>

      <div className="border-b border-[var(--border)] px-5 py-3 text-sm text-[var(--muted)]">
        {active.blurb}
      </div>

      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--background)] px-5 py-3 font-mono text-sm">
        <div className="flex min-w-0 items-center gap-3">
          <span className="text-[var(--accent)]">$</span>
          <span className="truncate">{active.command}</span>
        </div>
        <CopyButton text={active.command} />
      </div>

      <div
        className="overflow-x-auto p-5"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: active.html }}
      />
    </div>
  );
}

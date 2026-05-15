"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";

type InstallTab = {
  id: "npm" | "pip" | "search";
  label: string;
  cmd: string;
};

const TABS: InstallTab[] = [
  { id: "npm", label: "npm", cmd: "npm i -g @vosslang/cli" },
  { id: "pip", label: "pip", cmd: "pip install voss" },
  { id: "search", label: "semantic memory", cmd: 'pip install "voss[search]"' },
];

export default function InstallTabs() {
  const [active, setActive] = useState<InstallTab["id"]>("npm");
  const tab = TABS.find((t) => t.id === active);

  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-10 max-w-2xl">
          <h2 className="display text-4xl sm:text-5xl">
            <span className="em">Install</span>.
          </h2>
          <p className="mt-4 text-[var(--muted)]">
            The npm package vendors Python 3.12 and the Voss wheel. Use pip when you manage
            Python 3.11+ yourself.
          </p>
        </div>

        <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="flex border-b border-[var(--border)] bg-[var(--surface-2)]">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setActive(t.id)}
                className={`relative px-5 py-3 text-sm font-mono transition ${
                  t.id === active
                    ? "text-[var(--foreground)]"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {t.label}
                {t.id === active && (
                  <span className="absolute inset-x-2 -bottom-px h-px bg-[var(--accent)]" />
                )}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between gap-3 px-5 py-4 font-mono text-sm">
            <div className="flex min-w-0 items-center gap-3">
              <span className="text-[var(--accent)]">$</span>
              <span className="truncate">{tab?.cmd}</span>
            </div>
            {tab && <CopyButton text={tab.cmd} />}
          </div>
        </div>
      </div>
    </section>
  );
}

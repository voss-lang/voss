"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";

const TABS = [
  { id: "pip", label: "pip", cmd: 'pip install -e ".[dev]"', active: true },
  { id: "cargo", label: "cargo", cmd: "cargo install voss   # coming with v1", active: false },
  { id: "brew", label: "brew", cmd: "brew install voss      # coming with v1", active: false },
];

export default function InstallTabs() {
  const [active, setActive] = useState("pip");
  const tab = TABS.find((t) => t.id === active);

  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-10 max-w-2xl">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Install</h2>
          <p className="mt-4 text-[var(--muted)]">
            Voss runs on Python 3.11+. Native binaries are on the roadmap.
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
                {!t.active && (
                  <span className="ml-2 rounded bg-[var(--background)] px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    soon
                  </span>
                )}
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

import type { CSSProperties } from "react";

import { Stagger, StaggerItem } from "./Reveal";

const controls = [
  {
    label: "Scope",
    title: "Writes stay bounded",
    body: "Edit mode starts from the path you named and keeps mutation inside explicit project boundaries.",
    tone: "#FF5B1F",
  },
  {
    label: "Modes",
    title: "Planning and editing are separate",
    body: "Plan, edit, and auto modes make repo mutation a deliberate workflow choice.",
    tone: "#2A6FDB",
  },
  {
    label: "Memory",
    title: "Context survives the session",
    body: "VOSS.md, project memory, and session records keep useful repo context inspectable.",
    tone: "#1F8A4C",
  },
  {
    label: "Language",
    title: "Rules become code",
    body: ".voss captures confidence gates, budgets, routing, and fallbacks as durable workflow semantics.",
    tone: "#C58A0F",
  },
] as const;

export default function FeatureGrid() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-6 lg:grid-cols-[0.78fr_1.22fr] lg:items-end">
          <h2 className="display text-4xl sm:text-5xl">The harness proves the loop.</h2>
          <p className="max-w-3xl text-lg leading-8 text-[var(--muted)] lg:justify-self-end">
            Voss makes the risky parts of AI-assisted repo work explicit: scope, modes, memory,
            tools, and language rules that outlive one chat.
          </p>
        </div>

        <Stagger className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {controls.map((f) => (
            <StaggerItem
              key={f.label}
              style={{ "--card-tone": f.tone } as CSSProperties}
              className="rounded-xl border border-[color-mix(in_oklab,var(--card-tone)_34%,var(--border))] bg-[color-mix(in_oklab,var(--card-tone)_18%,var(--surface))] p-6 transition hover:border-[color-mix(in_oklab,var(--card-tone)_72%,var(--border))] hover:bg-[color-mix(in_oklab,var(--card-tone)_23%,var(--surface))]"
            >
              <div className="inline-flex w-fit rounded-md border border-[color-mix(in_oklab,var(--card-tone)_34%,var(--border))] bg-[color-mix(in_oklab,var(--card-tone)_10%,var(--background))] px-2 py-1 font-mono text-xs text-[var(--card-tone)]">
                {f.label}
              </div>
              <div className="mt-5">
                <h3 className="text-lg font-medium">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{f.body}</p>
              </div>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}

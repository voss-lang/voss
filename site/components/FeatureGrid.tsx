import type { CSSProperties } from "react";

import { primitives } from "@/lib/site";
import { Stagger, StaggerItem } from "./Reveal";

export default function FeatureGrid() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-6 lg:grid-cols-[0.82fr_1.18fr] lg:items-end">
          <h2 className="display text-4xl sm:text-5xl">Six primitives, one org.</h2>
          <p className="max-w-3xl text-lg leading-8 text-[var(--muted)] lg:justify-self-end">
            Voss models software work like a high-performing engineering organization — not a rigid
            automation pipeline. Every run is built from the same six primitives.
          </p>
        </div>

        <Stagger className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {primitives.map((f) => (
            <StaggerItem
              key={f.name}
              style={{ "--card-tone": f.tone } as CSSProperties}
              className="rounded-xl border border-[color-mix(in_oklab,var(--card-tone)_34%,var(--border))] bg-[color-mix(in_oklab,var(--card-tone)_18%,var(--surface))] p-6 transition hover:border-[color-mix(in_oklab,var(--card-tone)_72%,var(--border))] hover:bg-[color-mix(in_oklab,var(--card-tone)_23%,var(--surface))]"
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-lg font-medium">{f.name}</h3>
                <div className="inline-flex w-fit rounded-md border border-[color-mix(in_oklab,var(--card-tone)_34%,var(--border))] bg-[color-mix(in_oklab,var(--card-tone)_10%,var(--background))] px-2 py-1 font-mono text-xs text-[var(--card-tone)]">
                  {f.label}
                </div>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-[var(--muted)]">{f.body}</p>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}

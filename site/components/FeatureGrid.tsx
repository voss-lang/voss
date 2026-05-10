import { features } from "@/lib/site";
import { Stagger, StaggerItem } from "./Reveal";

export default function FeatureGrid() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-12 max-w-2xl">
          <h2 className="display text-4xl sm:text-5xl">
            Five things every AI app reinvents.<br />
            <span className="em">Plus one.</span>
          </h2>
          <p className="mt-4 text-[var(--muted)]">
            Voss makes them language constructs — checked by the compiler, owned by the runtime,
            written once.
          </p>
        </div>
        <Stagger className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <StaggerItem
              key={f.name}
              className="bg-[var(--surface)] p-6 transition hover:bg-[var(--surface-2)]"
            >
              <div className="mb-3 inline-flex rounded-md border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-mono text-xs text-[var(--accent)]">
                {f.name}
              </div>
              <h3 className="text-lg font-medium">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{f.body}</p>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}

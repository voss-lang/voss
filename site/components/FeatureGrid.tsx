import { Stagger, StaggerItem } from "./Reveal";

const controls = [
  {
    label: "Scope",
    title: "Writes stay bounded",
    body: "Edit mode starts from the path you named and keeps mutation inside explicit project boundaries.",
  },
  {
    label: "Modes",
    title: "Planning and editing are separate",
    body: "Plan, edit, and auto modes make repo mutation a deliberate workflow choice.",
  },
  {
    label: "Memory",
    title: "Context survives the session",
    body: "VOSS.md, project memory, and session records keep useful repo context inspectable.",
  },
  {
    label: "Language",
    title: "Rules become code",
    body: ".voss captures confidence gates, budgets, routing, and fallbacks as durable workflow semantics.",
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
          {controls.map((f, index) => (
            <StaggerItem
              key={f.label}
              className={`rounded-xl border border-[var(--border)] p-6 transition hover:border-[var(--accent)] ${
                index === 0
                  ? "bg-[color-mix(in_oklab,var(--accent)_18%,var(--surface))]"
                  : "bg-[var(--surface)] hover:bg-[var(--surface-2)]"
              }`}
            >
              <div className="inline-flex w-fit rounded-md border border-[var(--border)] bg-[var(--background)] px-2 py-1 font-mono text-xs text-[var(--accent)]">
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

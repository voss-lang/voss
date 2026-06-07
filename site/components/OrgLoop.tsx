import { orgLoop } from "@/lib/site";
import { Stagger, StaggerItem } from "./Reveal";

export default function OrgLoop({
  heading = "One idea in. Audited work out.",
  blurb = "The Engineering Manager loop is the orchestrator: a constrained tech lead that decomposes, delegates, verifies, and integrates — and asks for you only when it matters.",
}: {
  heading?: string;
  blurb?: string;
}) {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-12 max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
            Engineering Manager loop
          </p>
          <h2 className="display mt-3 text-4xl sm:text-5xl">{heading}</h2>
          <p className="mt-4 text-[var(--muted)]">{blurb}</p>
        </div>
        <Stagger className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2 lg:grid-cols-4">
          {orgLoop.map((item) => (
            <StaggerItem key={item.step} className="bg-[var(--surface)] p-6">
              <span className="font-mono text-sm text-[var(--accent)]">{item.step}</span>
              <h3 className="mt-4 text-lg font-medium">{item.title}</h3>
              <p className="mt-2 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
            </StaggerItem>
          ))}
        </Stagger>
      </div>
    </section>
  );
}

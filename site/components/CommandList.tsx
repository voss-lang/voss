import { cliCommands } from "@/lib/site";

export default function CommandList() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="mb-10 max-w-2xl">
          <h2 className="display text-4xl sm:text-5xl">
            The <span className="em">CLI</span>.
          </h2>
          <p className="mt-4 text-[var(--muted)]">
            One binary. Compiler verbs and agent verbs share a namespace, so you stay in flow whether
            you&apos;re shipping a program or asking it questions.
          </p>
        </div>
        <ul className="grid gap-3 font-mono text-sm sm:grid-cols-2 lg:grid-cols-3">
          {cliCommands.map((c) => (
            <li
              key={c.cmd}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-5 py-4 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
            >
              <span className="block text-[var(--foreground)]">
                <span className="text-[var(--accent)]">$ </span>
                {c.cmd}
              </span>
              <span className="mt-2 block text-xs leading-5 text-[var(--muted)]">{c.desc}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

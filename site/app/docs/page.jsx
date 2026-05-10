import Link from "next/link";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const PLANNED_SECTIONS = [
  {
    title: "Getting Started",
    body: "Install, scaffold a project, run your first Voss program.",
  },
  {
    title: "Language Reference",
    body: "probable<T>, ctx blocks, semantic match, agents, spawn/gather, fallback.",
  },
  {
    title: "CLI",
    body: "compile, run, check, init, do, chat, doctor — and the bare REPL.",
  },
  {
    title: "Runtime API",
    body: "ContextScope, ProbableValue, SemanticMatcher, VossAgent, providers.",
  },
  {
    title: "Examples",
    body: "Classification, semantic routing, parallel research swarms.",
  },
  {
    title: "Migration from Python",
    body: "Patterns for porting hand-written asyncio + LLM SDK code into Voss.",
  },
];

export const metadata = {
  title: "Docs — Voss",
  description: "Voss documentation (in progress).",
};

export default function DocsPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-4xl px-6 pt-24 pb-12">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
              Documentation
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
              Docs are in progress.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-[var(--muted)]">
              Voss is in active development. The pages below are planned for v1. In the meantime,
              the{" "}
              <Link
                href="https://github.com/your-org/voss/blob/main/PRD.md"
                className="text-[var(--foreground)] underline decoration-[var(--accent)] underline-offset-4"
                target="_blank"
                rel="noreferrer"
              >
                PRD
              </Link>{" "}
              is the canonical reference.
            </p>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-4xl px-6 py-16">
            <ol className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2">
              {PLANNED_SECTIONS.map((s, i) => (
                <li
                  key={s.title}
                  className="bg-[var(--surface)] p-6 transition hover:bg-[var(--surface-2)]"
                >
                  <div className="flex items-baseline gap-3">
                    <span className="font-mono text-xs text-[var(--muted)]">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <h2 className="text-lg font-medium">{s.title}</h2>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{s.body}</p>
                  <p className="mt-3 inline-block rounded border border-[var(--border)] bg-[var(--background)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]">
                    Coming soon
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

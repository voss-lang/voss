import Link from "next/link";
import { Blocks, GitBranch, Layers3, ShieldCheck, TerminalSquare, Workflow } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import TrackedOutboundLink from "@/components/TrackedOutboundLink";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `About - ${site.name}`,
  description:
    "About Voss: a local-first harness and workflow-control language for bounded AI agent work.",
  path: "/about",
});

const PILLARS = [
  {
    title: "Local-first harness",
    body: "Voss runs from the developer's machine, keeps provider credentials local, and treats shell/file access as explicit permission surfaces.",
    icon: TerminalSquare,
  },
  {
    title: "Engineering org loop",
    body: "The orchestration layer models work as tickets, reviewers, audits, and handoffs instead of a single agent improvising in a repo.",
    icon: Workflow,
  },
  {
    title: ".voss control language",
    body: "Project instructions, roles, budgets, principles, and gates are declared in source-controlled workflow files.",
    icon: Blocks,
  },
  {
    title: "Replayable evidence",
    body: "Plans, diffs, tests, review verdicts, blocked work, and residual risk are kept in the run trail so claims can be checked.",
    icon: ShieldCheck,
  },
] as const;

const NOT_NOW = [
  "A hosted SaaS control plane",
  "A replacement for Python or TypeScript",
  "An unsupervised production deploy system",
  "A way to hide model uncertainty behind workflow language",
] as const;

export default function AboutPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-24">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              About
            </Badge>
            <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
              Local agent work needs <span className="em">engineering shape</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              Voss is an open-source CLI, harness, and workflow-control language for developers who
              want AI agents to work inside visible scope, budget, review, and audit boundaries.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/harness">
                  <TerminalSquare />
                  Harness
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <TrackedOutboundLink href={site.repoUrl} analyticsTarget="github">
                  <GitBranch />
                  Source
                </TrackedOutboundLink>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-10 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Product shape
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Four pieces, one boundary model.
              </h2>
            </div>
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2">
              {PILLARS.map((pillar) => {
                const Icon = pillar.icon;
                return (
                  <article key={pillar.title} className="bg-[var(--surface)] p-6">
                    <Icon className="h-6 w-6 text-[var(--accent)]" />
                    <h3 className="mt-5 text-xl font-semibold tracking-tight">{pillar.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{pillar.body}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-[1fr_0.75fr]">
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Intent
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Keep automation inspectable.
              </h2>
              <p className="mt-5 max-w-2xl leading-8 text-[var(--muted)]">
                Voss is built around a simple premise: an agent can be useful only when its
                authority is legible. The product keeps the human-facing parts of engineering work
                intact - plans, scopes, budgets, reviewers, tests, and sign-off - then gives agents
                a runtime that respects those boundaries.
              </p>
              <div className="mt-8">
                <Button asChild variant="outline" size="lg">
                  <Link href="/orchestration">
                    <Layers3 />
                    See orchestration
                  </Link>
                </Button>
              </div>
            </div>
            <aside className="h-fit rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <h2 className="font-mono text-sm uppercase tracking-widest">Not positioned as</h2>
              <ul className="mt-6 space-y-4">
                {NOT_NOW.map((item) => (
                  <li key={item} className="text-sm leading-7 text-[var(--muted)]">
                    {item}
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

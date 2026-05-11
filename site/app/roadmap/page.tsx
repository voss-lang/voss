import type { Metadata } from "next";
import Link from "next/link";
import { CheckCircle2, Milestone, Route } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Roadmap — ${site.name}`,
  description: "The current Voss roadmap from harness-led MVP to language/compiler maturity.",
};

const ROADMAP = [
  {
    phase: "Now",
    title: "Harness-led v0.1",
    status: "In progress",
    body: "Make the coding harness useful end-to-end: auth, sessions, permissions, tools, recorder, and reliable project cognition.",
  },
  {
    phase: "Next",
    title: "Voss-authored harness loop",
    status: "Planned",
    body: "Use Voss itself as the workflow control layer for planning, tool calls, validation, and agent memory.",
  },
  {
    phase: "Then",
    title: "Language reference and examples",
    status: "Planned",
    body: "Stabilize syntax for the core constructs and publish realistic examples that compile to readable Python.",
  },
  {
    phase: "Later",
    title: "Distribution and launch",
    status: "Deferred",
    body: "Package binaries, Homebrew, docs, and OSS launch material after the harness and language surface are credible.",
  },
] as const;

const NOT_NOW = [
  "Hosted SaaS control plane",
  "Pricing or accounts",
  "Marketplace integrations",
  "General-purpose workflow engine",
] as const;

export default function RoadmapPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              Roadmap
            </Badge>
            <h1 className="display mt-5 max-w-4xl text-5xl sm:text-7xl">
              Build the harness, then <span className="em">prove the language</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              Voss is pre-release. The current roadmap prioritizes a useful local coding harness,
              then folds the same control loop back into the Voss language.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/harness">See harness</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="/language">Language overview</Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-[1fr_0.75fr]">
            <div className="space-y-4">
              {ROADMAP.map((item) => (
                <article key={item.title} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--accent)]">
                      <Milestone className="h-5 w-5" />
                    </span>
                    <span className="font-mono text-xs uppercase tracking-widest text-[var(--muted)]">
                      {item.phase}
                    </span>
                    <Badge variant={item.status === "In progress" ? "default" : "secondary"}>{item.status}</Badge>
                  </div>
                  <h2 className="mt-5 text-2xl font-semibold tracking-tight">{item.title}</h2>
                  <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                </article>
              ))}
            </div>
            <aside className="h-fit rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <div className="flex items-center gap-3">
                <Route className="h-5 w-5 text-[var(--accent)]" />
                <h2 className="font-mono text-sm uppercase tracking-widest">Not now</h2>
              </div>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                The roadmap is intentionally narrow. These are deferred until the local developer
                loop and language constructs are solid.
              </p>
              <ul className="mt-6 space-y-4">
                {NOT_NOW.map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-[var(--muted)]">
                    <CheckCircle2 className="h-4 w-4 text-[var(--accent)]" />
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

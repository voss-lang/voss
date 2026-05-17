import type { Metadata } from "next";
import Link from "next/link";
import { Ban, PackageCheck, Milestone, Route, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Roadmap — ${site.name}`,
  description: "The current Voss roadmap from the v0.1 harness to TUI, memory, and codebase intelligence.",
};

const ROADMAP: {
  phase: string;
  title: string;
  status: string;
  body: string;
  icon: LucideIcon;
}[] = [
  {
    phase: "Shipped",
    title: "Harness-led v0.1",
    status: "Built",
    body: "The Python harness, .voss language path, project cognition, evals, npm wrapper, SDK polish, and project memory foundation are in place.",
    icon: PackageCheck,
  },
  {
    phase: "Now",
    title: "TUI shell",
    status: "Final verify",
    body: "Replace line-streamed chat with a Textual interface for turn history, slash commands, permission modals, budget views, and session forking.",
    icon: Milestone,
  },
  {
    phase: "Next",
    title: "Codebase intelligence",
    status: "Planned",
    body: "Add a project index, LSP-backed symbol lookup, structural search, code_search/find_definition/find_references tools, and a TUI code panel.",
    icon: Route,
  },
  {
    phase: "Later",
    title: "Agent capability surface",
    status: "Sequenced",
    body: "Layer in Voss-aware tools, MCP bridge, multi-agent chat, long-running watch tasks, and a signed skill/plugin marketplace.",
    icon: Workflow,
  },
];

const NOT_NOW = [
  "Hosted SaaS control plane",
  "Pricing or accounts",
  "Unsigned third-party plugins",
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
            <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
              Ship the harness, then <span className="em">raise the ceiling</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              Voss is early developer tooling. The roadmap now extends the local harness with a
              full-screen TUI, persistent memory, codebase intelligence, and language-aware tools.
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
              {ROADMAP.map((item) => {
                const Icon = item.icon;
                return (
                <article key={item.title} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--background)] text-[var(--accent)]">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="font-mono text-xs uppercase tracking-widest text-[var(--muted)]">
                      {item.phase}
                    </span>
                    <Badge variant={item.status === "Final verify" ? "default" : "secondary"}>{item.status}</Badge>
                  </div>
                  <h2 className="mt-5 text-2xl font-semibold tracking-tight">{item.title}</h2>
                  <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                </article>
                );
              })}
            </div>
            <aside className="h-fit rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <div className="flex items-center gap-3">
                <Route className="h-5 w-5 text-[var(--accent)]" />
                <h2 className="font-mono text-sm uppercase tracking-widest">Not now</h2>
              </div>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                The roadmap stays local-first. These stay deferred while the repo loop, memory,
                TUI, and code intelligence mature.
              </p>
              <ul className="mt-6 space-y-4">
                {NOT_NOW.map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-[var(--muted)]">
                    <Ban className="h-4 w-4 shrink-0 text-[var(--muted)]" />
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

import Link from "next/link";
import { Ban, PackageCheck, Milestone, Route, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Roadmap - ${site.name}`,
  description:
    "The Voss roadmap: from the bounded harness substrate to a full agent engineering organization layer — board, reviewers, EM loop, audit, and ADE.",
  path: "/roadmap",
});

const ROADMAP: {
  phase: string;
  title: string;
  status: string;
  body: string;
  icon: LucideIcon;
}[] = [
  {
    phase: "Shipped",
    title: "The engineering org core",
    status: "Built",
    body: "Session tree + budget fan-out, the board state machine, the Reviewer-A/B split, and the Engineering Manager loop. `voss team run`, `voss board`, and `voss review` compose them into one run.",
    icon: PackageCheck,
  },
  {
    phase: "Shipped",
    title: "Bounded harness substrate",
    status: "Built",
    body: "Plan/edit/auto modes, scoped writes, project memory, resumable sessions, the .voss control language, and the capability + principles layers the org runs on top of.",
    icon: PackageCheck,
  },
  {
    phase: "Now",
    title: "Multi-agent chat + live steering",
    status: "Building",
    body: "Non-blocking spawn, status, gather, and steer inside `voss chat` and the ADE. Child budget is drawn from the parent, the recursive budget invariant holds, and panels stay quiet by default.",
    icon: Milestone,
  },
  {
    phase: "Next",
    title: "Audit product + ADE panels",
    status: "Planned",
    body: "Render the audit as a navigable session tree, with board, roster, reviewer-verdict, budget, and scope panels, blocked-card decision flows, and full run replay.",
    icon: Route,
  },
  {
    phase: "Later",
    title: "Language as coordination spec",
    status: "Sequenced",
    body: "Stabilize the grammar for principles, team, role, gate, board, review, and memory, with compiler diagnostics clear enough for non-CS users and `voss run <file.voss>` for declared workflows.",
    icon: Workflow,
  },
];

const NOT_NOW = [
  "Hosted SaaS control plane",
  "Distributed multi-machine agent swarms",
  "Autonomous deploy / delete / money without sign-off",
  "Voss as a general-purpose programming language",
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
              From bounded harness to <span className="em">engineering org</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              The org core is in: session tree, board, independent review, and the Engineering
              Manager loop. From here, the work is live steering, the audit-centered ADE, and a
              stable coordination language — kept local-first the whole way.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/orchestration">See orchestration</Link>
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
                    <Badge variant={item.status === "Built" ? "default" : "secondary"}>{item.status}</Badge>
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

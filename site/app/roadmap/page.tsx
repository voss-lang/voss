import Link from "next/link";
import { Ban, FileText, MessagesSquare, Milestone, PackageCheck, Route, Workflow } from "lucide-react";
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
    "The Voss roadmap: live workspace verification, managed project instructions, semantic code recall, budget-aware context, and global memory.",
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
    title: "Bounded harness + engineering org core",
    status: "Built",
    body: "The CLI harness, scoped tools, project memory, sessions, team roles, board, independent review, and run audit are the current product foundation.",
    icon: PackageCheck,
  },
  {
    phase: "Preview",
    title: "Live desktop workspace",
    status: "In verification",
    body: "The desktop path is moving from a terminal grid into a live local workspace: structured run views, inline approvals, reconnectable recent work, and honest lifecycle states.",
    icon: Milestone,
  },
  {
    phase: "Shipped",
    title: "Managed project instructions",
    status: "Built",
    body: "voss sync writes generated workflow docs, managed instruction sections, and editable review prompts, with a check mode for CI drift and hand-edited managed docs.",
    icon: FileText,
  },
  {
    phase: "Shipped",
    title: "Semantic code recall",
    status: "Built",
    body: "voss recall and the code_recall tool search code and project memory together, label results by source, and degrade to lexical recall when vector search is unavailable.",
    icon: Route,
  },
  {
    phase: "Shipped",
    title: "Budget-aware context",
    status: "Built",
    body: "Long-running harness work now keeps recent context full, compresses older replay into structural summaries, and reports estimated savings from a session ledger.",
    icon: Workflow,
  },
  {
    phase: "Next",
    title: "External-agent handoffs",
    status: "Planned",
    body: "Adopted tools and external CLI agents should coordinate through clear ownership, identity, and handoff signals without pretending Voss fully controls tools it did not launch.",
    icon: MessagesSquare,
  },
  {
    phase: "Later",
    title: "Global and external memory",
    status: "Sequenced",
    body: "The next memory work is curated cross-project recall first, then explicit read-only ingest for markdown docs and external memory directories.",
    icon: FileText,
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
              From bounded harness to <span className="em">live agent workspace</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              The org core is in: scoped tools, sessions, board, independent review, and replayable
              audit. Recent work added managed project instructions, code-aware recall, and
              budget-aware context. From here, the work is live local supervision, external-agent
              handoffs, and memory that can cross projects without leaving local control.
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
                The roadmap stays local-first. These stay deferred while the live workspace,
                global memory, and external-agent coordination mature.
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

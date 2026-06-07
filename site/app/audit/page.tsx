import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  FileJson,
  GitCompare,
  ScanSearch,
  ShieldAlert,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { auditSections, site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Audit - ${site.name}`,
  description:
    "The Voss audit is the primary trust product: a replayable, deterministic trail of every action, decision, and gate outcome — with EM claims separated from verified evidence.",
};

const ANSWERS: { title: string; body: string; icon: LucideIcon }[] = [
  {
    title: "What actually changed",
    body: "Diff summary, agent actions, and tests per card — understandable without reading raw logs.",
    icon: GitCompare,
  },
  {
    title: "Claims vs. evidence",
    body: "The audit separates what the EM said from what was independently verified. Unsupported claims are detectable.",
    icon: ScanSearch,
  },
  {
    title: "Why it passed — or didn't",
    body: "Reviewer-A verification and Reviewer-B verdict are recorded separately, linked to files, tests, and eval output.",
    icon: Workflow,
  },
  {
    title: "What's still risky",
    body: "Every run ends with a residual-risk section and the blocked, killed, and rescoped lineage.",
    icon: ShieldAlert,
  },
];

export default function AuditPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20">
            <Reveal>
              <Badge variant="secondary" className="font-mono uppercase tracking-wider">
                Audit
              </Badge>
            </Reveal>
            <Reveal delay={0.05}>
              <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
                The audit is the <span className="em">trust product</span>.
              </h1>
            </Reveal>
            <Reveal delay={0.1}>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
                A multi-agent run is only useful if you can trust the result. Voss makes the audit
                trail the center of the product: a replayable, deterministic record of every action,
                decision, and gate outcome — good enough to review a PR from.
              </p>
            </Reveal>
            <Reveal delay={0.15}>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-mono text-sm">
                  <span className="text-[var(--accent)]">$</span>
                  <span className="select-all">voss audit &lt;run_id&gt;</span>
                </div>
                <Button asChild variant="outline" size="lg">
                  <Link href="/orchestration">
                    How runs work
                    <ArrowRight />
                  </Link>
                </Button>
              </div>
            </Reveal>
          </div>
        </section>

        {/* What it answers */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                What it answers
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Understand a run <span className="em">without the logs</span>.
              </h2>
            </div>
            <Stagger className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2">
              {ANSWERS.map((item) => {
                const Icon = item.icon;
                return (
                  <StaggerItem key={item.title} className="bg-[var(--surface)] p-6">
                    <Icon className="h-6 w-6 text-[var(--accent)]" />
                    <h3 className="mt-5 text-xl font-medium">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                  </StaggerItem>
                );
              })}
            </Stagger>
          </div>
        </section>

        {/* The 15 sections */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                The report
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Fifteen sections, <span className="em">one trail</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Every audit is deterministic from persisted run data and exports to Markdown and
                JSON. In the ADE it renders as a navigable session tree.
              </p>
            </div>
            <Stagger className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {auditSections.map((s) => (
                <StaggerItem
                  key={s.n}
                  className="flex items-center gap-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-5 py-4 transition hover:border-[var(--accent)]"
                >
                  <span className="font-mono text-sm text-[var(--accent)]">{s.n}</span>
                  <span className="text-sm text-[var(--foreground)]">{s.title}</span>
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </section>

        {/* Export + CTA */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 sm:p-12">
              <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
                <div>
                  <FileJson className="h-6 w-6 text-[var(--accent)]" />
                  <h2 className="display mt-5 text-4xl sm:text-5xl">
                    Built for <span className="em">review and replay</span>.
                  </h2>
                  <p className="mt-4 text-[var(--muted)]">
                    Use the audit to review a multi-agent run like a PR, to detect unsupported
                    claims, or to replay exactly what happened. Budget allocation and consumption are
                    shown per node, alongside scope violations and denied attempts.
                  </p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <Button asChild size="lg">
                      <Link href="/orchestration">
                        See orchestration
                        <ArrowRight />
                      </Link>
                    </Button>
                    <Button asChild variant="outline" size="lg">
                      <Link href={site.docsUrl} target="_blank" rel="noreferrer">
                        Audit docs
                      </Link>
                    </Button>
                  </div>
                </div>
                <ul className="grid gap-3 font-mono text-sm">
                  {[
                    { cmd: "voss audit <run_id>", desc: "Full replayable report" },
                    { cmd: "voss audit latest", desc: "Most recent run" },
                    { cmd: "voss review <run_id>", desc: "Reviewer-A + Reviewer-B output" },
                    { cmd: "voss board", desc: "Live card state" },
                  ].map((c) => (
                    <li
                      key={c.cmd}
                      className="rounded-xl border border-[var(--border)] bg-[var(--background)] px-5 py-4"
                    >
                      <span className="block text-[var(--foreground)]">
                        <span className="text-[var(--accent)]">$ </span>
                        {c.cmd}
                      </span>
                      <span className="mt-2 block text-xs leading-5 text-[var(--muted)]">
                        {c.desc}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

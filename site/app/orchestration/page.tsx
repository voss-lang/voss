import Link from "next/link";
import { codeToHtml } from "shiki";
import {
  ArrowRight,
  GitBranch,
  KanbanSquare,
  Scale,
  ScrollText,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import OrgLoop from "@/components/OrgLoop";
import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { orgInvariants, site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Orchestration - ${site.name}`,
  description:
    "Voss orchestrates AI agents as a constrained engineering organization: a board, a session tree, declared roles, an Engineering Manager loop, and independent review.",
  path: "/orchestration",
});

const BOARD_COLUMNS = [
  { name: "Backlog", body: "Raw ideas, not yet scoped." },
  { name: "Planned", body: "EM has authored acceptance criteria + role." },
  { name: "InProgress", body: "Scope and budget allocated; worker running." },
  { name: "InReview", body: "Artifact exists; awaiting independent review." },
  { name: "Blocked", body: "Timeout, budget, scope error, or reviewer block." },
  { name: "Done", body: "Tests pass and independent review passed." },
];

const GATES: { from: string; to: string; gate: string }[] = [
  { from: "Backlog", to: "Planned", gate: "EM creates acceptance criteria + role assignment" },
  { from: "Planned", to: "InProgress", gate: "Scope and budget allocated" },
  { from: "InProgress", to: "InReview", gate: "Artifact exists" },
  { from: "InReview", to: "Done", gate: "Tests/evals pass AND independent review passes" },
  { from: "Any", to: "Blocked", gate: "Timeout, budget, scope error, reviewer block, or human decision" },
  { from: "Blocked", to: "Planned", gate: "EM rescope or human approval" },
];

const PILLARS: { title: string; body: string; icon: LucideIcon; href: string }[] = [
  {
    title: "Engineering Manager loop",
    body: "A constrained tech lead. It can decompose, assign, and integrate — but cannot invent roles, widen scope, or raise budget.",
    icon: Users,
    href: "#em",
  },
  {
    title: "Board state machine",
    body: "Orchestration is a visible board, not an invisible prompt loop. Cards advance only through artifact-gated transitions.",
    icon: KanbanSquare,
    href: "#board",
  },
  {
    title: "Reviewer A/B split",
    body: "Verification is independent. Reviewer-A authors the bar from your idea; Reviewer-B judges narrative-blind.",
    icon: ShieldCheck,
    href: "#review",
  },
  {
    title: "Session tree + budget fan-out",
    body: "Every agent is a durable node with its own budget and scope. No child can overspend its parent.",
    icon: GitBranch,
    href: "#tree",
  },
];

const TEAM_SAMPLE = `team "default" {
  ceiling {
    budget: 120000 tokens
    scope: ["src/**", "tests/**", "docs/**"]
    latency: 30m
  }

  principles {
    diff: "Smallest diff that solves it"
    evidence: "No claim without evidence"
  }

  role architect {
    model: "strong"
    mode:  "plan"
    scope: ["src/**", "docs/**"]
    tools: ["fs", "code", "git"]
    budget: 12000 tokens
  }

  role backend {
    model: "cheap"
    mode:  "edit"
    scope: ["src/server/**", "tests/server/**"]
    tools: ["fs", "code", "test", "git"]
    budget: 24000 tokens
  }

  role reviewer {
    model: "strong"
    mode:  "plan"
    scope: ["src/**", "tests/**"]
    tools: ["fs", "code", "test", "git"]
    budget: 16000 tokens
  }
}`;

export default async function OrchestrationPage() {
  const teamHtml = await codeToHtml(TEAM_SAMPLE.trimEnd(), {
    lang: "python",
    theme: "github-dark-default",
  });

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
                Orchestration
              </Badge>
            </Reveal>
            <Reveal delay={0.05}>
              <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
                A controlled AI engineering <span className="em">organization</span>.
              </h1>
            </Reveal>
            <Reveal delay={0.1}>
              <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
                Most AI coding tools optimize one agent writing code faster. Voss optimizes verified
                parallel engineering: multiple agents, declared roles, independent review, hard
                budgets, scoped tools, and a replayable audit.
              </p>
            </Reveal>
            <Reveal delay={0.15}>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link href="/audit">
                    See the audit
                    <ScrollText />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href={site.docsUrl} target="_blank" rel="noreferrer">
                    Read docs
                    <ArrowRight />
                  </Link>
                </Button>
              </div>
            </Reveal>
          </div>
        </section>

        {/* Pillars */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <Stagger className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] md:grid-cols-2">
              {PILLARS.map((item) => {
                const Icon = item.icon;
                return (
                  <StaggerItem key={item.title} className="bg-[var(--surface)] p-6">
                    <a href={item.href} className="group block">
                      <Icon className="h-6 w-6 text-[var(--accent)]" />
                      <h3 className="mt-5 text-xl font-medium group-hover:text-[var(--accent)]">
                        {item.title}
                      </h3>
                      <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                    </a>
                  </StaggerItem>
                );
              })}
            </Stagger>
          </div>
        </section>

        {/* EM loop */}
        <div id="em" className="scroll-mt-20">
          <OrgLoop />
        </div>

        {/* Roles + team config */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Roles
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                A roster, declared in <span className="em">.voss</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                The default roster ships with architect, backend, frontend, tester, reviewer,
                skeptic, and docs. Each role carries its own scope, budget, tool subset, and model
                tier. The EM can only dispatch to declared roles — and{" "}
                <code className="font-mono text-[var(--foreground)]">voss team check</code> fails
                the build if a role widens scope or names an unknown capability.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild variant="outline" size="lg">
                  <Link href="/language">Coordination language</Link>
                </Button>
              </div>
            </div>
            <div
              className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 font-mono text-sm leading-7 [&_pre]:!bg-transparent [&_pre]:text-xs [&_pre]:leading-6 sm:[&_pre]:text-sm"
              dangerouslySetInnerHTML={{ __html: teamHtml }}
            />
          </div>
        </section>

        {/* Board */}
        <section id="board" className="scroll-mt-20 border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Board
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Orchestration you can <span className="em">watch</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Work moves across a board with WIP limits and transition gates. Agents cannot mark
                their own work Done. Every blocked card carries a reason.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {BOARD_COLUMNS.map((col) => (
                <article
                  key={col.name}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <h3 className="font-mono text-sm text-[var(--accent)]">{col.name}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{col.body}</p>
                </article>
              ))}
            </div>
            <div className="mt-10 overflow-hidden rounded-xl border border-[var(--border)]">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-[var(--surface-2)] font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
                  <tr>
                    <th className="px-4 py-3">From</th>
                    <th className="px-4 py-3">To</th>
                    <th className="px-4 py-3">Gate</th>
                  </tr>
                </thead>
                <tbody>
                  {GATES.map((g) => (
                    <tr key={`${g.from}-${g.to}`} className="border-t border-[var(--border)] bg-[var(--surface)]">
                      <td className="px-4 py-3 font-mono text-xs text-[var(--foreground)]">{g.from}</td>
                      <td className="px-4 py-3 font-mono text-xs text-[var(--accent)]">{g.to}</td>
                      <td className="px-4 py-3 text-[var(--muted)]">{g.gate}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Review + tree */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-px overflow-hidden border-y border-[var(--border)] bg-[var(--border)] lg:grid-cols-2">
            <div id="review" className="scroll-mt-20 bg-[var(--surface)] p-8 sm:p-12">
              <Scale className="h-6 w-6 text-[var(--accent)]" />
              <h2 className="display mt-5 text-3xl sm:text-4xl">
                Independent <span className="em">review</span>.
              </h2>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Reviewer-A derives the verification bar from your original idea — not the EM&apos;s
                acceptance criteria — and authors the tests, evals, or checklist. Worker agents
                cannot author their own final gate.
              </p>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Reviewer-B judges the artifact, diff, and tests narrative-blind, and can fail work
                when Reviewer-A&apos;s verification has drifted from the original idea. Verdicts
                carry confidence, evidence references, and an inferred domain.
              </p>
              <Button asChild variant="outline" className="mt-6">
                <Link href="/audit">Reviewer verdicts in the audit</Link>
              </Button>
            </div>
            <div id="tree" className="scroll-mt-20 bg-[var(--surface)] p-8 sm:p-12">
              <GitBranch className="h-6 w-6 text-[var(--accent)]" />
              <h2 className="display mt-5 text-3xl sm:text-4xl">
                Session tree + <span className="em">budget fan-out</span>.
              </h2>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Every agent and subagent is a first-class recorded node with its own budget, scope,
                status, and artifacts. The invariant is hard:{" "}
                <code className="font-mono text-[var(--foreground)]">
                  sum(child budgets) + reserve ≤ parent budget
                </code>
                .
              </p>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Budget is treated as a security boundary, not telemetry. Rejected budget-raise
                attempts are recorded, and failed, killed, or timed-out children still reach a
                terminal state — so a run reconstructs without reading the chat transcript.
              </p>
              <Button asChild variant="outline" className="mt-6">
                <Link href={site.docsUrl} target="_blank" rel="noreferrer">
                  Session tree docs
                </Link>
              </Button>
            </div>
          </div>
        </section>

        {/* Invariants */}
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                The cage
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                What the orchestrator <span className="em">cannot</span> do.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                Autonomy is bounded by invariants the runtime enforces — not by trust in the model.
              </p>
            </div>
            <Stagger className="grid gap-3 sm:grid-cols-2">
              {orgInvariants.map((inv) => (
                <StaggerItem
                  key={inv}
                  className="flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--foreground)]"
                >
                  <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-[var(--accent)]" />
                  {inv}
                </StaggerItem>
              ))}
            </Stagger>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

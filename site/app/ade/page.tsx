import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  BrainCircuit,
  Code2,
  Gauge,
  GitBranch,
  KanbanSquare,
  Layers3,
  Monitor,
  Network,
  Scale,
  ScrollText,
  ShieldCheck,
  SquareTerminal,
  TerminalSquare,
  Users,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import ProductScreenshot from "@/components/ProductScreenshot";
import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Agentic Development Environment - ${site.name}`,
  description:
    "Voss ADE is a separate macOS desktop app built on Voss: agent terminals, notes, and managed Voss tasks on one canvas, connected to the engine through voss serve.",
  path: "/ade",
});

const WHY_ADE: { title: string; body: string; icon: LucideIcon }[] = [
  {
    title: "Stateful workspaces",
    body: "Keep agent terminals, notes, sessions, and task history tied to the repo. Shells run in tmux, so they survive an app quit.",
    icon: Boxes,
  },
  {
    title: "Inspectable execution",
    body: "Review task graphs, worker attempts, diffs, output, and acceptance evidence before they become opaque history.",
    icon: BrainCircuit,
  },
  {
    title: "Governed capabilities",
    body: "Managed tasks run on subscription OAuth only, with an isolated login per CLI process, explicit modes, and permission gates.",
    icon: ShieldCheck,
  },
];

const STACK: { name: string; desc: string; icon: LucideIcon }[] = [
  { name: "CLI", desc: "Scriptable one-shot and repo commands.", icon: TerminalSquare },
  { name: "TUI", desc: "Full-screen Go client for turns, approvals, and inspection.", icon: SquareTerminal },
  { name: "Voss ADE", desc: "macOS canvas for agent terminals and managed tasks.", icon: Monitor },
  { name: "MCP Server", desc: "Expose Voss tools to agent clients over stdio.", icon: Network },
  { name: "Code Intelligence", desc: "Code index, symbols, references, and recall.", icon: Code2 },
  { name: "Voss Tools", desc: "Diff, inspect, lint, and budget helpers.", icon: Wrench },
  { name: "voss serve + SDKs", desc: "Local REST + SSE API with Go, Rust, and TypeScript clients.", icon: Layers3 },
];

const LIVE_PREVIEW: { title: string; body: string; icon: LucideIcon }[] = [
  {
    title: "Preview before Start",
    body: "An objective, PRD, or issue becomes a task graph with dependencies, file lists, and acceptance criteria. Start runs only the exact revision you accepted.",
    icon: ScrollText,
  },
  {
    title: "Inline approvals",
    body: "Permission and diff requests appear beside the work, and the engine confirms each reply as applied or stale.",
    icon: ShieldCheck,
  },
  {
    title: "Durable task state",
    body: "Task state and events are journaled on disk. ADE replays from its last cursor after a restart, and unfinished work shows as interrupted instead of relaunching.",
    icon: GitBranch,
  },
  {
    title: "Honest run states",
    body: "Active, waiting, candidate ready, failed, and interrupted come from the engine. Candidate ready means waiting for review, not merged.",
    icon: Gauge,
  },
];

const PANELS: { name: string; desc: string; icon: LucideIcon }[] = [
  { name: "Worker attempts", desc: "Each attempt with its harness, model, branch, and output.", icon: Users },
  { name: "Review queue", desc: "Approve candidates tied to an exact recorded attempt.", icon: KanbanSquare },
  { name: "Task graph", desc: "Nodes, dependencies, and blockers, live.", icon: GitBranch },
  { name: "Acceptance evidence", desc: "The diff, checks, and criteria behind each review.", icon: Scale },
  { name: "OAuth availability", desc: "Which harnesses are signed in before you start.", icon: Gauge },
  { name: "Task replay", desc: "The run rebuilt from the engine's journal.", icon: ScrollText },
];

const WORKFLOW = [
  {
    step: "Preview",
    body: "Turn a briefing into a task graph with scope, file lists, and acceptance criteria.",
  },
  {
    step: "Start",
    body: "Accept the exact revision. The engine checks HEAD and the workspace before dispatch.",
  },
  {
    step: "Inspect",
    body: "Follow each node's attempts and output while the work is fresh.",
  },
  {
    step: "Review",
    body: "Approve candidates against recorded acceptance evidence before anything merges.",
  },
];

export default function AdePage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto grid max-w-6xl gap-12 px-6 pt-24 pb-20 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <Reveal>
                <Badge variant="secondary" className="font-mono uppercase tracking-wider">
                  ADE
                </Badge>
              </Reveal>
              <Reveal delay={0.05}>
                <h1 className="display mt-5 text-[clamp(2.5rem,6vw,4.5rem)]">
                  Agentic workspace for<br />
                  <span className="em">coding agents</span>.
                </h1>
              </Reveal>
              <Reveal delay={0.1}>
                <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
                  Voss ADE is a separate desktop app built on Voss. It puts Claude Code and Codex
                  terminals, notes, and managed Voss tasks on one canvas, and talks to the engine
                  only through voss serve and the SDK.
                </p>
              </Reveal>
              <Reveal delay={0.15}>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Button asChild size="lg">
                    <Link href="#download">
                      Setup options
                      <ArrowRight />
                    </Link>
                  </Button>
                  <Button asChild variant="outline" size="lg">
                    <Link href="/harness">
                      Harness details
                      <TerminalSquare />
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
            <Reveal delay={0.1}>
              <ProductScreenshot
                src="/product/voss-tools.png"
                alt="Voss tools output listing read-only and mutating harness tools."
                width={1200}
                height={853}
                priority
                sizes="(min-width: 1024px) 560px, calc(100vw - 48px)"
              />
            </Reveal>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Managed Voss tasks
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Local agent work you can <span className="em">watch and steer</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                ADE runs managed Voss tasks: preview the plan as a task graph, accept the exact
                revision, watch each worker attempt, and approve from a review queue tied to
                recorded acceptance evidence.
              </p>
            </div>
            <Stagger className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {LIVE_PREVIEW.map((item) => {
                const Icon = item.icon;

                return (
                  <StaggerItem
                    key={item.title}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                  >
                    <Icon className="h-6 w-6 text-[var(--accent)]" />
                    <h3 className="mt-5 text-lg font-medium">{item.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.body}</p>
                  </StaggerItem>
                );
              })}
            </Stagger>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Why ADE
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Agents need an <span className="em">environment</span>, not another text box.
              </h2>
            </div>
            <Stagger className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] md:grid-cols-3">
              {WHY_ADE.map((item) => {
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

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Stack
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                The Voss <span className="em">ADE stack</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                ADE owns the desktop: canvas, terminals, panes, and layouts. Voss owns the engine
                underneath: CLI, TUI, harness, protocol, and SDKs.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {STACK.map((item) => {
                const Icon = item.icon;

                return (
                  <article
                    key={item.name}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--accent)]">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 text-lg font-medium">{item.name}</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.desc}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Orchestration panels
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Watch a team work, <span className="em">without the spam</span>.
              </h2>
              <p className="mt-4 text-[var(--muted)]">
                ADE renders what the engine records: the task graph, each worker attempt, and the
                evidence behind every review. Panels stay quiet by default and reveal detail on
                demand.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {PANELS.map((item) => {
                const Icon = item.icon;

                return (
                  <article
                    key={item.name}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--background)] text-[var(--accent)]">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 text-lg font-medium">{item.name}</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.desc}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="mb-12 max-w-2xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Workflow
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Preview, start, inspect, <span className="em">review</span>.
              </h2>
            </div>
            <div className="grid gap-4 md:grid-cols-4">
              {WORKFLOW.map((item) => (
                <article
                  key={item.step}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <h3 className="text-xl font-medium text-[var(--accent)]">{item.step}</h3>
                  <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="download" className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 sm:p-12">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Desktop builds
              </p>
              <div className="mt-3 grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
                <div>
                  <h2 className="display text-4xl sm:text-5xl">
                    Use the CLI today. <span className="em">ADE is in private preview.</span>
                  </h2>
                  <p className="mt-4 text-[var(--muted)]">
                    Voss itself installs from npm. ADE is a separate macOS app for Apple Silicon,
                    developed in its own repository and not yet distributed.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <article className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-5">
                    <h3 className="text-xl font-medium">CLI</h3>
                    <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                      Install with npm or pip and run Voss inside an existing repo.
                    </p>
                    <code className="mt-5 block rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-mono text-sm text-[var(--foreground)]">
                      {site.install.primary}
                    </code>
                  </article>
                  <article className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-5">
                    <h3 className="text-xl font-medium">Voss ADE</h3>
                    <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                      Separate macOS app for agent terminals, managed tasks, and review.
                    </p>
                    <Badge variant="secondary" className="mt-5 font-mono uppercase tracking-wider">
                      Private preview
                    </Badge>
                  </article>
                </div>
              </div>
              <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-6">
                <p className="text-sm text-[var(--muted)]">
                  ADE needs only a released Voss executable. Until it ships, everything runs from
                  the Voss CLI.
                </p>
                <Button asChild variant="outline">
                  <Link href={site.docsUrl} target="_blank" rel="noreferrer">
                    View setup docs
                    <ArrowRight />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

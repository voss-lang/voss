import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  BrainCircuit,
  Code2,
  Download,
  Layers3,
  Monitor,
  Network,
  ShieldCheck,
  SquareTerminal,
  TerminalSquare,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import ProductScreenshot from "@/components/ProductScreenshot";
import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Agentic Development Environment - ${site.name}`,
  description:
    "Voss is a local Agentic Development Environment for running, inspecting, and governing agent work.",
};

const WHY_ADE: { title: string; body: string; icon: LucideIcon }[] = [
  {
    title: "Stateful workspaces",
    body: "Keep sessions, project memory, phase context, and validation artifacts tied to the repo where the work happens.",
    icon: Boxes,
  },
  {
    title: "Inspectable execution",
    body: "Review tool calls, traces, diffs, confidence gates, budget records, and generated artifacts before they become opaque history.",
    icon: BrainCircuit,
  },
  {
    title: "Governed capabilities",
    body: "Expose tools through explicit modes, MCP surfaces, permission gates, and mutation boundaries instead of all-or-nothing automation.",
    icon: ShieldCheck,
  },
];

const STACK: { name: string; desc: string; icon: LucideIcon }[] = [
  { name: "CLI", desc: "Scriptable one-shot and repo commands.", icon: TerminalSquare },
  { name: "TUI", desc: "Interactive turns, modals, and traces.", icon: SquareTerminal },
  { name: "Desktop Shell", desc: "A local app wrapper for the harness.", icon: Monitor },
  { name: "MCP Server", desc: "Expose Voss tools to agent clients.", icon: Network },
  { name: "Code Intelligence", desc: "Repo-aware context and navigation.", icon: Code2 },
  { name: "Voss Tools", desc: "Diff, inspect, lint, and budget helpers.", icon: Wrench },
  { name: "Planning + Validation", desc: "Phase plans, checks, and summaries.", icon: Layers3 },
];

const WORKFLOW = [
  {
    step: "Plan",
    body: "Start with bounded intent, phase context, and read-only analysis before edits.",
  },
  {
    step: "Run",
    body: "Execute tool calls through declared modes and workspace-scoped capabilities.",
  },
  {
    step: "Inspect",
    body: "Open traces, budget records, probable decisions, and Voss diffs while the work is fresh.",
  },
  {
    step: "Ship",
    body: "Close the loop with validation checks, summaries, and PR-ready artifacts.",
  },
];

const DOWNLOADS = [
  {
    platform: "macOS",
    button: "Download .dmg",
    meta: "Apple Silicon + Intel builds planned",
  },
  {
    platform: "Windows",
    button: "Download .exe",
    meta: "Windows 10/11 installer planned",
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
                  Voss gives coding agents a real workspace: tools, memory, permissions, sessions,
                  replay, and inspection surfaces built for software work instead of chat drift.
                </p>
              </Reveal>
              <Reveal delay={0.15}>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Button asChild size="lg">
                    <Link href="#download">
                      Setup options
                      <Download />
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
                height={780}
                priority
              />
            </Reveal>
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
                The marketing page should name the real surfaces users will install and operate,
                from the CLI up through the desktop shell and MCP bridge.
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
                Workflow
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Plan, run, inspect, <span className="em">ship</span>.
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
                Download
              </p>
              <div className="mt-3 grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
                <div>
                  <h2 className="display text-4xl sm:text-5xl">
                    Install the <span className="em">Voss ADE</span>.
                  </h2>
                  <p className="mt-4 text-[var(--muted)]">
                    Desktop builds will package the Voss harness into a local Agentic Development
                    Environment for running, inspecting, and governing agent work from your machine.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {DOWNLOADS.map((item) => (
                    <article
                      key={item.platform}
                      className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-5"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-xl font-medium">{item.platform}</h3>
                        <Badge variant="secondary" className="font-mono uppercase tracking-wider">
                          Coming soon
                        </Badge>
                      </div>
                      <p className="mt-3 min-h-12 text-sm leading-6 text-[var(--muted)]">{item.meta}</p>
                      <Button variant="outline" size="lg" disabled className="mt-5 w-full">
                        {item.button}
                      </Button>
                    </article>
                  ))}
                </div>
              </div>
              <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-[var(--border)] pt-6">
                <p className="text-sm text-[var(--muted)]">
                  Run Voss from source while desktop builds are finalized.
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

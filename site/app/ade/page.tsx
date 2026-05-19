import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  BrainCircuit,
  CheckCircle2,
  CircleDollarSign,
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
import Reveal, { Stagger, StaggerItem } from "@/components/Reveal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Agentic Development Environment — ${site.name}`,
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
                  Agentic Development <span className="em">Environment</span>.
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
                      Install the ADE
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
              <AdeMock />
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
              {WORKFLOW.map((item, index) => (
                <article
                  key={item.step}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <p className="font-mono text-xs text-[var(--accent)]">{String(index + 1).padStart(2, "0")}</p>
                  <h3 className="mt-4 text-xl font-medium">{item.step}</h3>
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

function AdeMock() {
  const sessionRows = ["M12 MCP bridge", "M11 inspect tools", "T8 input ergonomics"];
  const toolRows = ["voss_py_diff", "voss_budget_trace", "mcp.tools.list"];

  return (
    <div
      className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[color-mix(in_oklab,var(--surface)_82%,black)] shadow-2xl"
      aria-label="Mock Voss ADE interface"
    >
      <div className="flex items-center justify-between border-b border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 font-mono text-xs text-[var(--muted)]">
        <span>voss ade</span>
        <span className="text-[var(--accent)]">plan | edit | auto</span>
      </div>
      <div className="space-y-4 p-4">
        <section className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4">
          <div className="flex items-center justify-between gap-4">
            <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--muted)]">
              Workspace
            </p>
            <p className="truncate font-mono text-xs text-[var(--accent)]">~/Projects/Voss</p>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {sessionRows.map((row, index) => (
              <div
                key={row}
                className="min-w-0 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
              >
                <p className="truncate font-mono text-xs text-[var(--foreground)]">{row}</p>
                <p className="mt-1 font-mono text-[10px] text-[var(--muted)]">checkpoint 0{index + 1}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4">
          <div className="mb-4 flex items-center justify-between gap-4">
            <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--muted)]">
              Active turn
            </p>
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              edit
            </Badge>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-black/30 p-4 font-mono text-[11px] leading-6">
            <p className="text-[var(--accent)]">$ voss do &quot;plan ADE page&quot;</p>
            <div className="mt-3 grid gap-2">
              <MockLine label="plan" value="route + scaffold + download placeholders" />
              <MockLine label="read" value="site/app/page.tsx" />
              <MockLine label="edit" value="site/components/Nav.tsx" />
              <MockLine label="check" value="lint + build + mobile review" />
            </div>
          </div>
        </section>

        <section className="grid gap-3">
          <div className="grid grid-cols-3 gap-2">
            {toolRows.map((row) => (
              <div
                key={row}
                className="flex min-w-0 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
              >
                <CheckCircle2 className="h-4 w-4 text-[var(--accent)]" />
                <span className="min-w-0 truncate font-mono text-xs">{row}</span>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2">
            <Metric label="confidence" value="0.91" />
            <Metric label="budget" value="$0.18" />
            <Metric label="mode" value="edit" />
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-3">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-[var(--accent)]">
              <CircleDollarSign className="h-4 w-4" />
                <span className="font-mono text-xs">budget trace</span>
              </div>
              <span className="font-mono text-xs text-[var(--muted)]">inspectable</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]">
              <div className="h-full w-2/3 rounded-full bg-[var(--accent)]" />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function MockLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[56px_minmax(0,1fr)] gap-3">
      <span className="font-mono text-xs text-[var(--muted)]">{label}</span>
      <span className="min-w-0 truncate text-[var(--foreground)]">{value}</span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-3">
      <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--muted)]">{label}</p>
      <p className="mt-2 font-mono text-sm text-[var(--accent)]">{value}</p>
    </div>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import {
  CheckCircle2,
  FolderLock,
  KeyRound,
  LockKeyhole,
  SlidersHorizontal,
  SquareTerminal,
  TerminalSquare,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Security - ${site.name}`,
  description: "How Voss approaches harness permissions, local credentials, project boundaries, and agent execution safety.",
};

const PRINCIPLES: { title: string; body: string; icon: LucideIcon }[] = [
  {
    title: "Permission modes are explicit",
    body: "`plan`, `edit`, and `auto` make the agent's authority visible. The default path favors inspection before mutation.",
    icon: SlidersHorizontal,
  },
  {
    title: "Writes are scoped to the project",
    body: "Harness tools operate from the current working directory and keep file operations inside the project boundary.",
    icon: FolderLock,
  },
  {
    title: "Shell access is gated",
    body: "Shell execution is treated as a separate permission surface instead of being bundled into ordinary file edits.",
    icon: SquareTerminal,
  },
  {
    title: "Auth stays local",
    body: "Claude Code, Codex, and provider API keys are read from local auth stores or environment variables. Voss does not add a hosted credential service.",
    icon: KeyRound,
  },
];

const SURFACES = [
  "cwd jail for file tools",
  "read-only planning mode",
  "scoped edit mode",
  "prompted shell commands",
  "project-local session files",
  "VOSS.md and .voss/memory",
  "TUI permission modals",
  "redaction-aware transcripts",
] as const;

export default function SecurityPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              Security
            </Badge>
            <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
              Agent power needs <span className="em">visible boundaries</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              Voss treats repository automation as a security-sensitive workflow. The harness is
              built around scoped file access, explicit permission modes, local auth, project
              memory, and auditable sessions.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/harness">
                  <TerminalSquare />
                  Harness model
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href={site.docsUrl} target="_blank" rel="noreferrer">
                  Docs
                </Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-[1fr_0.85fr]">
            <div>
              <h2 className="display text-4xl sm:text-5xl">Current posture.</h2>
              <div className="mt-10 grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)]">
                {PRINCIPLES.map((item) => {
                  const Icon = item.icon;
                  return (
                  <article key={item.title} className="bg-[var(--surface)] p-6">
                    <div className="flex items-start gap-4">
                      <Icon className="mt-1 h-5 w-5 shrink-0 text-[var(--accent)]" />
                      <div>
                        <h3 className="text-lg font-medium">{item.title}</h3>
                        <p className="mt-2 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                      </div>
                    </div>
                  </article>
                  );
                })}
              </div>
            </div>
            <aside className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <div className="flex items-center gap-3">
                <LockKeyhole className="h-5 w-5 text-[var(--accent)]" />
                <h2 className="font-mono text-sm uppercase tracking-widest">Reviewed surfaces</h2>
              </div>
              <ul className="mt-6 space-y-4">
                {SURFACES.map((surface) => (
                  <li key={surface} className="flex items-center gap-3 text-sm text-[var(--muted)]">
                    <CheckCircle2 className="h-4 w-4 text-[var(--accent)]" />
                    {surface}
                  </li>
                ))}
              </ul>
              <p className="mt-8 border-t border-[var(--border)] pt-6 text-sm leading-7 text-[var(--muted)]">
                Voss is pre-release. Treat the harness as developer tooling, not a hardened
                production sandbox, until the v0.1 security checklist is complete.
              </p>
            </aside>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { teamRunDemo } from "@/lib/site";
import { Button } from "@/components/ui/button";

export default function TeamRunDemo() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div className="max-w-xl">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
              The MVP flow
            </p>
            <h2 className="display mt-3 text-4xl sm:text-5xl">
              Declare a team. <span className="em">Run a goal.</span>
            </h2>
            <p className="mt-4 text-[var(--muted)]">
              A team is declared once in <code className="font-mono text-[var(--foreground)]">.voss</code>:
              roles, scope, budget, and tools. Then a single goal runs as scoped, budgeted,
              independently reviewed work — with a replayable audit at the end.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/orchestration">
                  How it works
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="/audit">See the audit</Link>
              </Button>
            </div>
          </div>
          <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
            <div className="flex items-center gap-2 border-b border-[var(--border)] bg-[var(--background)] px-4 py-3">
              <span className="h-3 w-3 rounded-full bg-[#ff5b1f]" />
              <span className="h-3 w-3 rounded-full bg-[#c58a0f]" />
              <span className="h-3 w-3 rounded-full bg-[#1f8a4c]" />
              <span className="ml-2 font-mono text-xs text-[var(--muted)]">voss team run</span>
            </div>
            <pre className="overflow-x-auto px-5 py-5 font-mono text-xs leading-6 text-[var(--foreground)] sm:text-sm">
              {teamRunDemo}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}

import Link from "next/link";
import { site } from "@/lib/site";
import CopyButton from "./CopyButton";

export default function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-[var(--border)]">
      <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
      <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-28">
        <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 font-mono text-xs text-[var(--muted)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
          A language for AI workflows
        </p>
        <h1 className="text-balance text-5xl font-semibold tracking-tight sm:text-6xl">
          Stop reinventing the AI runtime.
        </h1>
        <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-[var(--muted)]">
          {site.description}
        </p>

        <div className="mt-10 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-mono text-sm">
            <span className="text-[var(--accent)]">$</span>
            <span className="select-all">{site.install.primary}</span>
            <CopyButton text={site.install.primary} />
          </div>
          <Link
            href={site.prdUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] px-4 py-3 text-sm text-[var(--foreground)] transition hover:border-[var(--accent)]"
          >
            Read the PRD →
          </Link>
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">{site.install.primaryNote}</p>
      </div>
    </section>
  );
}

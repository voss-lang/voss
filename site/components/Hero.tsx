import Link from "next/link";
import { site } from "@/lib/site";
import CopyButton from "./CopyButton";
import Cursor from "./Cursor";
import Reveal from "./Reveal";
import TerminalDemo from "./TerminalDemo";

export default function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-[var(--border)]">
      <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
      <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
      <div className="mx-auto grid max-w-6xl gap-12 px-6 pt-24 pb-20 sm:pt-32 sm:pb-28 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16">
        <div className="min-w-0">
          <Reveal>
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 font-mono text-xs text-[var(--muted)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              Terminal harness + .voss control language
            </p>
          </Reveal>
          <Reveal delay={0.05}>
            <h1 className="display text-balance text-[clamp(2.5rem,6vw,4.5rem)]">
              Bound AI coding work<br />
              <span className="em">before it edits.</span>
            </h1>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-[var(--muted)]">
              {site.description}
            </p>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="mt-10 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 font-mono text-sm">
                <span className="text-[var(--accent)]">$</span>
                <span className="select-all">{site.install.primary}</span>
                <Cursor />
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
          </Reveal>
        </div>

        <Reveal delay={0.2} className="min-w-0 lg:justify-self-end">
          <TerminalDemo className="w-full rotate-[0.5deg] transition-transform duration-500 hover:rotate-0" />
        </Reveal>
      </div>
    </section>
  );
}

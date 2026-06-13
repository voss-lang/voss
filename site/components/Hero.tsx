import { site } from "@/lib/site";
import CopyButton from "./CopyButton";
import TrackedIntentLink from "./TrackedIntentLink";
import Cursor from "./Cursor";
import ProductScreenshot from "./ProductScreenshot";
import Reveal from "./Reveal";

export default function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-[var(--border)]">
      <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
      <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
      <div className="mx-auto grid max-w-6xl gap-12 px-6 pt-24 pb-20 sm:pt-32 sm:pb-28 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16">
        <div className="min-w-0">
          <Reveal>
            <p className="mb-6 inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 font-mono text-xs text-[var(--muted)]">
              For developers supervising Claude Code, Codex, and local coding agents
            </p>
          </Reveal>
          <Reveal delay={0.05}>
            <h1 className="display text-balance text-[clamp(2.5rem,6vw,4.5rem)]">
              Keep coding agents inside<br />
              <span className="em">clear repo boundaries.</span>
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
              <TrackedIntentLink
                href="/audit"
                analyticsTarget="audit"
                className="inline-flex items-center justify-center rounded-lg border border-[var(--border)] px-4 py-3 text-sm text-[var(--foreground)] transition hover:border-[var(--accent)]"
              >
                See the audit trail
              </TrackedIntentLink>
            </div>
            <p className="mt-3 text-xs text-[var(--muted)]">{site.install.primaryNote}</p>
          </Reveal>
        </div>

        <Reveal delay={0.2} className="min-w-0 lg:justify-self-end">
          <ProductScreenshot
            src="/product/voss-vdiff.png"
            alt="Voss vdiff output showing a .voss source file beside generated Python."
            width={1200}
            height={1302}
            priority
            sizes="(min-width: 1024px) 520px, calc(100vw - 48px)"
            className="w-full rotate-[0.5deg] transition-transform duration-500 hover:rotate-0"
          />
        </Reveal>
      </div>
    </section>
  );
}

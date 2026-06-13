import Link from "next/link";
import Nav from "@/components/Nav";
import { pageMetadata } from "@/lib/metadata";
import Hero from "@/components/Hero";
import FeatureGrid from "@/components/FeatureGrid";
import OrgLoop from "@/components/OrgLoop";
import TeamRunDemo from "@/components/TeamRunDemo";
import CliShowcase from "@/components/CliShowcase";
import CommandList from "@/components/CommandList";
import InstallTabs from "@/components/InstallTabs";
import Footer from "@/components/Footer";
import TrackedIntentLink from "@/components/TrackedIntentLink";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `${site.name} - ${site.tagline}`,
  description: site.description,
  path: "/",
});

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <FeatureGrid />
        <OrgLoop />
        <TeamRunDemo />
        <CliShowcase />
        <CommandList />
        <InstallTabs />
        <ProductTeaser />
      </main>
      <Footer />
    </>
  );
}

function ProductTeaser() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] lg:grid-cols-2">
          <div className="p-8 sm:p-12">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">Audit</p>
            <h2 className="display mt-3 text-4xl sm:text-5xl">
              The audit is the <span className="em">trust product</span>.
            </h2>
            <p className="mt-4 text-[var(--muted)]">
              Every run produces a replayable trail: goal, principles, board, diffs, tests, reviewer
              verdicts, blocked work, and residual risk. EM claims are separated from verified
              evidence.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedIntentLink
                href="/audit"
                analyticsTarget="audit"
                className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--background)] transition hover:opacity-90"
              >
                See the audit
              </TrackedIntentLink>
              <Link
                href="/ade"
                className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
              >
                Explore the ADE
              </Link>
            </div>
          </div>
          <div className="border-t border-[var(--border)] bg-[var(--background)] p-8 sm:p-12 lg:border-l lg:border-t-0">
            <h2 className="display text-4xl sm:text-5xl">
              Declared in <span className="em">.voss</span>.
            </h2>
            <p className="mt-4 text-[var(--muted)]">
              Roles, scope, budget, tools, principles, and gates are a compiler-checked control
              language — not prompt soup. Static errors are clear enough for non-CS users.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/language"
                className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--background)] transition hover:opacity-90"
              >
                The language
              </Link>
              <Link
                href={site.docsUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
              >
                Browse docs
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

import Link from "next/link";
import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import FeatureGrid from "@/components/FeatureGrid";
import CliShowcase from "@/components/CliShowcase";
import CommandList from "@/components/CommandList";
import InstallTabs from "@/components/InstallTabs";
import Footer from "@/components/Footer";
import { site } from "@/lib/site";

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <FeatureGrid />
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
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">ADE</p>
            <h2 className="display mt-3 text-4xl sm:text-5xl">
              An agentic workspace with <span className="em">explicit boundaries</span>.
            </h2>
            <p className="mt-4 text-[var(--muted)]">
              The Voss ADE brings tools, memory, permissions, sessions, replay, and inspection
              surfaces into one local environment.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/ade"
                className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--background)] transition hover:opacity-90"
              >
                Explore ADE
              </Link>
              <Link
                href="/harness"
                className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
              >
                Harness details
              </Link>
            </div>
          </div>
          <div className="border-t border-[var(--border)] bg-[var(--background)] p-8 sm:p-12 lg:border-l lg:border-t-0">
            <h2 className="display text-4xl sm:text-5xl">
              Docs for the <span className="em">current harness</span>.
            </h2>
            <p className="mt-4 text-[var(--muted)]">
              Install paths, harness commands, permission modes, project memory, language reference,
              and troubleshooting live in the public docs.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href={site.docsUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-[var(--background)] transition hover:opacity-90"
              >
                Browse docs
              </Link>
              <Link
                href={site.prdUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
              >
                Read PRD
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

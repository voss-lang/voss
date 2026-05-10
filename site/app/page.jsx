import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import FeatureGrid from "@/components/FeatureGrid";
import CliShowcase from "@/components/CliShowcase";
import CommandList from "@/components/CommandList";
import InstallTabs from "@/components/InstallTabs";
import Footer from "@/components/Footer";
import Link from "next/link";

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
        <DocsTeaser />
      </main>
      <Footer />
    </>
  );
}

function DocsTeaser() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-10 sm:p-14">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">Docs</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            The full reference is coming.
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--muted)]">
            Language reference, runtime API, CLI deep-dive, and migration guides from raw Python.
            For now the PRD is the source of truth.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/docs"
              className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
            >
              Browse docs
            </Link>
            <Link
              href="https://github.com/your-org/voss/blob/main/PRD.md"
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
            >
              Read the PRD
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

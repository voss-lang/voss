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
        <AdeTeaser />
        <DocsTeaser />
      </main>
      <Footer />
    </>
  );
}

function AdeTeaser() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-10 sm:p-14">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
            ADE
          </p>
          <h2 className="display mt-3 text-4xl sm:text-5xl">
            An agentic workspace with <span className="em">explicit boundaries</span>.
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--muted)]">
            The Voss ADE brings tools, memory, permissions, sessions, replay, and inspection
            surfaces into one local environment, with the harness as its bounded execution layer.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/ade"
              className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
            >
              Explore the ADE
            </Link>
            <Link
              href="/harness"
              className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm transition hover:border-[var(--accent)]"
            >
              Harness details
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function DocsTeaser() {
  return (
    <section className="border-b border-[var(--border)]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-10 sm:p-14">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">Docs</p>
          <h2 className="display mt-3 text-4xl sm:text-5xl">
            The docs track the <span className="em">current harness</span>.
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--muted)]">
            Install paths, harness commands, permission modes, project memory, language reference,
            and troubleshooting all live in the public docs.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href={site.docsUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-[var(--accent)] bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
            >
              Browse docs
            </Link>
            <Link
              href="https://github.com/bm9797/Voss/blob/main/PRD.md"
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

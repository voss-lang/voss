import type { Metadata } from "next";
import type { ComponentType } from "react";
import Link from "next/link";
import { ArrowUpRight, BookOpenText, Code2, ShieldCheck, TerminalSquare } from "lucide-react";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

type DocSection = {
  icon: ComponentType<{ className?: string }>;
  title: string;
  body: string;
  href: string;
};

const DOC_SECTIONS: DocSection[] = [
  {
    icon: TerminalSquare,
    title: "Harness",
    body: "Plan, edit, validate, and resume AI-assisted repo work with explicit modes and scoped tools.",
    href: `${site.docsUrl}/harness/overview`,
  },
  {
    icon: Code2,
    title: "Language",
    body: "Use `.voss` as the workflow-control language for confidence, budgets, routing, memory, and agents.",
    href: `${site.docsUrl}/language/overview`,
  },
  {
    icon: ShieldCheck,
    title: "Security",
    body: "Understand cwd jails, permission prompts, shell allowlists, session redaction, and edit scope.",
    href: `${site.docsUrl}/security/overview`,
  },
];

export const metadata: Metadata = {
  title: "Docs — Voss",
  description: "Developer documentation for the Voss harness and .voss workflow-control language.",
};

export default function DocsPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-5xl px-6 pt-24 pb-16">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
              Documentation
            </p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
              Voss docs now live in Mintlify.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--muted)]">
              The public docs cover the harness, `.voss` workflow-control language, security model,
              CLI reference, and v0.1 roadmap.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href={site.docsUrl}>
                  <BookOpenText />
                  Open docs
                  <ArrowUpRight />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href={`${site.docsUrl}/get-started/quickstart`}>
                  Quickstart
                  <ArrowUpRight />
                </Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-5xl gap-px overflow-hidden px-6 py-16 sm:grid-cols-3">
            {DOC_SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <Link
                  key={section.title}
                  href={section.href}
                  className="group border border-[var(--border)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                >
                  <Icon className="h-5 w-5 text-[var(--accent)]" />
                  <h2 className="mt-4 text-lg font-medium">{section.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{section.body}</p>
                  <span className="mt-4 inline-flex items-center gap-1 font-mono text-xs uppercase tracking-wider text-[var(--accent)]">
                    Read section
                    <ArrowUpRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

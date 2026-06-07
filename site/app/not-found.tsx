import type { Metadata } from "next";
import Link from "next/link";
import { BookOpenText, Home, TerminalSquare, Workflow } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import TrackedOutboundLink from "@/components/TrackedOutboundLink";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: `Page not found - ${site.name}`,
  robots: { index: false, follow: true },
};

const RECOVERY_LINKS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/harness/", label: "Harness", icon: TerminalSquare },
  { href: "/orchestration/", label: "Orchestration", icon: Workflow },
] as const;

export default function NotFound() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="glow absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-28">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              404
            </Badge>
            <h1 className="display mt-5 max-w-3xl text-[clamp(2.5rem,6vw,4.5rem)]">
              This route is <span className="em">out of scope</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              The page you requested does not exist or may have moved. Head back to the product
              overview or jump into the harness docs to keep going.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/">
                  <Home />
                  Back to home
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <TrackedOutboundLink href={site.docsUrl} analyticsTarget="docs">
                  <BookOpenText />
                  Documentation
                </TrackedOutboundLink>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <h2 className="font-mono text-sm uppercase tracking-widest text-[var(--muted)]">
              Popular destinations
            </h2>
            <ul className="mt-6 grid gap-3 sm:grid-cols-3">
              {RECOVERY_LINKS.map(({ href, label, icon: Icon }) => (
                <li key={href}>
                  <Link
                    href={href}
                    className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-5 py-4 text-[var(--foreground)] transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                  >
                    <Icon className="h-5 w-5 shrink-0 text-[var(--accent)]" aria-hidden="true" />
                    <span className="font-medium">{label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

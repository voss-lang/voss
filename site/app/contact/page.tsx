import Link from "next/link";
import { BookOpenText, Bug, GitBranch, ShieldAlert, TerminalSquare } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import TrackedOutboundLink from "@/components/TrackedOutboundLink";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Contact - ${site.name}`,
  description:
    "How to reach the Voss project for bugs, product questions, documentation issues, and security disclosures.",
  path: "/contact",
});

const CHANNELS = [
  {
    title: "Bugs and product questions",
    body: "Open a GitHub issue with the command, environment, expected behavior, actual behavior, and any relevant logs.",
    href: `${site.repoUrl}/issues/new`,
    label: "Open an issue",
    icon: Bug,
    external: true,
  },
  {
    title: "Documentation issues",
    body: "Start from the docs if you are validating an install, command, mode, or orchestration workflow.",
    href: site.docsUrl,
    label: "Read docs",
    icon: BookOpenText,
    external: true,
  },
  {
    title: "Security reports",
    body: "Use the disclosure page first so exploit details are not posted into a public issue by accident.",
    href: "/disclosure",
    label: "Disclosure process",
    icon: ShieldAlert,
    external: false,
  },
] as const;

export default function ContactPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-24">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              Contact
            </Badge>
            <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
              Reach the project where <span className="em">the work happens</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              Voss is early and open-source. For now, the public repo is the primary place to
              report bugs, ask product questions, and follow implementation work.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <TrackedOutboundLink href={`${site.repoUrl}/issues/new`} analyticsTarget="github">
                  <GitBranch />
                  GitHub issue
                </TrackedOutboundLink>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="/harness">
                  <TerminalSquare />
                  Product overview
                </Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-4 px-6 py-20 md:grid-cols-3">
            {CHANNELS.map((channel) => {
              const Icon = channel.icon;
              const content = (
                <>
                  <Icon className="h-6 w-6 text-[var(--accent)]" />
                  <h2 className="mt-5 text-xl font-semibold tracking-tight">{channel.title}</h2>
                  <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{channel.body}</p>
                  <span className="mt-6 inline-flex text-sm font-medium text-[var(--foreground)]">
                    {channel.label}
                  </span>
                </>
              );

              return channel.external ? (
                <TrackedOutboundLink
                  key={channel.title}
                  href={channel.href}
                  analyticsTarget={channel.href === site.docsUrl ? "docs" : "github"}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                >
                  {content}
                </TrackedOutboundLink>
              ) : (
                <Link
                  key={channel.title}
                  href={channel.href}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"
                >
                  {content}
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

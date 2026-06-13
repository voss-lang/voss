import Link from "next/link";
import { Cookie, EyeOff, GitBranch, LockKeyhole, ShieldCheck } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import TrackedOutboundLink from "@/components/TrackedOutboundLink";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Privacy - ${site.name}`,
  description:
    "Privacy notes for the Voss marketing site, including opt-in analytics and local consent storage.",
  path: "/privacy",
});

const PRIVACY_POINTS = [
  {
    title: "No account or contact form on this site",
    body: "The marketing site does not create user accounts and does not collect form submissions.",
    icon: LockKeyhole,
  },
  {
    title: "Analytics starts opted out",
    body: "PostHog is initialized with capture disabled by default. Pageviews and conversion events are sent only after analytics consent is accepted.",
    icon: EyeOff,
  },
  {
    title: "Consent is stored locally",
    body: "The consent choice is stored in browser localStorage under `voss-analytics-consent`; PostHog may also use localStorage and cookies after opt-in.",
    icon: Cookie,
  },
  {
    title: "No ads or cross-site tracking",
    body: "The consent banner describes the current posture: product analytics for pages and install paths, not advertising or cross-site tracking.",
    icon: ShieldCheck,
  },
] as const;

export default function PrivacyPage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-24">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              Privacy
            </Badge>
            <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
              Minimal collection, <span className="em">explicit analytics consent</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              This page documents what the Voss marketing site does today. It is intentionally
              narrow: no account system, no sales form, no advertising pixels, and opt-in product
              analytics only when a PostHog key is configured.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/contact">Contact</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <TrackedOutboundLink href={site.repoUrl} analyticsTarget="github">
                  <GitBranch />
                  Source
                </TrackedOutboundLink>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="grid gap-px overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-2">
              {PRIVACY_POINTS.map((point) => {
                const Icon = point.icon;
                return (
                  <article key={point.title} className="bg-[var(--surface)] p-6">
                    <Icon className="h-6 w-6 text-[var(--accent)]" />
                    <h2 className="mt-5 text-xl font-semibold tracking-tight">{point.title}</h2>
                    <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{point.body}</p>
                  </article>
                );
              })}
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-20">
            <div className="max-w-3xl">
              <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
                Events currently instrumented
              </p>
              <h2 className="display mt-3 text-4xl sm:text-5xl">
                Pageviews, outbound clicks, install-copy actions.
              </h2>
              <p className="mt-5 leading-8 text-[var(--muted)]">
                After consent, the site records pageviews, outbound clicks to docs, GitHub, and the
                PRD, audit-trail clicks, and install-command copy actions. Those events help
                identify which pages, proof artifacts, and install paths are useful. Declining
                analytics keeps capture disabled.
              </p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

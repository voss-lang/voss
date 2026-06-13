import Link from "next/link";
import { AlertTriangle, GitBranch, LockKeyhole, ShieldAlert, ShieldCheck } from "lucide-react";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import TrackedOutboundLink from "@/components/TrackedOutboundLink";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { pageMetadata } from "@/lib/metadata";
import { site } from "@/lib/site";

export const metadata = pageMetadata({
  title: `Security Disclosure - ${site.name}`,
  description:
    "How to report security issues in Voss without exposing sensitive details in public channels.",
  path: "/disclosure",
});

const SCOPE = [
  "Voss CLI and harness behavior",
  ".voss workflow-control files and runtime behavior",
  "npm, PyPI, and container packaging paths",
  "Marketing and documentation site behavior",
] as const;

const OUT_OF_SCOPE = [
  "Social engineering",
  "Spam or denial-of-service testing",
  "Destructive testing against real projects",
  "Reports that require leaking secrets into a public issue",
] as const;

export default function DisclosurePage() {
  return (
    <>
      <Nav />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--border)]">
          <div className="grid-backdrop absolute inset-0 -z-10" aria-hidden="true" />
          <div className="mx-auto max-w-6xl px-6 pt-24 pb-20 sm:pt-32 sm:pb-24">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              Security disclosure
            </Badge>
            <h1 className="display mt-5 max-w-4xl text-[clamp(2.5rem,6vw,4.5rem)]">
              Report security issues <span className="em">without public details</span>.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted)]">
              Voss is local-first developer tooling, so security reports should protect repos,
              credentials, and exploit details. Do not paste secrets, token values, or working
              exploit steps into a public issue.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <TrackedOutboundLink href={`${site.repoUrl}/issues/new`} analyticsTarget="github">
                  <ShieldAlert />
                  Start a minimal issue
                </TrackedOutboundLink>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="/security">
                  <ShieldCheck />
                  Security model
                </Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-2">
            <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <LockKeyhole className="h-6 w-6 text-[var(--accent)]" />
              <h2 className="mt-5 text-2xl font-semibold tracking-tight">How to report</h2>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Open a minimal GitHub issue that says you have a security report and need a private
                channel. Include the affected package or surface, impact summary, and safe contact
                path. Leave exploit details, private repo names, and credentials out of the issue.
              </p>
              <div className="mt-6">
                <Button asChild variant="outline">
                  <TrackedOutboundLink href={`${site.repoUrl}/issues/new`} analyticsTarget="github">
                    <GitBranch />
                    Open GitHub issue
                  </TrackedOutboundLink>
                </Button>
              </div>
            </article>

            <article className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <AlertTriangle className="h-6 w-6 text-[var(--accent)]" />
              <h2 className="mt-5 text-2xl font-semibold tracking-tight">Handling expectations</h2>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">
                Voss does not currently publish a bug bounty program. Reports are handled as
                coordinated disclosure: confirm receipt, reproduce impact, ship a fix, and credit
                the reporter when they want attribution.
              </p>
            </article>
          </div>
        </section>

        <section className="border-b border-[var(--border)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-2">
            <div>
              <h2 className="font-mono text-sm uppercase tracking-widest">In scope</h2>
              <ul className="mt-6 space-y-4">
                {SCOPE.map((item) => (
                  <li key={item} className="text-sm leading-7 text-[var(--muted)]">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h2 className="font-mono text-sm uppercase tracking-widest">Out of scope</h2>
              <ul className="mt-6 space-y-4">
                {OUT_OF_SCOPE.map((item) => (
                  <li key={item} className="text-sm leading-7 text-[var(--muted)]">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

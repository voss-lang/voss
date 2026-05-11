import Link from "next/link";
import { ArrowUpRight, BookOpenText, Github, TerminalSquare } from "lucide-react";
import { LogoMark } from "@/components/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[color-mix(in_oklab,var(--surface)_42%,var(--background))]">
      <div className="mx-auto grid max-w-6xl gap-12 px-6 py-16 md:grid-cols-[1.35fr_1fr] md:py-20">
        <div className="max-w-xl">
          <Link href="/" className="group inline-flex items-center gap-4">
            <span className="flex h-16 w-16 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--background)] transition-colors group-hover:border-[var(--accent)]">
              <LogoMark className="h-13 w-13" />
            </span>
            <span>
              <span className="block font-mono text-3xl font-semibold leading-none tracking-tight">{site.name}</span>
              <span className="mt-2 block text-base text-[var(--muted)]">{site.tagline}</span>
            </span>
          </Link>
          <p className="mt-6 text-base leading-7 text-[var(--muted)]">{site.description}</p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Badge variant="secondary" className="font-mono uppercase tracking-wider">
              {site.version}
            </Badge>
            <Button asChild variant="outline" size="lg">
              <Link href="/harness">
                <TerminalSquare />
                Harness
              </Link>
            </Button>
          </div>
        </div>
        <div className="grid gap-8 sm:grid-cols-2 md:justify-self-end">
          <div>
            <h2 className="font-mono text-sm uppercase tracking-widest text-[var(--foreground)]">Product</h2>
            <div className="mt-4 flex flex-col items-start gap-2">
              <Button asChild variant="link" className="h-auto px-0 py-1 text-base">
                <Link href="/harness">
                  <TerminalSquare />
                  Harness
                </Link>
              </Button>
              <Button asChild variant="link" className="h-auto px-0 py-1 text-base">
                <Link href="/docs">
                  <BookOpenText />
                  Docs
                </Link>
              </Button>
            </div>
          </div>
          <div>
            <h2 className="font-mono text-sm uppercase tracking-widest text-[var(--foreground)]">Source</h2>
            <div className="mt-4 flex flex-col items-start gap-2">
              <Button asChild variant="link" className="h-auto px-0 py-1 text-base">
                <Link href={site.repoUrl} target="_blank" rel="noreferrer">
                  <Github />
                  GitHub
                  <ArrowUpRight />
                </Link>
              </Button>
              <Button asChild variant="link" className="h-auto px-0 py-1 text-base">
                <Link href={site.prdUrl} target="_blank" rel="noreferrer">
                  <BookOpenText />
                  PRD
                  <ArrowUpRight />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

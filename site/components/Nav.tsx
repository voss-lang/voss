import Link from "next/link";
import { ArrowUpRight, BookOpenText, Github, TerminalSquare } from "lucide-react";
import { LogoMark } from "@/components/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--border)] bg-[color-mix(in_oklab,var(--background)_90%,transparent)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-5 md:min-h-24 md:flex-row md:items-center md:justify-between">
        <Link href="/" className="group flex items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] transition-colors group-hover:border-[var(--accent)]">
            <LogoMark className="h-11 w-11" />
          </span>
          <span className="flex flex-col gap-1">
            <span className="font-mono text-2xl font-semibold leading-none tracking-tight">{site.name}</span>
            <span className="text-sm text-[var(--muted)]">{site.tagline}</span>
          </span>
          <Badge variant="secondary" className="ml-1 hidden font-mono uppercase tracking-wider sm:inline-flex">
            {site.version}
          </Badge>
        </Link>
        <nav className="flex flex-wrap items-center gap-2">
          <Button asChild variant="ghost" size="lg">
            <Link href="/harness">
              <TerminalSquare />
              Harness
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/docs">
              <BookOpenText />
              Docs
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href={site.repoUrl} target="_blank" rel="noreferrer">
              <Github />
              GitHub
              <ArrowUpRight />
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}

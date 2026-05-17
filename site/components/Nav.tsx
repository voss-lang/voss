import Link from "next/link";
import { ArrowUpRight, BookOpenText, Code2, GitBranch, TerminalSquare } from "lucide-react";
import { LogoMark } from "@/components/Logo";
import MobileMenu from "@/components/MobileMenu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--border)] bg-[color-mix(in_oklab,var(--background)_90%,transparent)] backdrop-blur-xl">
      <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5 md:min-h-24">
        <Link href="/" className="group flex items-center gap-4">
          <span className="flex h-12 w-12 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] transition-colors group-hover:border-[var(--accent)] sm:h-14 sm:w-14">
            <LogoMark className="h-9 w-9 sm:h-11 sm:w-11" />
          </span>
          <span className="flex flex-col gap-1">
            <span className="font-mono text-xl font-semibold leading-none tracking-tight sm:text-2xl">{site.name}</span>
            <span className="hidden text-sm text-[var(--muted)] sm:block">{site.tagline}</span>
          </span>
          <Badge variant="secondary" className="ml-1 hidden font-mono uppercase tracking-wider sm:inline-flex">
            {site.version}
          </Badge>
        </Link>
        <MobileMenu className="md:hidden" />
        <nav className="hidden flex-wrap items-center gap-2 md:flex">
          <Button asChild variant="ghost" size="lg">
            <Link href="/harness">
              <TerminalSquare />
              Harness
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href={site.docsUrl} target="_blank" rel="noreferrer">
              <BookOpenText />
              Docs
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/language">
              <Code2 />
              Language
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href={site.repoUrl} target="_blank" rel="noreferrer">
              <GitBranch />
              GitHub
              <ArrowUpRight />
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}

import Link from "next/link";
import { ArrowUpRight, BookOpenText, Code2, GitBranch, Layers3, TerminalSquare, Workflow } from "lucide-react";
import { LogoMark } from "@/components/Logo";
import MobileMenu from "@/components/MobileMenu";
import TrackedOutboundLink from "@/components/TrackedOutboundLink";
import { Button } from "@/components/ui/button";
import { site } from "@/lib/site";

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--border)] bg-[color-mix(in_oklab,var(--background)_90%,transparent)] backdrop-blur-xl">
      <div className="relative mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3 md:min-h-16">
        <Link href="/" className="group flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] transition-colors group-hover:border-[var(--accent)] sm:h-12 sm:w-12">
            <LogoMark className="h-8 w-8 sm:h-9 sm:w-9" />
          </span>
          <span className="flex flex-col gap-1">
            <span className="font-mono text-xl font-semibold leading-none tracking-tight sm:text-2xl">{site.name}</span>
            <span className="hidden text-sm text-[var(--muted)] sm:block">{site.tagline}</span>
          </span>
        </Link>
        <MobileMenu className="md:hidden" />
        <nav className="hidden items-center gap-2 md:flex">
          <Button asChild variant="ghost" size="lg">
            <Link href="/orchestration">
              <Workflow />
              Orchestration
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/ade">
              <Layers3 />
              ADE
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/harness">
              <TerminalSquare />
              Harness
            </Link>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <TrackedOutboundLink href={site.docsUrl} analyticsTarget="docs">
              <BookOpenText />
              Docs
            </TrackedOutboundLink>
          </Button>
          <Button asChild variant="ghost" size="lg">
            <Link href="/language">
              <Code2 />
              Language
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <TrackedOutboundLink href={site.repoUrl} analyticsTarget="github">
              <GitBranch />
              GitHub
              <ArrowUpRight />
            </TrackedOutboundLink>
          </Button>
        </nav>
      </div>
    </header>
  );
}

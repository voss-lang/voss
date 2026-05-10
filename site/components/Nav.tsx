import Link from "next/link";
import { site } from "@/lib/site";

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--border)] bg-[color-mix(in_oklab,var(--background)_85%,transparent)] backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-mono text-lg font-semibold tracking-tight">
          <Logomark />
          <span>{site.name}</span>
          <span className="ml-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-1.5 py-0.5 text-[10px] font-normal uppercase tracking-wider text-[var(--muted)]">
            {site.version}
          </span>
        </Link>
        <nav className="flex items-center gap-6 text-sm text-[var(--muted)]">
          <Link href="/harness" className="transition hover:text-[var(--foreground)]">
            Harness
          </Link>
          <Link href="/docs" className="transition hover:text-[var(--foreground)]">
            Docs
          </Link>
          <Link
            href={site.repoUrl}
            className="transition hover:text-[var(--foreground)]"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </Link>
        </nav>
      </div>
    </header>
  );
}

function Logomark() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 4l9 16 9-16" />
    </svg>
  );
}

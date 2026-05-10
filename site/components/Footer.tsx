import Link from "next/link";
import { site } from "@/lib/site";

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border)]">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-6 py-12 sm:flex-row sm:items-center">
        <div>
          <p className="font-mono text-sm">{site.name}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {site.tagline} &middot; {site.version}
          </p>
        </div>
        <div className="flex items-center gap-6 text-sm text-[var(--muted)]">
          <Link href="/docs" className="hover:text-[var(--foreground)]">
            Docs
          </Link>
          <Link href={site.repoUrl} target="_blank" rel="noreferrer" className="hover:text-[var(--foreground)]">
            GitHub
          </Link>
          <Link href={site.prdUrl} target="_blank" rel="noreferrer" className="hover:text-[var(--foreground)]">
            PRD
          </Link>
        </div>
      </div>
    </footer>
  );
}

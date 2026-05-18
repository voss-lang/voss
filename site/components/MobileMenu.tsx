"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, BookOpenText, Code2, GitBranch, Menu, TerminalSquare, X } from "lucide-react";
import { captureOutboundClick } from "@/lib/analytics";
import { site } from "@/lib/site";

type Item = {
  href: string;
  label: string;
  icon: typeof TerminalSquare;
  external?: boolean;
};

const ITEMS: Item[] = [
  { href: "/harness", label: "Harness", icon: TerminalSquare },
  { href: site.docsUrl, label: "Docs", icon: BookOpenText, external: true },
  { href: "/language", label: "Language", icon: Code2 },
  { href: site.repoUrl, label: "GitHub", icon: GitBranch, external: true },
];

const OUTBOUND_TARGETS: Partial<Record<string, "docs" | "github">> = {
  Docs: "docs",
  GitHub: "github",
};

export default function MobileMenu({ className = "" }: { className?: string }) {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="mobile-nav"
        aria-label={open ? "Close menu" : "Open menu"}
        className="flex h-11 w-11 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)] transition active:scale-[0.94] hover:border-[var(--accent)]"
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.nav
            id="mobile-nav"
            initial={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
            animate={reduced ? { opacity: 1 } : { opacity: 1, height: "auto" }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
            className="absolute inset-x-0 top-full overflow-hidden border-b border-[var(--border)] bg-[var(--background)]"
          >
            <ul className="mx-auto flex max-w-6xl flex-col gap-1 px-6 py-4">
              {ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.label}>
                    <Link
                      href={item.href}
                      onClick={() => {
                        const target = OUTBOUND_TARGETS[item.label];
                        if (target) captureOutboundClick(target);
                        setOpen(false);
                      }}
                      target={item.external ? "_blank" : undefined}
                      rel={item.external ? "noreferrer" : undefined}
                      className="flex items-center gap-3 rounded-lg px-3 py-3 text-base text-[var(--foreground)] transition active:scale-[0.98] hover:bg-[var(--surface)]"
                    >
                      <Icon className="h-5 w-5 text-[var(--accent)]" />
                      {item.label}
                      {item.external && <ArrowUpRight className="ml-auto h-4 w-4 text-[var(--muted)]" />}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </motion.nav>
        )}
      </AnimatePresence>
    </div>
  );
}

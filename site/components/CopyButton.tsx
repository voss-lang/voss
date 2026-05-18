"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { captureCopyInstall } from "@/lib/analytics";

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <motion.button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          captureCopyInstall(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1400);
        } catch {
          /* clipboard unavailable */
        }
      }}
      animate={copied ? { scale: [1, 1.08, 1] } : { scale: 1 }}
      transition={{ type: "spring", stiffness: 540, damping: 14 }}
      className={`rounded-md border px-2.5 py-1 text-xs font-medium transition ${
        copied
          ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--foreground)]"
          : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--foreground)]"
      }`}
      aria-label="Copy to clipboard"
    >
      {copied ? "Copied" : "Copy"}
    </motion.button>
  );
}

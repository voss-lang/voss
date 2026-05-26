"use client";

import { motion, useReducedMotion } from "motion/react";

type Props = {
  className?: string;
  /** When true, holds steady (no blink), used for static prompts. */
  steady?: boolean;
};

export default function Cursor({ className = "", steady = false }: Props) {
  const reduced = useReducedMotion();
  return (
    <motion.span
      aria-hidden
      className={`ml-0.5 inline-block h-[1em] w-[0.55ch] -mb-[0.12em] bg-[var(--accent)] align-baseline ${className}`}
      animate={steady || reduced ? { opacity: 1 } : { opacity: [1, 1, 0, 0] }}
      transition={
        steady || reduced
          ? { duration: 0 }
          : { duration: 1.06, repeat: Infinity, times: [0, 0.5, 0.5, 1], ease: "linear" }
      }
    />
  );
}

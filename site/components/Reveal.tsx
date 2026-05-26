"use client";

import { motion, useReducedMotion } from "motion/react";
import type { CSSProperties, ReactNode } from "react";

type Props = {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
  as?: "div" | "section" | "li" | "span";
};

export default function Reveal({
  children,
  delay = 0,
  y = 16,
  className = "",
  as = "div",
}: Props) {
  const reduced = useReducedMotion();
  const MotionTag = motion[as];
  if (reduced) {
    const Tag = as;
    return <Tag className={className}>{children}</Tag>;
  }
  return (
    <MotionTag
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.05 }}
      transition={{ type: "spring", stiffness: 220, damping: 28, delay }}
    >
      {children}
    </MotionTag>
  );
}

/**
 * Stagger plays once on mount (not viewport-gated) so children
 * always become visible, even when JS-driven scroll listeners
 * don't fire (e.g. headless screenshot tools).
 */
export function Stagger({
  children,
  className = "",
  staggerChildren = 0.06,
}: {
  children: ReactNode;
  className?: string;
  staggerChildren?: number;
}) {
  const reduced = useReducedMotion();
  if (reduced) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren, delayChildren: 0.05 } },
      }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className = "",
  style,
  y = 16,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  y?: number;
}) {
  const reduced = useReducedMotion();
  if (reduced) {
    return (
      <div className={className} style={style}>
        {children}
      </div>
    );
  }
  return (
    <motion.div
      className={className}
      style={style}
      variants={{
        hidden: { opacity: 0, y },
        show: {
          opacity: 1,
          y: 0,
          transition: { type: "spring", stiffness: 220, damping: 28 },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

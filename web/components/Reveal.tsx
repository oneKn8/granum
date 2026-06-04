"use client";

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  /** vertical travel in px */
  y?: number;
  as?: "div" | "section" | "li";
}

/**
 * Fade + rise as the element scrolls into view. Compositor-only (opacity +
 * transform). Honors prefers-reduced-motion by rendering statically.
 */
export function Reveal({ children, className, delay = 0, y = 18, as = "div" }: RevealProps) {
  const reduce = useReducedMotion();
  const Tag = motion[as];
  if (reduce) {
    const Plain = as;
    return <Plain className={className}>{children}</Plain>;
  }
  return (
    <Tag
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-72px" }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </Tag>
  );
}

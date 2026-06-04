"use client";

import Link from "next/link";
import { CELL_LABEL, CELL_LIST } from "@/lib/mock-data";
import { cn } from "@/lib/cn";
import type { CellId } from "@/lib/types";

export interface CellNavItem {
  id: CellId;
  label: string;
}

interface CellSelectorProps {
  current?: CellId;
  className?: string;
  /** Cells to offer. Omitted falls back to the full static list (mock mode). */
  items?: CellNavItem[];
}

const FALLBACK_ITEMS: CellNavItem[] = CELL_LIST.map((id) => ({
  id,
  label: CELL_LABEL[id],
}));

export function CellSelector({ current, className, items }: CellSelectorProps) {
  const cells = items && items.length > 0 ? items : FALLBACK_ITEMS;
  return (
    <nav
      aria-label="Select a payer and diagnosis"
      className={cn(
        "flex flex-wrap items-center gap-px overflow-hidden rounded-[3px] border border-border bg-border",
        className,
      )}
    >
      {cells.map(({ id, label }) => {
        const isCurrent = id === current;
        return (
          <Link
            key={id}
            href={`/cell/${id}`}
            aria-current={isCurrent ? "page" : undefined}
            className={cn(
              "px-3 py-1.5 font-mono text-xs transition-colors duration-200",
              isCurrent
                ? "bg-primary text-on-primary"
                : "bg-surface text-ink-muted hover:bg-agar hover:text-ink",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

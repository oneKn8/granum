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
  /**
   * Cells to offer. When omitted, falls back to the full static list (mock
   * mode). Server components pass the live API's served cells here so the nav
   * never links to a cell the deployed API can't render.
   */
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
      aria-label="Select a (payer × diagnosis) cell"
      className={cn(
        "flex flex-wrap items-center gap-px border border-stroke-1 bg-bg-1 p-px",
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
                ? "bg-bg-3 text-fg-0"
                : "bg-bg-1 text-fg-1 hover:bg-bg-2 hover:text-fg-0",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

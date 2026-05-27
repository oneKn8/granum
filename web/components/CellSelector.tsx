"use client";

import Link from "next/link";
import { CELL_LABEL, CELL_LIST } from "@/lib/mock-data";
import type { CellId } from "@/lib/types";

interface CellSelectorProps {
  current?: CellId;
  className?: string;
}

export function CellSelector({ current, className = "" }: CellSelectorProps) {
  return (
    <nav
      aria-label="Select a (payer × diagnosis) cell"
      className={`flex flex-wrap items-center gap-px border border-stroke-1 bg-bg-1 p-px ${className}`}
    >
      {CELL_LIST.map((id) => {
        const isCurrent = id === current;
        return (
          <Link
            key={id}
            href={`/cell/${id}`}
            aria-current={isCurrent ? "page" : undefined}
            className={[
              "px-3 py-1.5 font-mono text-xs transition-colors duration-200",
              isCurrent
                ? "bg-bg-3 text-fg-0"
                : "bg-bg-1 text-fg-1 hover:bg-bg-2 hover:text-fg-0",
            ].join(" ")}
          >
            {CELL_LABEL[id]}
          </Link>
        );
      })}
    </nav>
  );
}

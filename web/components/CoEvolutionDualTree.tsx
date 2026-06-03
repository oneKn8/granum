"use client";

import { LineageTree } from "./LineageTree";
import type { CoEvolutionState, BCellStrategy } from "@/lib/types";

interface CoEvolutionDualTreeProps {
  state: CoEvolutionState;
  selectedId?: string | null;
  onSelect?: (strategy: BCellStrategy) => void;
  height?: number;
}

export function CoEvolutionDualTree({
  state,
  selectedId,
  onSelect,
  height = 360,
}: CoEvolutionDualTreeProps) {
  const isEmpty = state.writers.length === 0 && state.payers.length === 0;

  if (isEmpty) {
    return (
      <section
        className="flex flex-col items-center border border-stroke-1 bg-bg-1 px-6 py-14 text-center"
        aria-label="Co-evolution dual lineage view"
      >
        <p className="font-mono text-[10px] uppercase tracking-widest text-fg-2">
          red queen
        </p>
        <h2 className="mt-3 font-serif text-lg text-fg-0">Co-evolution run pending</h2>
        <p className="mt-2 max-w-prose font-serif text-sm text-fg-1">
          The payer-adversary population hasn&rsquo;t been seeded for this cell yet.
          When a Red&nbsp;Queen run completes, the appeal-writer and payer lineages
          co-evolve here side by side.
        </p>
        <p className="mt-4 font-mono text-xs text-fg-2">
          Meanwhile, the <span className="text-survivor">appeal-writer lineage</span> tab
          shows the live germinal loop.
        </p>
      </section>
    );
  }

  return (
    <section
      className="grid grid-cols-1 gap-4 lg:grid-cols-2"
      aria-label="Co-evolution dual lineage view"
    >
      <LineageTree
        strategies={state.writers}
        caption="Appeal-writer population"
        selectedId={selectedId}
        onSelect={onSelect}
        height={height}
      />
      <LineageTree
        strategies={state.payers}
        caption="Payer-adversary population"
        selectedId={selectedId}
        onSelect={onSelect}
        height={height}
      />
    </section>
  );
}

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

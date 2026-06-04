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
  height = 380,
}: CoEvolutionDualTreeProps) {
  const isEmpty = state.writers.length === 0 && state.payers.length === 0;

  if (isEmpty) {
    return (
      <section
        className="flex flex-col items-center border border-border bg-surface/70 px-6 py-16 text-center"
        aria-label="Co-evolution dual lineage view"
      >
        <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-seed-ink">
          red queen
        </p>
        <h2 className="mt-3 font-display text-lg text-ink fraunces-head">
          The adversary has not been seeded yet
        </h2>
        <p className="mt-2 max-w-prose font-body text-sm text-ink-muted">
          In a Red Queen run, a population of payer denial-strategies evolves at the same time as the
          appeal writers, each one pushing the other to get sharper. Once that run completes for this cell,
          both lineages grow here side by side.
        </p>
        <p className="mt-4 font-mono text-xs text-ink-subtle">
          For now, the <span className="text-alive">appeal lineage</span> tab shows the live germinal loop.
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
        caption="Appeal writers"
        variant="writer"
        selectedId={selectedId}
        onSelect={onSelect}
        height={height}
      />
      <LineageTree
        strategies={state.payers}
        caption="Payer adversaries"
        variant="payer"
        selectedId={selectedId}
        onSelect={onSelect}
        height={height}
      />
    </section>
  );
}

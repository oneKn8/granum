"use client";

import { useState } from "react";
import { LineageTree } from "./LineageTree";
import { PromptDiff } from "./PromptDiff";
import { FitnessCurve } from "./FitnessCurve";
import { CoEvolutionDualTree } from "./CoEvolutionDualTree";
import { cn } from "@/lib/cn";
import type { BCellStrategy, CellPayload, CoEvolutionState } from "@/lib/types";

interface CellDashboardProps {
  payload: CellPayload;
  coEvolution: CoEvolutionState;
}

type ViewMode = "lineage" | "coevolution";

export function CellDashboard({ payload, coEvolution }: CellDashboardProps) {
  const defaultSelected =
    payload.strategies.find((s) => s.status === "champion") ??
    payload.strategies.find((s) => s.status === "alive") ??
    payload.strategies[payload.strategies.length - 1];

  const [selectedId, setSelectedId] = useState<string>(defaultSelected.id);
  const [mode, setMode] = useState<ViewMode>("lineage");

  const selected =
    payload.strategies.find((s) => s.id === selectedId) ?? defaultSelected;
  const parent = selected.parentId
    ? payload.strategies.find((s) => s.id === selected.parentId) ?? null
    : null;

  const handleSelect = (s: BCellStrategy) => setSelectedId(s.id);

  return (
    <div className="flex flex-col gap-6">
      {/* Plain toggle group — not a tab system. Two buttons, aria-pressed. */}
      <div className="inline-flex w-fit border border-stroke-1" role="group" aria-label="Lineage view mode">
        <button
          type="button"
          aria-pressed={mode === "lineage"}
          onClick={() => setMode("lineage")}
          className={cn(
            "px-3 py-1.5 font-mono text-xs transition-colors duration-200",
            mode === "lineage"
              ? "bg-bg-3 text-fg-0"
              : "bg-bg-1 text-fg-1 hover:bg-bg-2 hover:text-fg-0",
          )}
        >
          appeal-writer lineage
        </button>
        <button
          type="button"
          aria-pressed={mode === "coevolution"}
          onClick={() => setMode("coevolution")}
          className={cn(
            "border-l border-stroke-1 px-3 py-1.5 font-mono text-xs transition-colors duration-200",
            mode === "coevolution"
              ? "bg-bg-3 text-fg-0"
              : "bg-bg-1 text-fg-1 hover:bg-bg-2 hover:text-fg-0",
          )}
        >
          co-evolution (writer vs payer)
        </button>
      </div>

      <div
        className="grid grid-cols-1 gap-4 lg:grid-cols-5"
        aria-live="polite"
      >
        {mode === "lineage" ? (
          <>
            <div className="lg:col-span-3">
              <LineageTree
                strategies={payload.strategies}
                selectedId={selected.id}
                onSelect={handleSelect}
                caption="Appeal-writer population"
                height={520}
              />
            </div>
            <div className="lg:col-span-2">
              <PromptDiff parent={parent} mutant={selected} />
            </div>
          </>
        ) : (
          <div className="lg:col-span-5">
            <CoEvolutionDualTree
              state={coEvolution}
              selectedId={selected.id}
              onSelect={handleSelect}
              height={420}
            />
          </div>
        )}
      </div>

      <FitnessCurve
        points={payload.fitness}
        baseline={payload.meta.baselineOverturn}
      />
    </div>
  );
}

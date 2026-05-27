"use client";

import { useState } from "react";
import { LineageTree } from "./LineageTree";
import { PromptDiff } from "./PromptDiff";
import { FitnessCurve } from "./FitnessCurve";
import { CoEvolutionDualTree } from "./CoEvolutionDualTree";
import type { BCellStrategy, CellPayload, CoEvolutionState } from "@/lib/types";

interface CellDashboardProps {
  payload: CellPayload;
  coEvolution: CoEvolutionState;
}

type ViewMode = "lineage" | "coevolution";

export function CellDashboard({ payload, coEvolution }: CellDashboardProps) {
  // Default selection = champion if present, else most recent alive strategy.
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
      {/* View mode toggle */}
      <div
        role="tablist"
        aria-label="Lineage view mode"
        className="inline-flex w-fit border border-stroke-1"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mode === "lineage"}
          onClick={() => setMode("lineage")}
          className={[
            "px-3 py-1.5 font-mono text-xs transition-colors duration-200",
            mode === "lineage"
              ? "bg-bg-3 text-fg-0"
              : "bg-bg-1 text-fg-1 hover:bg-bg-2",
          ].join(" ")}
        >
          appeal-writer lineage
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "coevolution"}
          onClick={() => setMode("coevolution")}
          className={[
            "border-l border-stroke-1 px-3 py-1.5 font-mono text-xs transition-colors duration-200",
            mode === "coevolution"
              ? "bg-bg-3 text-fg-0"
              : "bg-bg-1 text-fg-1 hover:bg-bg-2",
          ].join(" ")}
        >
          co-evolution (writer vs payer)
        </button>
      </div>

      {/* Tree + diff */}
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

      {/* Fitness curve full-width footer */}
      <FitnessCurve
        points={payload.fitness}
        baseline={payload.meta.baselineOverturn}
      />
    </div>
  );
}

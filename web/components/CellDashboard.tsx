"use client";

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { LineageTree } from "./LineageTree";
import { PromptDiff } from "./PromptDiff";
import { FitnessCurve } from "./FitnessCurve";
import { ImmuneTimeline } from "./ImmuneTimeline";
import { SelfImprovementLoop } from "./SelfImprovementLoop";
import { CoEvolutionDualTree } from "./CoEvolutionDualTree";
import { cn } from "@/lib/cn";
import type { BCellStrategy, CellPayload, CoEvolutionState } from "@/lib/types";

interface CellDashboardProps {
  payload: CellPayload;
  coEvolution: CoEvolutionState;
}

type ViewMode = "lineage" | "coevolution";

export function CellDashboard({ payload, coEvolution }: CellDashboardProps) {
  const reduce = useReducedMotion();
  const defaultSelected =
    payload.strategies.find((s) => s.status === "champion") ??
    payload.strategies.find((s) => s.status === "alive") ??
    payload.strategies[payload.strategies.length - 1] ??
    null;

  const [selectedId, setSelectedId] = useState<string>(defaultSelected?.id ?? "");
  const [mode, setMode] = useState<ViewMode>("lineage");

  // A freshly seeded cell can be listed before its first strategies are
  // written; render a waiting state instead of crashing the page.
  if (!defaultSelected) {
    return (
      <div className="border border-border bg-surface/70 p-6 font-body text-sm text-ink-muted">
        This cell is seeded but has no strategies yet. The lineage appears with the first generation.
      </div>
    );
  }

  const selected = payload.strategies.find((s) => s.id === selectedId) ?? defaultSelected;
  const parent = selected.parentId
    ? payload.strategies.find((s) => s.id === selected.parentId) ?? null
    : null;

  const handleSelect = (s: BCellStrategy) => setSelectedId(s.id);

  return (
    <div className="flex flex-col gap-6">
      <div
        className="inline-flex w-fit overflow-hidden rounded-[3px] border border-border"
        role="group"
        aria-label="Lineage view mode"
      >
        {(
          [
            ["lineage", "appeal lineage"],
            ["coevolution", "writer vs payer"],
          ] as const
        ).map(([key, label], i) => (
          <button
            key={key}
            type="button"
            aria-pressed={mode === key}
            onClick={() => setMode(key)}
            className={cn(
              "px-3.5 py-1.5 font-mono text-xs transition-colors duration-200",
              i > 0 && "border-l border-border",
              mode === key
                ? "bg-primary text-on-primary"
                : "bg-surface text-ink-muted hover:bg-agar hover:text-ink",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div aria-live="polite">
        <AnimatePresence mode="wait" initial={false}>
          {mode === "lineage" ? (
            <motion.div
              key="lineage"
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
              className="grid grid-cols-1 gap-4 lg:grid-cols-5"
            >
              <div className="lg:col-span-3">
                <LineageTree
                  strategies={payload.strategies}
                  selectedId={selected.id}
                  onSelect={handleSelect}
                  caption="Appeal-writer lineage"
                  height={540}
                />
              </div>
              <div className="lg:col-span-2">
                <PromptDiff parent={parent} mutant={selected} />
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="coevolution"
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -8 }}
              transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
            >
              <CoEvolutionDualTree
                state={coEvolution}
                selectedId={selected.id}
                onSelect={handleSelect}
                height={440}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <FitnessCurve points={payload.fitness} baseline={payload.meta.baselineOverturn} />

      <ImmuneTimeline payload={payload} />

      <SelfImprovementLoop payload={payload} />
    </div>
  );
}

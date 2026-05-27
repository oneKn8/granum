"use client";

import { diffWordsWithSpace, type Change } from "diff";
import { useMemo } from "react";
import type { BCellStrategy } from "@/lib/types";

interface PromptDiffProps {
  parent: BCellStrategy | null;
  mutant: BCellStrategy;
}

function renderSide(changes: Change[], side: "parent" | "mutant") {
  return changes.map((c, i) => {
    if (c.added && side === "parent") return null;
    if (c.removed && side === "mutant") return null;
    if (c.added) {
      return (
        <ins
          key={i}
          className="bg-champion/15 text-champion no-underline"
          aria-label="added in mutant"
        >
          {c.value}
        </ins>
      );
    }
    if (c.removed) {
      return (
        <del
          key={i}
          className="bg-apoptosis/15 text-apoptosis line-through"
          aria-label="removed from parent"
        >
          {c.value}
        </del>
      );
    }
    return <span key={i}>{c.value}</span>;
  });
}

export function PromptDiff({ parent, mutant }: PromptDiffProps) {
  const changes = useMemo(() => {
    if (!parent) return [];
    return diffWordsWithSpace(parent.promptBody, mutant.promptBody);
  }, [parent, mutant]);

  if (!parent) {
    return (
      <section
        className="border border-stroke-1 bg-bg-1 p-4"
        aria-label="Prompt diff (root strategy)"
      >
        <header className="mb-3 flex items-baseline justify-between font-sans text-sm">
          <span className="text-fg-1">Prompt — root strategy</span>
          <span className="font-mono text-xs text-fg-2">gen {mutant.generation}</span>
        </header>
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-fg-0">
          {mutant.promptBody}
        </pre>
      </section>
    );
  }

  const citationsAdded = mutant.citations.filter((c) => !parent.citations.includes(c));
  const citationsRemoved = parent.citations.filter((c) => !mutant.citations.includes(c));

  return (
    <section
      className="border border-stroke-1 bg-bg-1 p-4"
      aria-label="Prompt diff between parent and mutant"
    >
      <header className="mb-3 flex items-baseline justify-between font-sans text-sm">
        <span className="text-fg-1">
          Prompt diff —{" "}
          <span className="font-mono text-xs text-fg-2">
            {parent.label} → {mutant.label}
          </span>
        </span>
        <span className="font-mono text-xs text-fg-2">
          fitness {parent.fitness.toFixed(2)} → {mutant.fitness.toFixed(2)}
        </span>
      </header>

      {mutant.mutationNote && (
        <p
          className="mb-3 border-l border-stroke-2 bg-bg-2/40 px-3 py-2 font-mono text-xs text-fg-1"
          role="note"
        >
          mutation · {mutant.mutationNote}
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-fg-2">
            parent · gen {parent.generation}
          </div>
          <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-fg-0">
            {renderSide(changes, "parent")}
          </pre>
        </div>
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-fg-2">
            mutant · gen {mutant.generation}
          </div>
          <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-fg-0">
            {renderSide(changes, "mutant")}
          </pre>
        </div>
      </div>

      {(citationsAdded.length > 0 || citationsRemoved.length > 0) && (
        <div className="mt-4 border-t border-stroke-1 pt-3">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-fg-2">
            citation delta
          </div>
          <ul className="space-y-1 font-mono text-xs">
            {citationsAdded.map((c) => (
              <li key={`add-${c}`} className="text-champion">
                + {c}
              </li>
            ))}
            {citationsRemoved.map((c) => (
              <li key={`del-${c}`} className="text-apoptosis line-through">
                − {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

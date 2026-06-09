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
          className="bg-primary-tint text-primary-strong no-underline decoration-clone"
          aria-label="added in this strategy"
        >
          {c.value}
        </ins>
      );
    }
    if (c.removed) {
      return (
        <del
          key={i}
          className="bg-removed-tint text-removed line-through decoration-clone"
          aria-label="removed from the parent"
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
      <section className="border border-border bg-surface/70 p-4" aria-label="Strategy prompt (the seed)">
        <header className="mb-3 flex items-baseline justify-between font-body text-sm">
          <span className="font-medium text-ink">The seed strategy</span>
          <span className="font-mono text-xs text-ink-subtle">gen {mutant.generation}</span>
        </header>
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-ink">
          {mutant.promptBody}
        </pre>
      </section>
    );
  }

  const citationsAdded = mutant.citations.filter((c) => !parent.citations.includes(c));
  const citationsRemoved = parent.citations.filter((c) => !mutant.citations.includes(c));

  return (
    <section className="border border-border bg-surface/70 p-4" aria-label="What changed from parent to this strategy">
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 font-body text-sm">
        <span className="font-medium text-ink">
          What changed{" "}
          <span className="font-mono text-xs font-normal text-ink-subtle">
            {parent.label} <span aria-hidden>→</span> {mutant.label}
          </span>
        </span>
        <span className="font-mono text-xs text-ink-subtle">
          {mutant.status === "alive" && mutant.fitness === 0 ? (
            // A daughter on the live frontier has not been judged yet;
            // "0.00" would read as a collapse, not a pending tournament.
            <>fitness {parent.fitness.toFixed(2)} <span aria-hidden>→</span> awaiting judge</>
          ) : (
            <>
              fitness {parent.fitness.toFixed(2)} <span aria-hidden>→</span>{" "}
              <span className="text-champion-ink">{mutant.fitness.toFixed(2)}</span>
            </>
          )}
        </span>
      </header>

      {mutant.mutationNote && (
        <p
          className="mb-3 border-l-2 border-primary/40 bg-primary-tint/50 px-3 py-2 font-mono text-xs text-ink-muted"
          role="note"
        >
          this mutation: {mutant.mutationNote}
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
            parent · gen {parent.generation}
          </div>
          <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-ink">
            {renderSide(changes, "parent")}
          </pre>
        </div>
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
            this strategy · gen {mutant.generation}
          </div>
          <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-ink">
            {renderSide(changes, "mutant")}
          </pre>
        </div>
      </div>

      {(citationsAdded.length > 0 || citationsRemoved.length > 0) && (
        <div className="mt-4 border-t border-border pt-3">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
            citations it learned to cite
          </div>
          <ul className="space-y-1 font-mono text-xs">
            {citationsAdded.map((c) => (
              <li key={`add-${c}`} className="text-primary-strong">
                + {c}
              </li>
            ))}
            {citationsRemoved.map((c) => (
              <li key={`del-${c}`} className="text-removed line-through">
                − {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

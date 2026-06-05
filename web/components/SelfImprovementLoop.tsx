"use client";

import { useMemo } from "react";
import { motion, useReducedMotion } from "motion/react";
import type { BCellStrategy, CellPayload } from "@/lib/types";

interface SelfImprovementLoopProps {
  payload: CellPayload;
}

interface ReadbackStep {
  from: number;
  to: number;
  /** The judge critique its OWN run recorded as telemetry at generation `from`. */
  critique: string;
  /** What the mutator bred in response at generation `to`. */
  mutation: string;
  fitnessBefore: number;
  fitnessAfter: number;
}

/**
 * Surfaces the Arize self-improvement loop in the product itself: before each
 * generation, Granum reads its own Phoenix telemetry back (the judge critique it
 * recorded) and the mutator optimizes against the weakness that telemetry reveals.
 * Built entirely from the CellPayload the API already serves — `rounds[].judgeRationale`
 * (the telemetry) paired with the next generation's winning `mutationNote` (the response).
 */
export function SelfImprovementLoop({ payload }: SelfImprovementLoopProps) {
  const reduce = useReducedMotion();

  const steps = useMemo<ReadbackStep[]>(() => {
    const roundByGen = new Map(payload.rounds.map((r) => [r.generation, r]));
    const fitByGen = new Map(payload.fitness.map((f) => [f.generation, f]));

    // Best (highest-fitness) strategy per generation = the lineage that carried forward.
    const bestByGen = new Map<number, BCellStrategy>();
    for (const s of payload.strategies) {
      const cur = bestByGen.get(s.generation);
      if (!cur || s.fitness > cur.fitness) bestByGen.set(s.generation, s);
    }

    const gens = [...fitByGen.keys()].sort((a, b) => a - b);
    const out: ReadbackStep[] = [];
    for (let i = 0; i < gens.length - 1; i++) {
      const from = gens[i];
      const to = gens[i + 1];
      const round = roundByGen.get(from);
      const next = bestByGen.get(to);
      if (!round?.judgeRationale || !next) continue;
      out.push({
        from,
        to,
        critique: round.judgeRationale.trim(),
        mutation: (next.mutationNote ?? next.label).trim(),
        fitnessBefore: fitByGen.get(from)?.maxFitness ?? 0,
        fitnessAfter: fitByGen.get(to)?.maxFitness ?? 0,
      });
    }
    return out;
  }, [payload]);

  if (steps.length === 0) return null;

  const first = steps[0].fitnessBefore;
  const last = steps[steps.length - 1].fitnessAfter;
  const climbed = last - first;

  return (
    <section
      aria-label="How Granum reads its own observability data to improve"
      className="border border-border bg-surface/70 p-5"
    >
      <header className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="max-w-prose">
          <h2 className="font-body text-lg font-medium text-ink">
            It reads its own telemetry to improve.
          </h2>
          <p className="mt-1.5 font-body text-sm leading-relaxed text-ink-muted">
            Before breeding each new generation, Granum calls Phoenix{" "}
            <code className="font-mono text-xs text-ink">get-spans</code> to read back the
            judge critique its own runs recorded — then the mutator optimizes against the
            weakness that telemetry surfaces. Champion fitness climbed{" "}
            <span className="font-mono text-champion-ink">{first.toFixed(2)}</span>
            <span aria-hidden> → </span>
            <span className="font-mono text-champion-ink">{last.toFixed(2)}</span>{" "}
            <span className="font-mono text-xs text-ink-subtle">
              (+{climbed.toFixed(2)})
            </span>
            , each step driven by the generation before it.
          </p>
        </div>
        <span className="inline-flex w-fit shrink-0 items-center gap-1.5 rounded-[3px] border border-primary/30 bg-primary-tint/50 px-2.5 py-1 font-mono text-[11px] text-primary-strong">
          <span aria-hidden>◆</span> Phoenix MCP · get-spans
        </span>
      </header>

      <motion.ol
        className="flex flex-col gap-3"
        initial={reduce ? false : "hidden"}
        whileInView={reduce ? undefined : "shown"}
        viewport={{ once: true, margin: "-40px" }}
        variants={{ shown: { transition: { staggerChildren: 0.06 } } }}
      >
        {steps.map((step) => {
          const delta = step.fitnessAfter - step.fitnessBefore;
          return (
            <motion.li
              key={`${step.from}-${step.to}`}
              variants={{
                hidden: { opacity: 0, y: 8 },
                shown: {
                  opacity: 1,
                  y: 0,
                  transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] },
                },
              }}
              className="border-l-2 border-border pl-4"
            >
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
                  generation {step.from} <span aria-hidden>→</span> {step.to}
                </span>
                <span className="font-mono text-xs text-ink-subtle">
                  fitness {step.fitnessBefore.toFixed(2)} <span aria-hidden>→</span>{" "}
                  <span className="text-champion-ink">{step.fitnessAfter.toFixed(2)}</span>
                  {delta > 0 && (
                    <span className="ml-1.5 text-champion-ink">
                      +{delta.toFixed(2)}
                    </span>
                  )}
                </span>
              </div>

              <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
                its telemetry flagged
              </p>
              <p className="mt-1 border-l-2 border-border/60 pl-3 font-body text-sm leading-relaxed text-ink-muted">
                {step.critique}
              </p>

              <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-subtle">
                so the next generation
              </p>
              <p
                className="mt-1 border-l-2 border-primary/40 bg-primary-tint/40 px-3 py-2 font-mono text-xs text-ink"
                role="note"
              >
                <span aria-hidden>→ </span>
                {step.mutation}
              </p>
            </motion.li>
          );
        })}
      </motion.ol>
    </section>
  );
}

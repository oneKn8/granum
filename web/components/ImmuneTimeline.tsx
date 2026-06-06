"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/cn";
import type { BCellStrategy, CellPayload } from "@/lib/types";

interface ImmuneTimelineProps {
  payload: CellPayload;
}

/** One generation's worth of immune-system events, derived from the run record. */
interface GenEvents {
  generation: number;
  /** Strategies whose birth generation is this one (mutants, or seeds at gen 0). */
  bred: BCellStrategy[];
  isSeed: boolean;
  /** Tournament winner this generation. */
  winner: BCellStrategy | null;
  candidateCount: number;
  judgeRationale: string | null;
  /** Strategies tombstoned this generation (the round's losers). */
  apoptosed: BCellStrategy[];
  /** A new lineage took the crown this generation. */
  crowned: boolean;
  /** The strategy displaced by the new crown (null on the first coronation). */
  dethroned: BCellStrategy | null;
  maxFitness: number;
  fitnessDelta: number;
}

const short = (s: BCellStrategy) => s.id.split("__").pop() ?? s.id;

/**
 * The population, generation by generation — the immune system's life-and-death
 * chronicle. Where the self-improvement panel explains *why* fitness climbed, this
 * shows *what happened to the population*: who was bred, who won the tournament, who
 * apoptosed, and when a descendant dethroned the reigning champion. Built entirely
 * from the CellPayload the API already serves (strategies + rounds + fitness) — the
 * round's losers are exactly that generation's apoptosis (count matches apoptosisCount).
 */
export function ImmuneTimeline({ payload }: ImmuneTimelineProps) {
  const reduce = useReducedMotion();

  const gens = useMemo<GenEvents[]>(() => {
    const byId = new Map(payload.strategies.map((s) => [s.id, s]));
    const bredByGen = new Map<number, BCellStrategy[]>();
    for (const s of payload.strategies) {
      const arr = bredByGen.get(s.generation) ?? [];
      arr.push(s);
      bredByGen.set(s.generation, arr);
    }
    const roundByGen = new Map(payload.rounds.map((r) => [r.generation, r]));
    const fitByGen = new Map(payload.fitness.map((f) => [f.generation, f]));

    const order = [...fitByGen.keys()].sort((a, b) => a - b);
    let prevWinnerId: string | null = null;
    let prevMax = payload.meta.baselineOverturn;

    return order.map((g) => {
      const round = roundByGen.get(g);
      const fit = fitByGen.get(g);
      const winner = round ? byId.get(round.winnerId) ?? null : null;
      const apoptosed = (round?.loserIds ?? [])
        .map((id) => byId.get(id))
        .filter((s): s is BCellStrategy => Boolean(s));
      const crowned = Boolean(winner) && winner!.id !== prevWinnerId;
      const dethroned =
        crowned && prevWinnerId ? byId.get(prevWinnerId) ?? null : null;
      const maxFitness = fit?.maxFitness ?? prevMax;
      const out: GenEvents = {
        generation: g,
        bred: bredByGen.get(g) ?? [],
        isSeed: g === order[0],
        winner,
        candidateCount: round?.candidateIds.length ?? 0,
        judgeRationale: round?.judgeRationale?.trim() ?? null,
        apoptosed,
        crowned,
        dethroned,
        maxFitness,
        fitnessDelta: maxFitness - prevMax,
      };
      if (winner) prevWinnerId = winner.id;
      prevMax = maxFitness;
      return out;
    });
  }, [payload]);

  // Default to the most dramatic generation (largest fitness jump) — the money moment.
  const defaultGen = useMemo(() => {
    if (gens.length === 0) return 0;
    return gens.reduce((best, g) => (g.fitnessDelta > best.fitnessDelta ? g : best))
      .generation;
  }, [gens]);

  const [selected, setSelected] = useState<number>(defaultGen);
  if (gens.length === 0) return null;

  const active = gens.find((g) => g.generation === selected) ?? gens[0];

  const move = (dir: -1 | 1) => {
    const idx = gens.findIndex((g) => g.generation === selected);
    const next = gens[Math.min(gens.length - 1, Math.max(0, idx + dir))];
    if (next) setSelected(next.generation);
  };

  return (
    <section
      aria-label="The appeal population, generation by generation"
      className="border border-border bg-surface/70 p-5"
    >
      <header className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="max-w-prose">
          <h2 className="font-body text-lg font-medium text-ink">
            The population, generation by generation.
          </h2>
          <p className="mt-1.5 font-body text-sm leading-relaxed text-ink-muted">
            Every generation Granum breeds variant appeals, judges them head to head,
            and lets the weakest die. Pick a generation to see who was bred, who won,
            who apoptosed, and when a descendant took the crown.
          </p>
        </div>
        <Legend />
      </header>

      {/* Swimlane: lane labels + one clickable column per generation.
          overflow-y must be clipped: overflow-x:auto alone computes overflow-y to
          auto, which spawns a stray vertical scrollbar. py gives the focus ring room. */}
      <div className="overflow-x-auto overflow-y-clip px-0.5 py-1">
        <div
          role="group"
          aria-label="Generations"
          className="flex min-w-max items-stretch gap-1.5"
        >
          <LaneLabels />
          <motion.div
            className="flex items-stretch gap-1.5"
            initial={reduce ? false : "hidden"}
            animate={reduce ? undefined : "shown"}
            variants={{ shown: { transition: { staggerChildren: 0.035 } } }}
          >
            {gens.map((g) => (
              <GenColumn
                key={g.generation}
                g={g}
                selected={g.generation === selected}
                reduce={Boolean(reduce)}
                onSelect={() => setSelected(g.generation)}
                onMove={move}
              />
            ))}
          </motion.div>
        </div>
      </div>

      {/* Detail for the selected generation. */}
      <div aria-live="polite" className="mt-5">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={active.generation}
            initial={reduce ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? undefined : { opacity: 0, y: -6 }}
            transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
          >
            <GenDetail g={active} />
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- markers */

function Dot({ kind }: { kind: "bred" | "seed" | "dead" | "crown" }) {
  if (kind === "dead") {
    return (
      <span className="relative inline-block h-[9px] w-[9px]" aria-hidden>
        <span className="absolute inset-0 rounded-full border-[1.5px] border-dead" />
        <span className="absolute left-1/2 top-1/2 h-px w-[11px] -translate-x-1/2 -translate-y-1/2 rotate-45 bg-dead" />
      </span>
    );
  }
  if (kind === "crown") {
    return (
      <span className="relative inline-block h-[10px] w-[10px]" aria-hidden>
        <span className="absolute inset-0 rounded-full bg-champion" />
        <span className="absolute -inset-[3px] rounded-full border-[1.5px] border-champion/70" />
      </span>
    );
  }
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-[9px] w-[9px] rounded-full",
        kind === "seed" ? "bg-seed" : "bg-mutant",
      )}
    />
  );
}

/** Diamond marking that a tournament ran this generation. */
function JudgeMark() {
  return (
    <span
      aria-hidden
      className="h-[8px] w-[8px] rotate-45 border-[1.5px] border-ink-subtle/60 bg-ink-subtle/15"
    />
  );
}

// Lane row heights — shared between the labels column and every generation column
// so the swimlane grid stays aligned. Keep these in lockstep.
const GEN_H = "h-6";
const LANE_H = "h-7";
const FIT_H = "h-14";

function LaneLabels() {
  const lanes = ["bred", "judged", "apoptosed", "crowned"];
  return (
    <div className="flex shrink-0 flex-col gap-1.5 pr-2.5 text-right">
      <div className={GEN_H} aria-hidden />
      {lanes.map((l) => (
        <div
          key={l}
          className={cn(
            LANE_H,
            "flex items-center justify-end font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle",
          )}
        >
          {l}
        </div>
      ))}
      <div
        className={cn(
          FIT_H,
          "flex items-end justify-end pb-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle",
        )}
      >
        fitness
      </div>
    </div>
  );
}

function GenColumn({
  g,
  selected,
  reduce,
  onSelect,
  onMove,
}: {
  g: GenEvents;
  selected: boolean;
  reduce: boolean;
  onSelect: () => void;
  onMove: (dir: -1 | 1) => void;
}) {
  // Bar height maps to absolute fitness (0..1) so the column heights read as the
  // real climb, echoing the fitness curve above at per-generation granularity.
  const barPct = Math.max(0.04, Math.min(1, g.maxFitness));
  const summary = [
    `generation ${g.generation}`,
    g.isSeed ? `${g.bred.length} seeds planted` : `${g.bred.length} bred`,
    g.apoptosed.length ? `${g.apoptosed.length} apoptosed` : null,
    g.crowned ? "new champion crowned" : null,
    `fitness ${g.maxFitness.toFixed(2)}`,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <motion.button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={summary}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight") {
          e.preventDefault();
          onMove(1);
        } else if (e.key === "ArrowLeft") {
          e.preventDefault();
          onMove(-1);
        }
      }}
      variants={{
        hidden: { opacity: 0, y: 8 },
        shown: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] },
        },
      }}
      className={cn(
        "flex w-11 shrink-0 flex-col items-center gap-1.5 rounded-[4px] border px-1 py-1.5 transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        selected
          ? "border-primary/55 bg-primary-tint/60"
          : "border-transparent hover:bg-agar",
      )}
    >
      <span
        className={cn(
          GEN_H,
          "flex items-center font-mono text-[11px]",
          selected ? "font-medium text-primary-strong" : "text-ink-muted",
        )}
      >
        {g.generation}
      </span>

      {/* bred */}
      <span className={cn(LANE_H, "flex items-center justify-center gap-[3px]")}>
        {g.bred.slice(0, 3).map((s) => (
          <Dot key={s.id} kind={g.isSeed ? "seed" : "bred"} />
        ))}
      </span>

      {/* judged — a diamond marks that a tournament ran */}
      <span className={cn(LANE_H, "flex items-center justify-center")}>
        <JudgeMark />
      </span>

      {/* apoptosed */}
      <span className={cn(LANE_H, "flex items-center justify-center gap-[3px]")}>
        {g.apoptosed.length === 0 ? (
          <Empty />
        ) : (
          g.apoptosed.slice(0, 3).map((s) => <Dot key={s.id} kind="dead" />)
        )}
      </span>

      {/* crowned */}
      <span className={cn(LANE_H, "flex items-center justify-center")}>
        {g.crowned ? <Dot kind="crown" /> : <Empty />}
      </span>

      {/* fitness micro bar-chart, with a track so even low bars read */}
      <span
        className={cn(
          FIT_H,
          "flex w-full items-end justify-center rounded-[2px] bg-well/70 px-1 pt-1",
        )}
      >
        <motion.span
          aria-hidden
          className={cn(
            "w-2.5 origin-bottom rounded-t-[2px]",
            selected ? "bg-champion" : "bg-champion/80",
          )}
          style={{ height: `${barPct * 100}%` }}
          initial={reduce ? false : { scaleY: 0 }}
          animate={reduce ? undefined : { scaleY: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
      </span>
    </motion.button>
  );
}

/** Faint placeholder when a lane has no event this generation. */
function Empty() {
  return (
    <span aria-hidden className="h-[3px] w-[3px] rounded-full bg-ink-subtle/25" />
  );
}

/* ---------------------------------------------------------------- detail */

function GenDetail({ g }: { g: GenEvents }) {
  const delta = g.fitnessDelta;
  return (
    <div className="border-l-2 border-primary/40 pl-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h3 className="font-body text-base font-medium text-ink">
          Generation {g.generation}
        </h3>
        <span className="font-mono text-xs text-ink-subtle">
          fitness{" "}
          <span className="text-champion-ink">{g.maxFitness.toFixed(2)}</span>
          {Math.abs(delta) >= 0.005 && (
            <span className={delta > 0 ? "ml-1.5 text-champion-ink" : "ml-1.5 text-ink-subtle"}>
              ({delta > 0 ? "+" : ""}
              {delta.toFixed(2)})
            </span>
          )}
        </span>
      </div>

      <dl className="flex flex-col gap-3">
        <Row label={g.isSeed ? "planted" : "bred"} dotKind={g.isSeed ? "seed" : "bred"}>
          {g.bred.length === 0 ? (
            <span className="text-ink-subtle">no new variants</span>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {g.bred.map((s) => {
                const parent = s.parentId;
                return (
                  <li key={s.id}>
                    <span className="font-mono text-ink">{short(s)}</span>
                    {parent && (
                      <span className="text-ink-subtle">
                        {" "}
                        <span aria-hidden>←</span> {parent.split("__").pop()}
                      </span>
                    )}
                    {s.mutationNote && (
                      <span className="text-ink-muted"> · {s.mutationNote}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </Row>

        <Row label="judged" dotKind="judge">
          {g.winner ? (
            <>
              <p>
                <span className="font-mono text-ink">{g.candidateCount}</span> candidates
                judged head to head{" "}
                <span aria-hidden>→</span>{" "}
                <span className="font-mono text-champion-ink">{short(g.winner)}</span> won
              </p>
              {g.judgeRationale && (
                <p className="mt-1.5 border-l-2 border-border/60 pl-3 text-ink-muted">
                  {g.judgeRationale}
                </p>
              )}
            </>
          ) : (
            <span className="text-ink-subtle">no tournament</span>
          )}
        </Row>

        <Row label="apoptosed" dotKind="dead">
          {g.apoptosed.length === 0 ? (
            <span className="text-ink-subtle">none — first generation</span>
          ) : (
            <span>
              <span className="font-mono text-dead-ink">{g.apoptosed.length}</span>{" "}
              strateg{g.apoptosed.length === 1 ? "y" : "ies"} lysed:{" "}
              <span className="font-mono text-ink-muted">
                {g.apoptosed.map(short).join(", ")}
              </span>
            </span>
          )}
        </Row>

        {g.crowned && g.winner && (
          <Row label="crowned" dotKind="crown">
            <span>
              <span className="font-mono text-champion-ink">{short(g.winner)}</span>{" "}
              {g.dethroned ? (
                <>
                  took the crown, displacing{" "}
                  <span className="font-mono text-ink-muted">{short(g.dethroned)}</span>
                </>
              ) : (
                "became the first lineage leader"
              )}
            </span>
          </Row>
        )}
      </dl>
    </div>
  );
}

function Row({
  label,
  dotKind,
  children,
}: {
  label: string;
  dotKind: "bred" | "seed" | "dead" | "crown" | "judge";
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-3">
      <dt className="flex w-24 shrink-0 items-center gap-1.5 pt-0.5 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-subtle">
        {dotKind === "judge" ? (
          <span aria-hidden className="h-[7px] w-[7px] rotate-45 border border-ink-subtle/70" />
        ) : (
          <Dot kind={dotKind} />
        )}
        {label}
      </dt>
      <dd className="min-w-0 flex-1 font-body text-sm leading-relaxed text-ink">
        {children}
      </dd>
    </div>
  );
}

function Legend() {
  const items: { kind: "bred" | "dead" | "crown" | "judge"; label: string }[] = [
    { kind: "bred", label: "bred" },
    { kind: "judge", label: "judged" },
    { kind: "dead", label: "apoptosed" },
    { kind: "crown", label: "crowned" },
  ];
  return (
    <ul className="flex w-fit shrink-0 flex-wrap items-center gap-x-3 gap-y-1.5">
      {items.map((it) => (
        <li
          key={it.label}
          className="inline-flex items-center gap-1.5 font-mono text-[11px] text-ink-subtle"
        >
          {it.kind === "judge" ? (
            <span aria-hidden className="h-[7px] w-[7px] rotate-45 border border-ink-subtle/70" />
          ) : (
            <Dot kind={it.kind} />
          )}
          {it.label}
        </li>
      ))}
    </ul>
  );
}

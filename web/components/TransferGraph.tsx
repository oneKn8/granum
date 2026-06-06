"use client";

import { useMemo } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/cn";
import type { CellMeta, TransferEdge } from "@/lib/types";

interface TransferGraphProps {
  edges: TransferEdge[];
  cells: CellMeta[];
}

interface Node {
  id: string;
  label: string;
  /** Champion appeal fitness (0-1) for the cell, shown inside the node. */
  fitness: number;
  x: number;
  y: number;
}

const fmt = (v: number) => (v / 10).toFixed(2); // composite 0-10 -> fitness 0-1

/**
 * Cross-cell transfer — clonal selection across cells. A champion strategy bred
 * against one payer is trialed against another payer's denials; the matured
 * STRATEGY (not its payer-specific citations) carries over, and the edge is
 * promoted only when it significantly lifts the target's naive baseline
 * (one-tailed t-test p < 0.05 and a >= 1.0 composite-point lift). Built from the
 * /api/transfers artifact the transfer harness produces.
 */
export function TransferGraph({ edges, cells }: TransferGraphProps) {
  const reduce = useReducedMotion();

  const { nodes, byId } = useMemo(() => {
    const ids = Array.from(
      new Set(edges.flatMap((e) => [e.sourceCell, e.targetCell])),
    );
    const metaFor = (id: string) => cells.find((c) => c.id === id);
    const labelFor = (id: string) => {
      const m = metaFor(id);
      if (!m) return id;
      const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
      return `${cap(m.payer)} · ${cap(m.diagnosis)}`;
    };
    // Lay the cells out evenly on a horizontal axis.
    const W = 620;
    const n = Math.max(ids.length, 1);
    const nodes: Node[] = ids.map((id, i) => ({
      id,
      label: labelFor(id),
      fitness: metaFor(id)?.currentOverturn ?? 0,
      x: n === 1 ? W / 2 : 120 + (i * (W - 240)) / (n - 1),
      y: 66,
    }));
    const byId = new Map(nodes.map((node) => [node.id, node]));
    return { nodes, byId };
  }, [edges, cells]);

  if (edges.length === 0) return null;

  const promotedCount = edges.filter((e) => e.promoted).length;

  return (
    <section
      aria-label="Cross-cell strategy transfer"
      className="border border-border bg-surface/70 p-5"
    >
      <header className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="max-w-prose">
          <h2 className="font-body text-lg font-medium text-ink">
            Strategies that transfer across cells.
          </h2>
          <p className="mt-1.5 font-body text-sm leading-relaxed text-ink-muted">
            A champion matured against one payer is trialed against another payer&apos;s
            denials. The payer-specific citations don&apos;t carry over — negative
            selection runs on the appeal it writes in the new cell — but the matured{" "}
            <em>strategy</em> does. An edge is promoted only when it significantly lifts
            the target&apos;s naive baseline.
          </p>
        </div>
        <span className="inline-flex w-fit shrink-0 items-center gap-1.5 rounded-[3px] border border-champion/40 bg-champion/10 px-2.5 py-1 font-mono text-[11px] text-champion-ink">
          <span aria-hidden>↯</span> {promotedCount} promoted transfer
          {promotedCount === 1 ? "" : "s"}
        </span>
      </header>

      {/* Node-and-edge diagram. */}
      <div className="mx-auto max-w-xl overflow-x-auto">
        <svg
          viewBox="0 0 620 150"
          className="h-auto w-full min-w-[480px]"
          role="img"
          aria-label="Transfer graph: cells as nodes, promoted transfers as arrows"
        >
          <defs>
            <marker
              id="tg-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 z" fill="var(--color-champion-ink)" />
            </marker>
            <marker
              id="tg-arrow-dim"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0,0 L10,5 L0,10 z" fill="var(--color-dead)" />
            </marker>
          </defs>

          {edges.map((e, i) => {
            const s = byId.get(e.sourceCell);
            const t = byId.get(e.targetCell);
            if (!s || !t) return null;
            // Bow the path up or down so opposite-direction edges don't overlap.
            const dir = s.x <= t.x ? 1 : -1;
            const bow = (dir > 0 ? -1 : 1) * 42;
            const mx = (s.x + t.x) / 2;
            const my = s.y + bow;
            const sx = s.x + dir * 34;
            const tx = t.x - dir * 34;
            const d = `M ${sx} ${s.y} Q ${mx} ${my} ${tx} ${t.y}`;
            const live = e.promoted;
            return (
              <g key={`${e.sourceCell}-${e.targetCell}`}>
                <motion.path
                  d={d}
                  fill="none"
                  stroke={live ? "var(--color-champion-ink)" : "var(--color-dead)"}
                  strokeWidth={live ? 2.75 : 1.5}
                  strokeDasharray={live ? undefined : "3 4"}
                  markerEnd={`url(#${live ? "tg-arrow" : "tg-arrow-dim"})`}
                  initial={reduce ? false : { pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 0.7, delay: 0.2 + i * 0.15, ease: "easeInOut" }}
                />
                <text
                  x={mx}
                  y={my + (bow < 0 ? -7 : 16)}
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                  fontSize="12"
                  fontWeight={live ? 600 : 400}
                  fill={live ? "var(--color-champion-ink)" : "var(--color-ink-subtle)"}
                >
                  {live ? `+${fmt(e.lift)} lift · p=${e.pValue.toFixed(3)}` : "no significant lift"}
                </text>
              </g>
            );
          })}

          {nodes.map((node) => (
            <g key={node.id}>
              <circle
                cx={node.x}
                cy={node.y}
                r="27"
                fill="var(--color-champion)"
                opacity="0.16"
              />
              <circle
                cx={node.x}
                cy={node.y}
                r="27"
                fill="none"
                stroke="var(--color-champion)"
                strokeWidth="2"
              />
              <text
                x={node.x}
                y={node.y}
                textAnchor="middle"
                dominantBaseline="central"
                fontFamily="var(--font-mono)"
                fontSize="14"
                fill="var(--color-champion-ink)"
              >
                {node.fitness.toFixed(2)}
              </text>
              <text
                x={node.x}
                y={node.y + 48}
                textAnchor="middle"
                fontFamily="var(--font-body)"
                fontSize="13"
                fontWeight="500"
                fill="var(--color-ink)"
              >
                {node.label}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* Per-edge detail. */}
      <ul className="mt-5 flex flex-col gap-3">
        {edges.map((e) => (
          <li
            key={`d-${e.sourceCell}-${e.targetCell}`}
            className={cn(
              "border-l-2 pl-4",
              e.promoted ? "border-champion/50" : "border-border",
            )}
          >
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="font-mono text-sm text-ink">
                <span className="text-champion-ink">{e.sourceStrategy}</span>{" "}
                <span className="text-ink-subtle">({e.sourceCell.split("_")[0]})</span>{" "}
                <span aria-hidden>→</span> {e.targetCell.split("_")[0]}
              </span>
              <span
                className={cn(
                  "rounded-[3px] px-2 py-0.5 font-mono text-[11px]",
                  e.promoted
                    ? "bg-champion/15 text-champion-ink"
                    : "bg-well text-ink-subtle",
                )}
              >
                {e.promoted ? "promoted" : "rejected"}
              </span>
            </div>
            <p className="mt-1.5 font-body text-sm leading-relaxed text-ink-muted">
              Scored{" "}
              <span className="font-mono text-champion-ink">{fmt(e.meanScore)}</span> on{" "}
              {e.targetCell.split("_")[0]}&apos;s denials versus its naive baseline{" "}
              <span className="font-mono">{fmt(e.baselineScore)}</span>
              {e.promoted ? (
                <>
                  {" "}
                  — a <span className="font-mono text-champion-ink">+{fmt(e.lift)}</span>{" "}
                  lift, significant at{" "}
                  <span className="font-mono">p={e.pValue.toFixed(3)}</span>. The matured
                  strategy writes better appeals in a payer it never trained on.
                </>
              ) : (
                <>
                  {" "}
                  — not a significant lift (
                  <span className="font-mono">p={e.pValue.toFixed(3)}</span>
                  {e.negativeSelectionFailures > 0
                    ? `, ${e.negativeSelectionFailures}/${e.samples.length} rejected at negative selection`
                    : ""}
                  ). This strategy is clonally specific to its own cell.
                </>
              )}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

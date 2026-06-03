"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { hierarchy, tree, type HierarchyPointNode } from "d3-hierarchy";
import { select } from "d3-selection";
import { zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { linkHorizontal } from "d3-shape";
import type { BCellStrategy } from "@/lib/types";

interface LineageTreeProps {
  strategies: BCellStrategy[];
  selectedId?: string | null;
  onSelect?: (strategy: BCellStrategy) => void;
  /** Title rendered above the tree, e.g. "Appeal-writer population". */
  caption?: string;
  /** Pixel height of the SVG. */
  height?: number;
  /** Render-as-card flag — wraps the tree in a panel surface. */
  framed?: boolean;
}

interface TreeDatum {
  strategy: BCellStrategy;
  children: TreeDatum[];
}

/** Horizontal pixels per generation (one x-column per generation of evolution). */
const GEN_SPACING = 104;

/**
 * Compact form for an inline tree label. Strips the redundant "G8 —" / "L3 —"
 * generation prefix (generation is shown on the axis and the f=… sub-line) and
 * truncates long real-world labels. The full label lives in the PromptDiff
 * panel and the node's aria-label, so nothing is lost — the tree stays legible.
 */
function shortLabel(label: string): string {
  const stripped = label.replace(/^[GL][\d.]*\s*[—–-]\s*/i, "").trim() || label;
  return stripped.length > 30 ? `${stripped.slice(0, 29).trimEnd()}…` : stripped;
}

function buildHierarchy(strategies: BCellStrategy[]): TreeDatum | null {
  const byId = new Map<string, TreeDatum>();
  for (const s of strategies) byId.set(s.id, { strategy: s, children: [] });
  let root: TreeDatum | null = null;
  for (const s of strategies) {
    const node = byId.get(s.id)!;
    if (s.parentId === null) {
      root = node;
    } else {
      const parent = byId.get(s.parentId);
      if (parent) parent.children.push(node);
    }
  }
  return root;
}

// Node color is semantic, per DESIGN.md §4 (single-accent + biology-stain rule):
//   champion           → hematoxylin amber (promoted to production)
//   tombstoned         → desaturated grey  (apoptosed; the permanent record)
//   alive + experimental → methyl-violet magenta (the live "mutant" tag)
//   alive + production   → eosin blue       (surviving lineage, the primary accent)
function nodeColor(s: BCellStrategy): string {
  if (s.status === "champion") return "var(--color-champion)";
  if (s.status === "tombstoned") return "var(--color-fg-tomb)";
  if (s.tag === "experimental") return "var(--color-mutant)";
  return "var(--color-survivor)";
}

// Fitter strategies render larger, so the climb is visible spatially.
function nodeRadius(s: BCellStrategy): number {
  if (s.status === "champion") return 9;
  const base = 4.2 + (s.fitness ?? 0) * 3.6;
  if (s.status === "tombstoned") return Math.max(3.4, base - 1.4);
  return base;
}

export function LineageTree({
  strategies,
  selectedId,
  onSelect,
  caption,
  height = 480,
  framed = true,
}: LineageTreeProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  // Live zoom transform — drives the HTML annotation overlay so the seed and
  // champion pills track the nodes as you pan/zoom and stay crisp at any scale.
  const [view, setView] = useState({ x: 0, y: 0, k: 1, ready: false });

  const layout = useMemo(() => {
    const rootDatum = buildHierarchy(strategies);
    if (!rootDatum) return null;
    const root = hierarchy<TreeDatum>(rootDatum);
    const layoutFn = tree<TreeDatum>().nodeSize([58, GEN_SPACING]);
    const laid = layoutFn(root);
    // Position horizontally by GENERATION (time), not lineage depth, so the
    // x-axis reads as generations and a strategy that survives several
    // generations before mutating shows as a longer edge.
    for (const d of laid.descendants()) {
      d.y = d.data.strategy.generation * GEN_SPACING;
    }
    return laid;
  }, [strategies]);

  // The surviving lineage: champion → … → seed (by parentId). Rendered as the
  // bright glowing "spine" so the eye follows the success story end to end.
  const spineIds = useMemo(() => {
    const set = new Set<string>();
    const byId = new Map(strategies.map((s) => [s.id, s]));
    let cur = strategies.find((s) => s.status === "champion");
    let guard = 0;
    while (cur && guard++ < 1000) {
      set.add(cur.id);
      cur = cur.parentId ? byId.get(cur.parentId) : undefined;
    }
    return set;
  }, [strategies]);

  const genColumns = useMemo(() => {
    if (!layout) return [];
    const byGen = new Map<number, number>();
    for (const n of layout.descendants()) byGen.set(n.data.strategy.generation, n.y);
    return Array.from(byGen.entries())
      .map(([generation, y]) => ({ generation, y }))
      .sort((a, b) => a.y - b.y);
  }, [layout]);

  const bbox = useMemo(() => {
    if (!layout) return null;
    const nodes = layout.descendants();
    if (nodes.length === 0) return null;
    let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
    for (const n of nodes) {
      if (n.x < xMin) xMin = n.x;
      if (n.x > xMax) xMax = n.x;
      if (n.y < yMin) yMin = n.y;
      if (n.y > yMax) yMax = n.y;
    }
    return { xMin, xMax, yMin, yMax };
  }, [layout]);

  // d3-zoom: pan + zoom on the SVG. Initial transform fits the tree, then the
  // transform is mirrored into React state for the annotation overlay.
  useEffect(() => {
    const svgEl = svgRef.current;
    const gEl = gRef.current;
    if (!svgEl || !gEl || !bbox) return;
    const width = svgEl.clientWidth || 800;
    const padding = 64;
    const labelPad = 210;
    const treeW = bbox.yMax - bbox.yMin + padding * 2 + labelPad;
    const treeH = bbox.xMax - bbox.xMin + padding * 2;
    const scale = Math.min(width / treeW, height / treeH, 1);
    const tx = padding * scale - bbox.yMin * scale;
    const ty = height / 2 - ((bbox.xMin + bbox.xMax) / 2) * scale;
    const svg = select(svgEl);
    const g = select(gEl);
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on("zoom", (event: D3ZoomEvent<SVGSVGElement, unknown>) => {
        const t = event.transform;
        g.attr("transform", t.toString());
        setView({ x: t.x, y: t.y, k: t.k, ready: true });
      });
    svg.call(zoomBehavior);
    svg.call(zoomBehavior.transform, zoomIdentity.translate(tx, ty).scale(scale));
    return () => {
      svg.on(".zoom", null);
    };
  }, [height, bbox]);

  if (!layout) return null;

  const nodes = layout.descendants();
  const links = layout.links();
  const linkPath = linkHorizontal<
    { source: HierarchyPointNode<TreeDatum>; target: HierarchyPointNode<TreeDatum> },
    HierarchyPointNode<TreeDatum>
  >()
    .x((d) => d.y)
    .y((d) => d.x);

  const championNode = nodes.find((n) => n.data.strategy.status === "champion");
  const seedNode = nodes.find((n) => n.data.strategy.parentId === null);
  const proj = (n: HierarchyPointNode<TreeDatum>) => ({
    left: view.x + n.y * view.k,
    top: view.y + n.x * view.k,
  });

  const aliveCount = strategies.filter((s) => s.status !== "tombstoned").length;
  const deadCount = strategies.filter((s) => s.status === "tombstoned").length;

  const wrapperClass = framed ? "border border-stroke-1 bg-bg-1 p-4" : "";

  return (
    <figure className={`flex flex-col gap-3 ${wrapperClass}`}>
      {caption && (
        <figcaption className="flex items-baseline justify-between gap-4 font-sans text-sm text-fg-1">
          <span>{caption}</span>
          <span className="shrink-0 font-mono text-xs text-fg-2">
            <span className="text-survivor">{aliveCount}</span> alive ·{" "}
            <span className="text-fg-1">{deadCount}</span> apoptosed
          </span>
        </figcaption>
      )}
      <div className="lineage-canvas tree-scroll relative overflow-hidden rounded-[2px]" style={{ height }}>
        <svg
          ref={svgRef}
          role="img"
          aria-label={caption ?? "Lineage tree"}
          width="100%"
          height={height}
          className="block"
        >
          <g ref={gRef} className="tree-enter">
            {/* Generation-depth axis — faint columns behind the lineage. */}
            {bbox &&
              genColumns.map((c) => (
                <g key={`gen-${c.generation}`} className="pointer-events-none">
                  <line
                    x1={c.y}
                    x2={c.y}
                    y1={bbox.xMin - 22}
                    y2={bbox.xMax + 20}
                    stroke="var(--color-stroke-1)"
                    strokeWidth={1}
                    strokeDasharray="2 6"
                    opacity={0.35}
                  />
                  <text
                    x={c.y}
                    y={bbox.xMin - 30}
                    textAnchor="middle"
                    fontFamily="var(--font-mono)"
                    fontSize={9}
                    fill="var(--color-fg-2)"
                  >
                    g{c.generation}
                  </text>
                </g>
              ))}
            {/* Edges — spine (seed→champion) glows; the rest recede. */}
            {links.map((link) => {
              const target = link.target.data.strategy;
              const isSpine =
                spineIds.has(target.id) && spineIds.has(link.source.data.strategy.id);
              return (
                <path
                  key={`${link.source.data.strategy.id}-${target.id}`}
                  d={linkPath(link) ?? ""}
                  className="lineage-edge"
                  data-status={target.status}
                  data-spine={isSpine ? "true" : undefined}
                />
              );
            })}
            {/* Nodes */}
            {nodes.map((node) => {
              const s = node.data.strategy;
              const isHover = hoverId === s.id;
              const isSelected = selectedId === s.id;
              const isChampion = s.status === "champion";
              const isTomb = s.status === "tombstoned";
              const unscored = s.status === "alive" && s.fitness === 0;
              const color = nodeColor(s);
              const r = nodeRadius(s);
              // Living lineage is always labelled (except the champion + seed,
              // which get prominent overlay pills); the dead are a quiet field
              // of struck grey dots whose labels surface on hover/focus.
              const hasPill = s.status === "champion" || s.parentId === null;
              const showLabel = (!isTomb && !hasPill) || isHover || isSelected;
              return (
                <g
                  key={s.id}
                  transform={`translate(${node.y}, ${node.x})`}
                  className="lineage-node cursor-pointer"
                  data-status={s.status}
                  tabIndex={0}
                  role="button"
                  aria-label={`${s.label}, generation ${s.generation}, ${unscored ? "awaiting judge" : `fitness ${s.fitness.toFixed(2)}`}, ${s.status}`}
                  aria-pressed={isSelected}
                  onMouseEnter={() => setHoverId(s.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onFocus={() => setHoverId(s.id)}
                  onBlur={() => setHoverId(null)}
                  onClick={() => onSelect?.(s)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect?.(s);
                    }
                  }}
                >
                  {/* Champion pulsing halo */}
                  {isChampion && (
                    <circle
                      className="champion-pulse"
                      r={17}
                      fill="none"
                      stroke={color}
                      strokeWidth={1.25}
                    />
                  )}
                  {/* Selection ring */}
                  {isSelected && (
                    <circle r={r + 7} fill="none" stroke="var(--color-survivor)" strokeWidth={1} opacity={0.85} />
                  )}
                  {/* Outer ring for living nodes — a crisp stained-cell look */}
                  {!isTomb && (
                    <circle r={r + 2.5} fill="none" stroke={color} strokeWidth={1} opacity={0.45} />
                  )}
                  {/* Body */}
                  <circle r={isHover ? r + 1 : r} fill={color} stroke={color} strokeWidth={1} />
                  {/* Apoptosis mark — a faint strike through the dead dot */}
                  {isTomb && (
                    <line
                      x1={-r - 1.5}
                      y1={0}
                      x2={r + 1.5}
                      y2={0}
                      stroke="var(--color-fg-tomb)"
                      strokeWidth={1}
                      opacity={0.7}
                    />
                  )}
                  {/* Inline label — survivors + revealed dead. aria-hidden: the
                      name comes from the node's aria-label, not this visual. */}
                  {showLabel && (
                    <g aria-hidden="true">
                      {isTomb && (
                        <rect
                          x={r + 4}
                          y={-7}
                          width={shortLabel(s.label).length * 6.2 + 10}
                          height={26}
                          fill="var(--color-bg-0)"
                          opacity={0.82}
                        />
                      )}
                      <text
                        x={r + 6}
                        y={4}
                        fontFamily="var(--font-mono)"
                        fontSize={11}
                        fill={isTomb ? "var(--color-fg-tomb)" : "var(--color-fg-0)"}
                        style={isTomb ? { textDecoration: "line-through" } : undefined}
                      >
                        {shortLabel(s.label)}
                      </text>
                      <text x={r + 6} y={16.5} fontFamily="var(--font-mono)" fontSize={9.5} fill="var(--color-fg-2)">
                        {unscored ? `awaiting judge · g${s.generation}` : `f=${s.fitness.toFixed(2)} · g${s.generation}`}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </svg>

        {/* Narrative overlay pills — crisp, constant-size, track the nodes. */}
        {view.ready && seedNode && (
          <div
            className="lineage-anno"
            style={{ left: proj(seedNode).left + 16, top: proj(seedNode).top }}
          >
            <div className="border border-stroke-2 bg-bg-0/85 px-2 py-1 backdrop-blur-[2px]">
              <div className="font-mono text-[9px] uppercase tracking-widest text-fg-2">seed · gen 0</div>
              <div className="font-mono text-xs text-fg-1">
                f={seedNode.data.strategy.fitness.toFixed(2)} · naive
              </div>
            </div>
          </div>
        )}
        {view.ready && championNode && (
          <div
            className="lineage-anno"
            style={{ left: proj(championNode).left + 16, top: proj(championNode).top }}
          >
            <div className="border border-champion/60 bg-bg-0/85 px-2.5 py-1 shadow-[0_0_24px_-8px_var(--color-champion)] backdrop-blur-[2px]">
              <div className="font-mono text-[9px] uppercase tracking-widest text-champion">champion</div>
              <div className="font-mono text-xs text-fg-0">
                f={championNode.data.strategy.fitness.toFixed(2)} · gen {championNode.data.strategy.generation}
              </div>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-2 left-2 flex flex-wrap gap-x-3 gap-y-1 border border-stroke-1 bg-bg-0/80 px-2 py-1 font-mono text-[10px] text-fg-1 backdrop-blur-[2px]">
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-survivor" /> alive</span>
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-champion" /> champion</span>
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-mutant" /> experimental</span>
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-fg-tomb" /> apoptosed</span>
        </div>
        {/* Reading guide — what the viewer is looking at, in one line. */}
        <p className="pointer-events-none absolute bottom-2 right-2 max-w-[15rem] text-right font-sans text-[11px] leading-snug text-fg-2">
          Each node is an appeal strategy. Winners branch; losers are deleted. The
          glowing thread is the lineage that became champion.
        </p>
      </div>
    </figure>
  );
}

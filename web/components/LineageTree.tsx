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
// This is the only place the magenta stain is keyed to data state.
function nodeColor(s: BCellStrategy): string {
  if (s.status === "champion") return "var(--color-champion)";
  if (s.status === "tombstoned") return "var(--color-fg-tomb)";
  if (s.tag === "experimental") return "var(--color-mutant)";
  return "var(--color-survivor)";
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

  const layout = useMemo(() => {
    const rootDatum = buildHierarchy(strategies);
    if (!rootDatum) return null;
    const root = hierarchy<TreeDatum>(rootDatum);
    // [vertical sibling gap, horizontal gap]. d3's depth layout is used only
    // for vertical sibling separation; horizontal is overridden below.
    const layoutFn = tree<TreeDatum>().nodeSize([44, GEN_SPACING]);
    const laid = layoutFn(root);
    // Position horizontally by GENERATION (time), not lineage depth: the x-axis
    // then reads as generations, and a strategy that survives several
    // generations before mutating shows as a longer edge rather than collapsing
    // adjacent. (Child generation is always > parent's, so edges stay rightward.)
    for (const d of laid.descendants()) {
      d.y = d.data.strategy.generation * GEN_SPACING;
    }
    return laid;
  }, [strategies]);

  // One column per generation present, at its time-position. Drives the faint
  // depth axis so the left→right progression reads explicitly as generations.
  const genColumns = useMemo(() => {
    if (!layout) return [];
    const byGen = new Map<number, number>();
    for (const n of layout.descendants()) {
      byGen.set(n.data.strategy.generation, n.y);
    }
    return Array.from(byGen.entries())
      .map(([generation, y]) => ({ generation, y }))
      .sort((a, b) => a.y - b.y);
  }, [layout]);

  // Bounding box of laid-out nodes — used to fit the tree to the viewport.
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

  // d3-zoom: pan + zoom on the SVG. Initial transform fits the tree.
  useEffect(() => {
    const svgEl = svgRef.current;
    const gEl = gRef.current;
    if (!svgEl || !gEl || !bbox) return;
    const width = svgEl.clientWidth || 800;
    const padding = 56;
    // Survivor labels render to the right of their node; reserve room so the
    // rightmost (latest-generation) labels are not clipped by the viewport.
    const labelPad = 185;
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
        g.attr("transform", event.transform.toString());
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

  const wrapperClass = framed
    ? "border border-stroke-1 bg-bg-1 p-4"
    : "";

  return (
    <figure className={`flex flex-col gap-3 ${wrapperClass}`}>
      {caption && (
        <figcaption className="flex items-baseline justify-between font-sans text-sm text-fg-1">
          <span>{caption}</span>
          <span className="font-mono text-xs text-fg-2">
            {strategies.filter((s) => s.status !== "tombstoned").length} alive ·{" "}
            {strategies.filter((s) => s.status === "tombstoned").length} apoptosed
          </span>
        </figcaption>
      )}
      <div className="tree-scroll relative overflow-hidden" style={{ height }}>
        <svg
          ref={svgRef}
          role="img"
          aria-label={caption ?? "Lineage tree"}
          width="100%"
          height={height}
          className="block"
        >
          <g ref={gRef}>
            {/* Generation-depth axis — faint columns behind the lineage so the
                left→right progression reads explicitly as generations. */}
            {bbox &&
              genColumns.map((c) => (
                <g key={`gen-${c.generation}`} className="pointer-events-none">
                  <line
                    x1={c.y}
                    x2={c.y}
                    y1={bbox.xMin - 20}
                    y2={bbox.xMax + 18}
                    stroke="var(--color-stroke-1)"
                    strokeWidth={1}
                    strokeDasharray="2 5"
                    opacity={0.4}
                  />
                  <text
                    x={c.y}
                    y={bbox.xMin - 28}
                    textAnchor="middle"
                    fontFamily="var(--font-mono)"
                    fontSize={9}
                    fill="var(--color-fg-2)"
                  >
                    g{c.generation}
                  </text>
                </g>
              ))}
            {/* Edges */}
            {links.map((link) => {
              const childStatus = link.target.data.strategy.status;
              const d = linkPath(link) ?? "";
              return (
                <path
                  key={`${link.source.data.strategy.id}-${link.target.data.strategy.id}`}
                  d={d}
                  className="lineage-edge"
                  data-status={childStatus}
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
              // A freshly-spawned mutant carries fitness 0 until the judge scores
              // it next cycle. Render that honestly as "awaiting judge" rather
              // than "f=0.00", which would read as a failed strategy.
              const unscored = s.status === "alive" && s.fitness === 0;
              const color = nodeColor(s);
              // Living lineage (champion + alive) is always labelled; the dead
              // are a quiet field of struck grey dots — their labels surface on
              // hover/focus/selection. Declutters 23 labels down to the survivors.
              const showLabel = !isTomb || isHover || isSelected;
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
                  {/* Selection ring */}
                  {isSelected && (
                    <circle
                      r={14}
                      fill="none"
                      stroke="var(--color-survivor)"
                      strokeWidth={1}
                      opacity={0.8}
                    />
                  )}
                  {/* Champion halo */}
                  {isChampion && (
                    <circle
                      r={12}
                      fill="none"
                      stroke={color}
                      strokeWidth={1}
                      opacity={0.5}
                    />
                  )}
                  {/* Body */}
                  <circle
                    r={isHover ? 6.5 : 5.5}
                    fill={color}
                    stroke={color}
                    strokeWidth={1}
                  />
                  {/* Label — survivors always; the dead reveal on hover/focus.
                      aria-hidden: the node's name comes from its aria-label (the
                      full, untruncated label); the visual text is decorative and
                      truncated, so it must not compete as the accessible name. */}
                  {showLabel && (
                    <g aria-hidden="true">
                      {/* Halo behind a revealed dead label so it reads above
                          neighbouring dots without reordering the DOM. */}
                      {isTomb && (
                        <rect
                          x={9}
                          y={-7}
                          width={shortLabel(s.label).length * 6.2 + 10}
                          height={26}
                          fill="var(--color-bg-0)"
                          opacity={0.82}
                        />
                      )}
                      <text
                        x={11}
                        y={4}
                        fontFamily="var(--font-mono)"
                        fontSize={11}
                        fill={isTomb ? "var(--color-fg-tomb)" : "var(--color-fg-0)"}
                        style={isTomb ? { textDecoration: "line-through" } : undefined}
                      >
                        {shortLabel(s.label)}
                      </text>
                      <text
                        x={11}
                        y={16.5}
                        fontFamily="var(--font-mono)"
                        fontSize={9.5}
                        fill={isChampion ? "var(--color-champion)" : "var(--color-fg-2)"}
                      >
                        {unscored
                          ? `awaiting judge · g${s.generation}`
                          : `f=${s.fitness.toFixed(2)} · g${s.generation}`}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
        {/* Legend */}
        <div className="absolute bottom-2 left-2 flex gap-3 border border-stroke-1 bg-bg-0/80 px-2 py-1 font-mono text-[10px] text-fg-1 backdrop-blur-[2px]">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-survivor" /> alive
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-champion" /> champion
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-mutant" /> experimental
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-fg-tomb" /> apoptosed
          </span>
        </div>
      </div>
    </figure>
  );
}

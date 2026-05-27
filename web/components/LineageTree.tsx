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

const STATUS_FILL: Record<BCellStrategy["status"], string> = {
  alive: "var(--color-survivor)",
  tombstoned: "var(--color-fg-tomb)",
  champion: "var(--color-champion)",
};

const STATUS_STROKE: Record<BCellStrategy["status"], string> = {
  alive: "var(--color-survivor)",
  tombstoned: "var(--color-fg-tomb)",
  champion: "var(--color-champion)",
};

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
    const layoutFn = tree<TreeDatum>().nodeSize([40, 130]);
    return layoutFn(root);
  }, [strategies]);

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
    const padding = 120;
    const treeW = bbox.yMax - bbox.yMin + padding * 2;
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
              return (
                <g
                  key={s.id}
                  transform={`translate(${node.y}, ${node.x})`}
                  className="lineage-node cursor-pointer"
                  data-status={s.status}
                  tabIndex={0}
                  role="button"
                  aria-label={`${s.label}, generation ${s.generation}, fitness ${s.fitness.toFixed(2)}, ${s.status}`}
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
                      stroke={STATUS_STROKE[s.status]}
                      strokeWidth={1}
                      opacity={0.5}
                    />
                  )}
                  {/* Body */}
                  <circle
                    r={isHover ? 6.5 : 5.5}
                    fill={STATUS_FILL[s.status]}
                    stroke={STATUS_STROKE[s.status]}
                    strokeWidth={1}
                  />
                  {/* Label */}
                  <text
                    x={10}
                    y={4}
                    fontFamily="var(--font-mono)"
                    fontSize={10}
                    fill={isTomb ? "var(--color-fg-tomb)" : "var(--color-fg-1)"}
                    style={isTomb ? { textDecoration: "line-through" } : undefined}
                  >
                    {s.label}
                  </text>
                  <text
                    x={10}
                    y={16}
                    fontFamily="var(--font-mono)"
                    fontSize={9}
                    fill="var(--color-fg-2)"
                  >
                    f={s.fitness.toFixed(2)} · g{s.generation}
                  </text>
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

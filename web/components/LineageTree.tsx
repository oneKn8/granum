"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { select } from "d3-selection";
import { zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { motion, useReducedMotion } from "motion/react";
import type { BCellStrategy } from "@/lib/types";

interface LineageTreeProps {
  strategies: BCellStrategy[];
  selectedId?: string | null;
  onSelect?: (strategy: BCellStrategy) => void;
  /** Title above the tree, e.g. "Appeal-writer population". */
  caption?: string;
  /** Pixel height of the SVG. */
  height?: number;
  /** Wrap in a panel surface. */
  framed?: boolean;
  /** Accent for this population (writers vs payers). Defaults to lineage palette. */
  variant?: "writer" | "payer";
}

/** Horizontal pixels per generation (X = time). */
const GEN_SPACING = 96;
const PAD_X = 56;
const PAD_Y = 44;
const MIN_GAP = 30; // minimum vertical pitch between co-generational nodes

interface PositionedNode {
  s: BCellStrategy;
  x: number;
  y: number;
  /** descendants in this node's subtree (for Murray's-law edge taper) */
  subtree: number;
}

interface PositionedLink {
  id: string;
  source: PositionedNode;
  target: PositionedNode;
  spine: boolean;
}

/** Round bump path (curveBumpX): horizontal tangents, smooth S — organic, not elbow. */
function bumpPath(sx: number, sy: number, tx: number, ty: number): string {
  const mx = (sx + tx) / 2;
  return `M${sx},${sy}C${mx},${sy} ${mx},${ty} ${tx},${ty}`;
}

function nodeRadius(s: BCellStrategy): number {
  if (s.status === "champion") return 10;
  const base = 4.4 + (s.fitness ?? 0) * 4.2;
  if (s.status === "tombstoned") return Math.max(3.6, base - 1.2);
  return base;
}

export function LineageTree({
  strategies,
  selectedId,
  onSelect,
  caption,
  height = 480,
  framed = true,
  variant = "writer",
}: LineageTreeProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const reduce = useReducedMotion();
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [offscreen, setOffscreen] = useState(false);
  const [view, setView] = useState({ x: 0, y: 0, k: 1, ready: false });
  // LIVE growth: one-shot flourishes (cell division, apoptosis lysis, promotion
  // bloom) fired when router.refresh() brings a new generation. `pulse` holds the
  // ids mid-flourish and self-clears, so the rings survive the camera re-fit's
  // re-renders instead of unmounting a frame later.
  const [pulse, setPulse] = useState<{
    arrived: Set<string>;
    died: Set<string>;
    promoted: Set<string>;
  }>({ arrived: new Set(), died: new Set(), promoted: new Set() });
  const prevRef = useRef<Map<string, { tomb: boolean; champ: boolean }>>(new Map());
  const mountedRef = useRef(false);

  // Pause the champion's looping breath when the tree scrolls out of view.
  useEffect(() => {
    const el = canvasRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => setOffscreen(!e.isIntersecting), {
      threshold: 0,
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  // ---- Layout: X = generation (time), Y = fitness (the climb) ----
  const model = useMemo(() => {
    if (strategies.length === 0) return null;
    const byId = new Map(strategies.map((s) => [s.id, s]));
    const childrenOf = new Map<string, BCellStrategy[]>();
    for (const s of strategies) {
      if (s.parentId && byId.has(s.parentId)) {
        const arr = childrenOf.get(s.parentId) ?? [];
        arr.push(s);
        childrenOf.set(s.parentId, arr);
      }
    }
    // subtree sizes (post-order) for edge taper
    const subtree = new Map<string, number>();
    const countSub = (id: string): number => {
      if (subtree.has(id)) return subtree.get(id)!;
      const kids = childrenOf.get(id) ?? [];
      const n = kids.reduce((acc, k) => acc + countSub(k.id), 1);
      subtree.set(id, n);
      return n;
    };
    for (const s of strategies) countSub(s.id);

    const maxGen = Math.max(...strategies.map((s) => s.generation));
    // Un-judged live-frontier daughters carry fitness 0; they must neither
    // stretch the Y scale nor plunge to the floor — they hang just below
    // their nearest scored ancestor until the judge runs.
    const isUnscored = (s: BCellStrategy) => s.status === "alive" && s.fitness === 0;
    const scored = strategies.filter((s) => !isUnscored(s));
    const minFit = Math.min(...(scored.length ? scored : strategies).map((s) => s.fitness));
    const fitFloor = Math.min(0.34, minFit - 0.03);
    const innerTop = PAD_Y;
    const innerBottom = height - PAD_Y;
    const yOf = (fit: number) => {
      const t = (fit - fitFloor) / (1 - fitFloor || 1);
      return innerBottom - t * (innerBottom - innerTop); // higher fitness → higher up
    };
    const anchorFit = (s: BCellStrategy): number => {
      let cur: BCellStrategy | undefined = s;
      let guard = 0;
      while (cur && isUnscored(cur) && guard++ < 100) {
        cur = cur.parentId ? byId.get(cur.parentId) : undefined;
      }
      return cur && !isUnscored(cur) ? cur.fitness : 0;
    };

    // position, then resolve vertical collisions per generation column
    const nodes: PositionedNode[] = strategies.map((s) => ({
      s,
      x: PAD_X + s.generation * GEN_SPACING,
      y: isUnscored(s) ? yOf(anchorFit(s)) + 18 : yOf(s.fitness),
      subtree: subtree.get(s.id) ?? 1,
    }));
    const byGen = new Map<number, PositionedNode[]>();
    for (const n of nodes) {
      const arr = byGen.get(n.s.generation) ?? [];
      arr.push(n);
      byGen.set(n.s.generation, arr);
    }
    for (const arr of byGen.values()) {
      arr.sort((a, b) => a.y - b.y);
      for (let i = 1; i < arr.length; i++) {
        if (arr[i].y - arr[i - 1].y < MIN_GAP) arr[i].y = arr[i - 1].y + MIN_GAP;
      }
    }
    const posById = new Map(nodes.map((n) => [n.s.id, n]));

    // survival spine: champion → … → seed
    const spineIds = new Set<string>();
    let cur = strategies.find((s) => s.status === "champion") ?? null;
    let guard = 0;
    while (cur && guard++ < 1000) {
      spineIds.add(cur.id);
      cur = cur.parentId ? byId.get(cur.parentId) ?? null : null;
    }

    const links: PositionedLink[] = [];
    for (const s of strategies) {
      if (!s.parentId) continue;
      const source = posById.get(s.parentId);
      const target = posById.get(s.id);
      if (!source || !target) continue;
      links.push({
        id: `${s.parentId}->${s.id}`,
        source,
        target,
        spine: spineIds.has(s.id) && spineIds.has(s.parentId),
      });
    }

    let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
    for (const n of nodes) {
      const r = nodeRadius(n.s);
      xMin = Math.min(xMin, n.x - r);
      xMax = Math.max(xMax, n.x + r);
      yMin = Math.min(yMin, n.y - r);
      yMax = Math.max(yMax, n.y + r);
    }

    const genCols = Array.from(byGen.keys())
      .sort((a, b) => a - b)
      .map((g) => ({ g, x: PAD_X + g * GEN_SPACING }));

    // Fitness reference lines — frames the climb as a deliberate plot.
    const yTicks = [0.4, 0.6, 0.8, 1.0]
      .filter((f) => f >= fitFloor)
      .map((f) => ({ f, y: yOf(f) }));

    return { nodes, links, spineIds, bbox: { xMin, xMax, yMin, yMax }, maxGen, genCols, yTicks };
  }, [strategies, height]);

  // ---- d3-zoom: fit on mount + smoothly re-fit as the tree grows ----
  const fitKey = model ? `${model.maxGen}:${model.nodes.length}` : "none";
  useEffect(() => {
    const svgEl = svgRef.current;
    const gEl = gRef.current;
    if (!svgEl || !gEl || !model) return;
    const width = svgEl.clientWidth || 800;
    const { bbox } = model;
    const labelPad = 188;
    const treeW = bbox.xMax - bbox.xMin + PAD_X * 2 + labelPad;
    const treeH = bbox.yMax - bbox.yMin + PAD_Y * 2;
    const scale = Math.min(width / treeW, height / treeH, 1.2);
    const tx = (width - (bbox.xMin + bbox.xMax) * scale) / 2 - 42 * scale;
    const ty = (height - (bbox.yMin + bbox.yMax) * scale) / 2;

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
    const target = zoomIdentity.translate(tx, ty).scale(scale);

    // animate camera so a freshly-grown champion eases into frame (no d3-transition dep)
    const start = performance.now();
    const from = view.ready ? zoomIdentity.translate(view.x, view.y).scale(view.k) : target;
    const dur = view.ready && !reduce ? 620 : 0;
    let raf = 0;
    const tick = (now: number) => {
      const p = dur === 0 ? 1 : Math.min(1, (now - start) / dur);
      const e = 1 - Math.pow(1 - p, 3); // ease-out cubic
      const cx = from.x + (target.x - from.x) * e;
      const cy = from.y + (target.y - from.y) * e;
      const ck = from.k + (target.k - from.k) * e;
      svg.call(zoomBehavior.transform, zoomIdentity.translate(cx, cy).scale(ck));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      svg.on(".zoom", null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey, height]);

  // Diff this poll's population against the last to drive the LIVE flourishes.
  useEffect(() => {
    const cur = new Map<string, { tomb: boolean; champ: boolean }>(
      strategies.map((s) => [
        s.id,
        { tomb: s.status === "tombstoned", champ: s.status === "champion" },
      ]),
    );
    if (!mountedRef.current || reduce) {
      prevRef.current = cur;
      mountedRef.current = true;
      return;
    }
    const prev = prevRef.current;
    const arrived = new Set<string>();
    const died = new Set<string>();
    const promoted = new Set<string>();
    for (const [id, st] of cur) {
      const p = prev.get(id);
      if (!p) arrived.add(id);
      else {
        if (!p.tomb && st.tomb) died.add(id);
        if (!p.champ && st.champ) promoted.add(id);
      }
    }
    prevRef.current = cur;
    if (arrived.size || died.size || promoted.size) {
      setPulse({ arrived, died, promoted });
      const t = setTimeout(
        () => setPulse({ arrived: new Set(), died: new Set(), promoted: new Set() }),
        1400,
      );
      return () => clearTimeout(t);
    }
  }, [strategies, reduce]);

  if (!model) return null;
  const { nodes, links, spineIds, genCols, bbox, yTicks } = model;

  const proj = (n: PositionedNode) => ({ left: view.x + n.x * view.k, top: view.y + n.y * view.k });
  const seedNode = nodes.find((n) => n.s.parentId === null);
  const championNode = nodes.find((n) => n.s.status === "champion");
  const aliveCount = strategies.filter((s) => s.status !== "tombstoned").length;
  const deadCount = strategies.filter((s) => s.status === "tombstoned").length;

  // Stagger order for live-arriving nodes, so a fresh generation buds in promptly
  // instead of waiting on its absolute generation index (the first-paint cascade).
  const liveOrder = new Map<string, number>();
  if (mountedRef.current && !reduce) {
    nodes
      .filter((n) => !prevRef.current.has(n.s.id))
      .sort((a, b) => a.s.generation - b.s.generation || a.y - b.y)
      .forEach((n, i) => liveOrder.set(n.s.id, i));
  }

  const accentGrad =
    variant === "payer" ? "url(#cell-payer)" : "url(#cell-alive)";

  const edgeWidth = (l: PositionedLink) =>
    Math.min(6, 1.1 + Math.sqrt(l.target.subtree) * (l.spine ? 1.5 : 0.85));

  const wrapperClass = framed ? "border border-border bg-surface/70 p-4" : "";

  return (
    <figure className={`flex flex-col gap-3 ${wrapperClass}`}>
      {caption && (
        <figcaption className="flex items-baseline justify-between gap-4 font-body text-sm text-ink-muted">
          <span className="font-medium text-ink">{caption}</span>
          <span className="shrink-0 font-mono text-xs text-ink-subtle">
            <span className="text-alive">{aliveCount}</span> alive ·{" "}
            <span className="text-dead-ink">{deadCount}</span> apoptosed
          </span>
        </figcaption>
      )}

      <div
        ref={canvasRef}
        className={`lineage-canvas tree-scroll relative overflow-hidden rounded-[3px] border border-border${offscreen ? " motion-paused" : ""}`}
        style={{ height }}
      >
        <svg
          ref={svgRef}
          role="img"
          aria-label={caption ?? "Lineage tree"}
          width="100%"
          height={height}
          className="block"
        >
          <defs>
            <radialGradient id="cell-alive" cx="38%" cy="34%" r="72%">
              <stop offset="0%" stopColor="oklch(0.68 0.135 152)" />
              <stop offset="100%" stopColor="oklch(0.545 0.135 152)" />
            </radialGradient>
            <radialGradient id="cell-champion" cx="38%" cy="34%" r="72%">
              <stop offset="0%" stopColor="oklch(0.82 0.15 84)" />
              <stop offset="100%" stopColor="oklch(0.705 0.15 82)" />
            </radialGradient>
            <radialGradient id="cell-mutant" cx="38%" cy="34%" r="72%">
              <stop offset="0%" stopColor="oklch(0.68 0.13 330)" />
              <stop offset="100%" stopColor="oklch(0.55 0.13 330)" />
            </radialGradient>
            <radialGradient id="cell-payer" cx="38%" cy="34%" r="72%">
              <stop offset="0%" stopColor="oklch(0.66 0.12 28)" />
              <stop offset="100%" stopColor="oklch(0.55 0.12 28)" />
            </radialGradient>
          </defs>

          <g ref={gRef}>
            {/* Fitness axis — horizontal reference lines so the climb reads as a plot */}
            {yTicks.map((t) => (
              <g key={`fit-${t.f}`} className="pointer-events-none">
                <line
                  x1={bbox.xMin - 10}
                  x2={bbox.xMax + 20}
                  y1={t.y}
                  y2={t.y}
                  stroke="var(--color-border)"
                  strokeWidth={1}
                  strokeDasharray="1 8"
                  opacity={0.7}
                />
                <text
                  x={bbox.xMin - 14}
                  y={t.y + 3}
                  textAnchor="end"
                  fontFamily="var(--font-mono)"
                  fontSize={9}
                  fill="var(--color-ink-subtle)"
                >
                  {t.f.toFixed(1)}
                </text>
              </g>
            ))}
            {/* Generation axis — faint warm gridlines + a time arrow */}
            {genCols.map((c, i) => (
              <g key={`gen-${c.g}`} className="pointer-events-none">
                <line
                  x1={c.x}
                  x2={c.x}
                  y1={bbox.yMin - 26}
                  y2={bbox.yMax + 18}
                  stroke="var(--color-border)"
                  strokeWidth={1}
                  strokeDasharray="2 7"
                  opacity={0.7}
                />
                <text
                  x={c.x}
                  y={bbox.yMin - 32}
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                  fontSize={9.5}
                  fill="var(--color-ink-subtle)"
                >
                  {i === 0 ? "gen 0" : `g${c.g}`}
                </text>
              </g>
            ))}

            {/* Edges — dead + non-spine fade in; spine draws seed→champion */}
            {links.map((l) => {
              const d = bumpPath(l.source.x, l.source.y, l.target.x, l.target.y);
              const isDead = l.target.s.status === "tombstoned";
              const delay = reduce ? 0 : 0.12 * l.target.s.generation + (l.spine ? 0 : 0.25);
              if (l.spine) {
                return (
                  <motion.path
                    key={l.id}
                    d={d}
                    className="lineage-edge"
                    data-spine="true"
                    strokeWidth={edgeWidth(l)}
                    initial={reduce ? false : { pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
                  />
                );
              }
              return (
                <motion.path
                  key={l.id}
                  d={d}
                  className="lineage-edge"
                  data-status={isDead ? "tombstoned" : undefined}
                  strokeWidth={edgeWidth(l)}
                  initial={reduce ? false : { opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay, ease: "easeOut" }}
                />
              );
            })}

            {/* Nodes — stained cells; bud in scaled, staggered by generation */}
            {nodes.map((n) => {
              const s = n.s;
              const isHover = hoverId === s.id;
              const isSelected = selectedId === s.id;
              const isChampion = s.status === "champion";
              const isTomb = s.status === "tombstoned";
              const onSpine = spineIds.has(s.id);
              const unscored = s.status === "alive" && s.fitness === 0;
              const r = nodeRadius(s);
              const isLiveArrival =
                mountedRef.current && !reduce && !prevRef.current.has(s.id);
              const justArrived = pulse.arrived.has(s.id);
              const justDied = pulse.died.has(s.id);
              const justPromoted = pulse.promoted.has(s.id);
              const fill =
                isChampion ? "url(#cell-champion)"
                : s.tag === "experimental" && !isTomb ? "url(#cell-mutant)"
                : accentGrad;
              const ringColor =
                isChampion ? "var(--color-champion)"
                : s.tag === "experimental" && !isTomb ? "var(--color-mutant)"
                : variant === "payer" ? "oklch(0.55 0.12 28)" : "var(--color-alive)";
              const delay = reduce
                ? 0
                : isLiveArrival
                  ? 0.05 * (liveOrder.get(s.id) ?? 0)
                  : 0.12 * s.generation + 0.2;

              return (
                <motion.g
                  key={s.id}
                  transform={`translate(${n.x},${n.y})`}
                  className="lineage-node cursor-pointer"
                  data-status={s.status}
                  style={{ opacity: isTomb ? 0.82 : 1 }}
                  initial={reduce ? false : { opacity: 0, scale: 0.3 }}
                  animate={{ opacity: isTomb ? 0.82 : 1, scale: 1 }}
                  transition={{ duration: 0.5, delay, ease: [0.34, 1.3, 0.5, 1] }}
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
                  {/* LIVE: a new cell divides into existence */}
                  {justArrived && !isTomb && (
                    <motion.circle
                      r={r}
                      fill="none"
                      stroke={ringColor}
                      strokeWidth={1.4}
                      style={{ transformBox: "fill-box", transformOrigin: "center" }}
                      initial={{ scale: 0.5, opacity: 0.7 }}
                      animate={{ scale: 3.4, opacity: 0 }}
                      transition={{ duration: 0.9, ease: "easeOut" }}
                    />
                  )}
                  {/* LIVE: apoptosis — the membrane bursts as the strategy lyses */}
                  {justDied && (
                    <motion.circle
                      r={r}
                      fill="var(--color-dead)"
                      style={{ transformBox: "fill-box", transformOrigin: "center" }}
                      initial={{ scale: 1, opacity: 0.32 }}
                      animate={{ scale: 2.5, opacity: 0 }}
                      transition={{ duration: 0.7, ease: "easeOut" }}
                    />
                  )}
                  {/* LIVE: champion promotion bloom */}
                  {justPromoted && (
                    <motion.circle
                      r={r}
                      fill="none"
                      stroke="var(--color-champion)"
                      strokeWidth={2}
                      style={{ transformBox: "fill-box", transformOrigin: "center" }}
                      initial={{ scale: 1, opacity: 0.8 }}
                      animate={{ scale: 3.1, opacity: 0 }}
                      transition={{ duration: 1.1, ease: "easeOut" }}
                    />
                  )}
                  {isChampion && (
                    <circle
                      className="champion-breath"
                      r={20}
                      fill="none"
                      stroke="var(--color-champion)"
                      strokeWidth={1.25}
                    />
                  )}
                  {isSelected && (
                    <circle r={r + 7} fill="none" stroke="var(--color-primary)" strokeWidth={1.25} opacity={0.9} />
                  )}

                  {isTomb ? (
                    <>
                      {/* apoptosed = hollow lysed cell + strike. On the spine, a
                          faded-gold ring marks it as the line that became champion. */}
                      <circle
                        r={r}
                        fill="var(--color-surface)"
                        stroke={onSpine ? "var(--color-champion)" : "var(--color-dead)"}
                        strokeWidth={onSpine ? 1.8 : 1.4}
                        opacity={onSpine ? 0.85 : 1}
                      />
                      {justDied ? (
                        <motion.line
                          x1={-r - 1.5}
                          y1={0}
                          x2={r + 1.5}
                          y2={0}
                          stroke="var(--color-dead)"
                          strokeWidth={1.1}
                          initial={{ pathLength: 0, opacity: 0 }}
                          animate={{ pathLength: 1, opacity: 0.8 }}
                          transition={{ duration: 0.42, delay: 0.16, ease: "easeOut" }}
                        />
                      ) : (
                        <line x1={-r - 1.5} y1={0} x2={r + 1.5} y2={0} stroke="var(--color-dead)" strokeWidth={1.1} opacity={0.8} />
                      )}
                    </>
                  ) : (
                    <>
                      <circle r={r + 2.6} fill="none" stroke={ringColor} strokeWidth={1.1} opacity={0.5} />
                      <circle r={isHover ? r + 1 : r} fill={fill} />
                      <circle r={r * 0.42} cx={-r * 0.28} cy={-r * 0.3} fill="oklch(0.99 0.01 95)" opacity={0.35} />
                    </>
                  )}

                  {/* In-tree hover/select label removed: Motion positions nodes via a
                      CSS transform the SVG geometry layer doesn't track, so this label
                      anchored to the untransformed origin (top-left). Selection feedback
                      is the ring + the detail panel; the seed/champion HTML pills handle
                      the always-on labels. */}
                </motion.g>
              );
            })}
          </g>
        </svg>

        {/* Crisp narrative pills tracking the seed + champion */}
        {view.ready && seedNode && (
          <div className="lineage-anno" style={{ left: proj(seedNode).left + 18, top: proj(seedNode).top }}>
            <div className="border border-border-strong bg-surface/90 px-2 py-1 shadow-sm backdrop-blur-[2px]">
              <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink-subtle">seed · gen 0</div>
              <div className="font-mono text-xs text-ink-muted">f={seedNode.s.fitness.toFixed(2)} · naive</div>
            </div>
          </div>
        )}
        {view.ready && championNode && (
          <div className="lineage-anno" style={{ left: proj(championNode).left + 18, top: proj(championNode).top }}>
            <div className="border border-champion/50 bg-surface/92 px-2.5 py-1 shadow-[0_2px_14px_-4px_var(--color-champion)] backdrop-blur-[2px]">
              <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-champion-ink">champion</div>
              <div className="font-mono text-xs text-ink">
                f={championNode.s.fitness.toFixed(2)} · gen {championNode.s.generation}
              </div>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-2 left-2 flex flex-wrap gap-x-3 gap-y-1 border border-border bg-surface/85 px-2 py-1 font-mono text-[10px] text-ink-muted backdrop-blur-[2px]">
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-alive" /> alive</span>
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-champion" /> champion</span>
          <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-mutant" /> experimental</span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full border border-dead bg-surface" /> apoptosed
          </span>
        </div>
        {/* Hidden below md: it shares the bottom edge with the legend and the
            two collide on narrow cards. */}
        <p className="pointer-events-none absolute bottom-2 right-2 hidden max-w-[15rem] text-right font-body text-[11px] leading-snug text-ink-subtle md:block">
          Height is fitness; left&nbsp;→&nbsp;right is time. Winners branch upward; losers are struck out and frozen.
        </p>
      </div>
    </figure>
  );
}

"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { useReducedMotion } from "motion/react";
import type { FitnessPoint } from "@/lib/types";

interface FitnessCurveProps {
  points: FitnessPoint[];
  baseline?: number;
  height?: number;
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload as FitnessPoint;
  return (
    <div className="border border-border bg-surface px-3 py-2 font-mono text-xs leading-tight text-ink shadow-sm">
      <div className="text-ink-muted">generation {point.generation}</div>
      <div>
        best <span className="text-champion-ink">{point.maxFitness.toFixed(2)}</span>
      </div>
      <div>
        mean <span className="text-ink-muted">{point.meanFitness.toFixed(2)}</span>
      </div>
      <div className="text-ink-subtle">
        {point.survivingCount} alive · {point.apoptosisCount} apoptosed
      </div>
    </div>
  );
}

export function FitnessCurve({ points, baseline, height = 200 }: FitnessCurveProps) {
  const reduce = useReducedMotion();
  const peak = points.length > 0 ? Math.max(...points.map((p) => p.maxFitness)) : null;
  return (
    <figure
      className="flex flex-col gap-2 border border-border bg-surface/70 p-4"
      aria-label="Appeal fitness over generations"
    >
      <figcaption className="flex items-baseline justify-between font-body text-sm text-ink-muted">
        <span className="font-medium text-ink">How fitness climbed, generation by generation</span>
        <span className="font-mono text-xs text-ink-subtle">
          seed {baseline?.toFixed(2) ?? "—"} <span className="text-ink-subtle">→</span>{" "}
          peak <span className="text-champion-ink">{peak !== null ? peak.toFixed(2) : "—"}</span>
        </span>
      </figcaption>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 10, right: 12, bottom: 6, left: -14 }}>
            <defs>
              <linearGradient id="meanFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-alive)" stopOpacity={0.26} />
                <stop offset="100%" stopColor="var(--color-alive)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--color-border)" vertical={false} />
            {baseline !== undefined && (
              <ReferenceLine
                y={baseline}
                stroke="var(--color-ink-subtle)"
                strokeDasharray="3 4"
                strokeOpacity={0.6}
              />
            )}
            <XAxis
              dataKey="generation"
              stroke="var(--color-ink-subtle)"
              tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--color-ink-subtle)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--color-border)" }}
              label={{
                value: "generation",
                position: "insideBottom",
                offset: -1,
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fill: "var(--color-ink-subtle)",
              }}
            />
            <YAxis
              domain={[0, 1]}
              stroke="var(--color-ink-subtle)"
              tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--color-ink-subtle)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--color-border)" }}
              tickFormatter={(v) => v.toFixed(1)}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ stroke: "var(--color-border-strong)", strokeDasharray: "2 3" }}
            />
            <Area
              type="monotone"
              dataKey="meanFitness"
              stroke="var(--color-alive)"
              strokeWidth={1.25}
              fill="url(#meanFill)"
              isAnimationActive={!reduce}
              animationDuration={900}
            />
            <Line
              type="monotone"
              dataKey="maxFitness"
              stroke="var(--color-champion)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--color-champion)", stroke: "none" }}
              activeDot={{ r: 4.5, fill: "var(--color-champion)", stroke: "var(--color-surface)", strokeWidth: 1.5 }}
              isAnimationActive={!reduce}
              animationDuration={1100}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

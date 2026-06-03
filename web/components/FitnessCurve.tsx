"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
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
    <div className="border border-stroke-1 bg-bg-1 px-3 py-2 font-mono text-xs leading-tight text-fg-0">
      <div className="text-fg-1">generation {point.generation}</div>
      <div>
        max <span className="text-survivor">{point.maxFitness.toFixed(2)}</span>
      </div>
      <div>
        mean <span className="text-fg-1">{point.meanFitness.toFixed(2)}</span>
      </div>
      <div className="text-fg-2">
        {point.survivingCount} alive · {point.apoptosisCount} apoptosed
      </div>
    </div>
  );
}

export function FitnessCurve({ points, baseline, height = 220 }: FitnessCurveProps) {
  // Peak of the plotted max-fitness line — honest (it is literally the highest
  // point on the curve) and consistent with the page's headline appeal-fitness.
  const peak = points.length > 0 ? Math.max(...points.map((p) => p.maxFitness)) : null;
  return (
    <figure
      className="flex flex-col gap-2 border border-stroke-1 bg-bg-1 p-4"
      aria-label="Appeal fitness over generations"
    >
      <figcaption className="flex items-baseline justify-between font-sans text-sm text-fg-1">
        <span>Appeal fitness over generations</span>
        <span className="font-mono text-xs text-fg-2">
          baseline {baseline?.toFixed(2) ?? "—"} → peak{" "}
          {peak !== null ? peak.toFixed(2) : "—"}
        </span>
      </figcaption>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={points}
            margin={{ top: 8, right: 8, bottom: 8, left: -16 }}
          >
            <defs>
              <linearGradient id="meanFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-survivor)" stopOpacity={0.32} />
                <stop offset="100%" stopColor="var(--color-survivor)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--color-stroke-1)" vertical={false} />
            <XAxis
              dataKey="generation"
              stroke="var(--color-fg-2)"
              tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--color-fg-2)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--color-stroke-1)" }}
              label={{
                value: "generation",
                position: "insideBottom",
                offset: -2,
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fill: "var(--color-fg-2)",
              }}
            />
            <YAxis
              domain={[0, 1]}
              stroke="var(--color-fg-2)"
              tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--color-fg-2)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--color-stroke-1)" }}
              tickFormatter={(v) => v.toFixed(1)}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ stroke: "var(--color-stroke-2)", strokeDasharray: "2 3" }}
            />
            <Area
              type="monotone"
              dataKey="meanFitness"
              stroke="var(--color-survivor)"
              strokeWidth={1}
              fill="url(#meanFill)"
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="maxFitness"
              stroke="var(--color-champion)"
              strokeWidth={1.5}
              dot={{ r: 2.5, fill: "var(--color-champion)", stroke: "none" }}
              activeDot={{ r: 4, fill: "var(--color-champion)", stroke: "none" }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

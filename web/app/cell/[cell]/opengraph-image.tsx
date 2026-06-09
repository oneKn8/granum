import { ImageResponse } from "next/og";
import { getCellPayload } from "@/lib/api";
import { ALL_CELLS, CELL_LABEL } from "@/lib/mock-data";
import type { CellId } from "@/lib/types";

export const runtime = "edge";
export const alt = "Granum cell lineage";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Share-card host shown in the footer; must match the canonical in layout.tsx.
const SITE_HOST = (() => {
  const url =
    process.env.NEXT_PUBLIC_SITE_URL ??
    (process.env.VERCEL_PROJECT_PRODUCTION_URL
      ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
      : "http://localhost:3000");
  return new URL(url).host;
})();

// Light "agar" palette (hex, for Satori safety).
const BG = "#f7f2e8";
const FG = "#26221a";
const FG_DIM = "#6d685b";
const ALIVE = "#2e7d52";
const CHAMPION = "#9c7322";
const DEAD = "#8f897a";
const STROKE = "#ddd8cb";

function isCellId(id: string): id is CellId {
  return id in ALL_CELLS;
}

export default async function CellOG({ params }: { params: { cell: string } }) {
  const cell = params.cell;
  if (!isCellId(cell)) {
    return new ImageResponse(
      (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            background: BG,
            padding: "80px",
            color: FG,
            fontFamily: "serif",
            fontSize: 72,
          }}
        >
          Granum · cell not found
        </div>
      ),
      size,
    );
  }
  // The card must show the same numbers as the page it previews: fetch the
  // real payload and only fall back to mock when the API is unreachable.
  let meta = ALL_CELLS[cell].meta;
  try {
    meta = (await getCellPayload(cell)).meta;
  } catch {
    /* mock fallback */
  }
  const baseline = (meta.baselineOverturn * 100).toFixed(0);
  const current = (meta.currentOverturn * 100).toFixed(0);

  const stat = (label: string, value: string, color: string) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <span style={{ fontSize: 14, color: FG_DIM, letterSpacing: 2 }}>{label}</span>
      <span style={{ color }}>{value}</span>
    </div>
  );

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: BG,
          padding: "80px",
          fontFamily: "serif",
          color: FG,
        }}
      >
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 18,
            color: FG_DIM,
            letterSpacing: 3,
            textTransform: "uppercase",
            marginBottom: 28,
            display: "flex",
          }}
        >
          Granum · {CELL_LABEL[cell]}
        </div>
        <div
          style={{
            fontSize: 64,
            lineHeight: 1.05,
            fontWeight: 500,
            letterSpacing: -1,
            display: "flex",
            maxWidth: 1000,
          }}
        >
          {meta.payer} · {meta.diagnosis}
        </div>
        <div
          style={{
            marginTop: 36,
            display: "flex",
            gap: 80,
            fontFamily: "monospace",
            fontSize: 26,
          }}
        >
          {stat("SEED", `${baseline}%`, DEAD)}
          {stat("CHAMPION", `${current}%`, CHAMPION)}
          {stat("GENERATIONS", String(meta.generations), ALIVE)}
          {stat("APOPTOSED", String(meta.apoptosisTotal), DEAD)}
        </div>
        <div
          style={{
            marginTop: "auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: `1px solid ${STROKE}`,
            paddingTop: 24,
            fontFamily: "monospace",
            fontSize: 16,
            color: FG_DIM,
          }}
        >
          <span>{SITE_HOST}/cell/{cell}</span>
          <span>Apache-2.0 · synthetic data only</span>
        </div>
      </div>
    ),
    size,
  );
}

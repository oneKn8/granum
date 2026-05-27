import { ImageResponse } from "next/og";
import { ALL_CELLS, CELL_LABEL } from "@/lib/mock-data";
import type { CellId } from "@/lib/types";

export const runtime = "edge";
export const alt = "Granum cell lineage";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BG = "oklch(0.16 0.020 285)";
const FG = "oklch(0.96 0.005 285)";
const FG_DIM = "oklch(0.74 0.020 285)";
const SURVIVOR = "oklch(0.74 0.16 230)";
const CHAMPION = "oklch(0.80 0.18 65)";
const TOMB = "oklch(0.42 0.010 285)";
const STROKE = "oklch(0.30 0.030 285)";

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
  const meta = ALL_CELLS[cell].meta;
  const baseline = (meta.baselineOverturn * 100).toFixed(0);
  const current = (meta.currentOverturn * 100).toFixed(0);

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
            maxWidth: 980,
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
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 14, color: FG_DIM, letterSpacing: 2 }}>BASELINE</span>
            <span style={{ color: TOMB }}>{baseline}%</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 14, color: FG_DIM, letterSpacing: 2 }}>CHAMPION</span>
            <span style={{ color: CHAMPION }}>{current}%</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 14, color: FG_DIM, letterSpacing: 2 }}>GENERATIONS</span>
            <span style={{ color: SURVIVOR }}>{meta.generations}</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 14, color: FG_DIM, letterSpacing: 2 }}>APOPTOSED</span>
            <span style={{ color: TOMB }}>{meta.apoptosisTotal}</span>
          </div>
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
          <span>granum.app/cell/{cell}</span>
          <span>Apache-2.0 · synthetic data only</span>
        </div>
      </div>
    ),
    size,
  );
}

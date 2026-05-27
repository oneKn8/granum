import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt =
  "Granum — an immune system for medical appeals. Lineage tree visualization.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const BG = "oklch(0.16 0.020 285)";
const FG = "oklch(0.96 0.005 285)";
const FG_DIM = "oklch(0.74 0.020 285)";
const SURVIVOR = "oklch(0.74 0.16 230)";
const CHAMPION = "oklch(0.80 0.18 65)";
const TOMB = "oklch(0.42 0.010 285)";
const STROKE = "oklch(0.30 0.030 285)";

export default function OG() {
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
          Granum · an immune system for medical appeals
        </div>
        <div
          style={{
            fontSize: 78,
            lineHeight: 1.05,
            fontWeight: 500,
            letterSpacing: -1,
            display: "flex",
            flexWrap: "wrap",
            maxWidth: 980,
          }}
        >
          Strategies that lose
          <br />
          are <span style={{ color: SURVIVOR }}>permanently</span> deleted.
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
          <div style={{ display: "flex", gap: 32 }}>
            <span>
              <span style={{ color: TOMB }}>41%</span> →{" "}
              <span style={{ color: CHAMPION }}>79%</span> overturn
            </span>
            <span>aetna · cardiac · 8 generations</span>
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            <span style={{ color: SURVIVOR }}>● alive</span>
            <span style={{ color: CHAMPION }}>● champion</span>
            <span style={{ color: TOMB }}>● apoptosed</span>
          </div>
        </div>
      </div>
    ),
    size,
  );
}

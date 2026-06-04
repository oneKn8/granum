import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt =
  "Granum, an immune system for medical appeals. A seed strategy matures into a champion across ten generations.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Light "agar" palette (hex, for Satori safety).
const BG = "#f7f2e8";
const FG = "#26221a";
const FG_DIM = "#6d685b";
const ALIVE = "#2e7d52";
const CHAMPION = "#9c7322";
const DEAD = "#8f897a";
const STROKE = "#ddd8cb";

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
            fontSize: 74,
            lineHeight: 1.06,
            fontWeight: 500,
            letterSpacing: -1.5,
            display: "flex",
            flexWrap: "wrap",
            maxWidth: 1000,
          }}
        >
          A denied appeal that gets{" "}
          <span style={{ color: ALIVE }}>&nbsp;better&nbsp;</span> every time it loses.
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
              <span style={{ color: DEAD }}>0.40</span> →{" "}
              <span style={{ color: CHAMPION }}>0.98</span> appeal fitness
            </span>
            <span>aetna · cardiac · 10 generations</span>
          </div>
          <div style={{ display: "flex", gap: 16 }}>
            <span style={{ color: ALIVE }}>● alive</span>
            <span style={{ color: CHAMPION }}>● champion</span>
            <span style={{ color: DEAD }}>○ apoptosed</span>
          </div>
        </div>
      </div>
    ),
    size,
  );
}

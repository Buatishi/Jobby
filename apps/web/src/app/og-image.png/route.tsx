import { ImageResponse } from "next/og";

import { scoreColorOnDarkGreen, statusTones } from "@/lib/utils/score-colors";

export const runtime = "edge";

const RING_RADIUS = 78;
const RING_LENGTH = 2 * Math.PI * RING_RADIUS;
const SAMPLE_SCORE = 78;

const sampleRows = [
  ["Python", "Cumple", "ok"],
  ["SQL", "Parcial", "mid"],
  ["Docker", "Falta", "bad"]
] as const;

// Imagen para compartir el link: panel oscuro con brillo verde y el anillo de match de ejemplo.
export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "#ffffff",
          display: "flex",
          height: "100%",
          justifyContent: "center",
          padding: 36,
          width: "100%"
        }}
      >
        <div
          style={{
            alignItems: "center",
            backgroundColor: "#1D1D1B",
            backgroundImage:
              "radial-gradient(circle at 50% 125%, rgba(43, 212, 138, 0.5), rgba(29, 29, 27, 0) 60%)",
            borderRadius: 44,
            display: "flex",
            gap: 56,
            height: "100%",
            padding: "0 64px",
            width: "100%"
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            <div
              style={{
                alignItems: "center",
                display: "flex",
                gap: 14,
                marginBottom: 30
              }}
            >
              <div
                style={{
                  alignItems: "center",
                  background: "#2BD48A",
                  borderRadius: 16,
                  color: "#1D1D1B",
                  display: "flex",
                  fontSize: 34,
                  fontWeight: 700,
                  height: 56,
                  justifyContent: "center",
                  width: 56
                }}
              >
                J
              </div>
              <div style={{ color: "#ffffff", display: "flex", fontSize: 42, fontWeight: 700 }}>
                Jobby
              </div>
            </div>
            <div
              style={{
                color: "#ffffff",
                display: "flex",
                fontSize: 62,
                fontWeight: 700,
                letterSpacing: "-0.03em",
                lineHeight: 1.04
              }}
            >
              Sabé cuánto matcheás antes de aplicar
            </div>
            <div
              style={{
                color: "#D4D4CF",
                display: "flex",
                fontSize: 25,
                lineHeight: 1.35,
                marginTop: 24
              }}
            >
              Match score, ATS y gaps reales para preparar mejores postulaciones.
            </div>
          </div>

          <div
            style={{
              alignItems: "center",
              background: "#272725",
              border: "1px solid #3A3A37",
              borderRadius: 28,
              display: "flex",
              flexDirection: "column",
              padding: 28,
              width: 330
            }}
          >
            <div style={{ display: "flex", height: 190, position: "relative", width: 190 }}>
              <svg height="190" viewBox="0 0 190 190" width="190">
                <circle
                  cx="95"
                  cy="95"
                  fill="none"
                  r={RING_RADIUS}
                  stroke="#3A3A37"
                  strokeWidth="16"
                />
                <circle
                  cx="95"
                  cy="95"
                  fill="none"
                  r={RING_RADIUS}
                  stroke={scoreColorOnDarkGreen}
                  strokeDasharray={`${(RING_LENGTH * SAMPLE_SCORE) / 100} ${RING_LENGTH}`}
                  strokeLinecap="round"
                  strokeWidth="16"
                  transform="rotate(-90 95 95)"
                />
              </svg>
              <div
                style={{
                  alignItems: "center",
                  color: "#ffffff",
                  display: "flex",
                  fontSize: 64,
                  fontWeight: 700,
                  height: 190,
                  justifyContent: "center",
                  left: 0,
                  position: "absolute",
                  top: 0,
                  width: 190
                }}
              >
                {SAMPLE_SCORE}
              </div>
            </div>
            {sampleRows.map(([label, status, tone]) => (
              <div
                key={label}
                style={{
                  alignItems: "center",
                  background: "#1F1F1D",
                  borderRadius: 14,
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: 12,
                  padding: "10px 16px",
                  width: "100%"
                }}
              >
                <div style={{ color: "#ffffff", display: "flex", fontSize: 20, fontWeight: 600 }}>
                  {label}
                </div>
                <div
                  style={{
                    background: statusTones.dark[tone].background,
                    borderRadius: 999,
                    color: statusTones.dark[tone].color,
                    display: "flex",
                    fontSize: 16,
                    fontWeight: 700,
                    padding: "4px 14px"
                  }}
                >
                  {status}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
    {
      height: 630,
      width: 1200
    }
  );
}

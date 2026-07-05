import { ImageResponse } from "next/og";

export const runtime = "edge";

export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "#f8fafa",
          display: "flex",
          height: "100%",
          justifyContent: "center",
          width: "100%"
        }}
      >
        <div
          style={{
            alignItems: "center",
            background: "#ffffff",
            border: "1px solid #e5eeee",
            borderRadius: 32,
            boxShadow: "0 24px 70px rgba(15, 23, 42, 0.12)",
            display: "flex",
            gap: 56,
            padding: 56,
            width: 980
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            <div
              style={{
                alignItems: "center",
                display: "flex",
                gap: 14,
                marginBottom: 28
              }}
            >
              <div
                style={{
                  alignItems: "center",
                  background: "#0F6E56",
                  borderRadius: 16,
                  color: "white",
                  display: "flex",
                  fontSize: 34,
                  fontWeight: 900,
                  height: 56,
                  justifyContent: "center",
                  width: 56
                }}
              >
                J
              </div>
              <div style={{ color: "#0a0a0a", fontSize: 42, fontWeight: 900 }}>
                Jobby
              </div>
            </div>
            <div
              style={{
                color: "#050505",
                fontSize: 58,
                fontWeight: 900,
                letterSpacing: "-0.04em",
                lineHeight: 1.02
              }}
            >
              Sabé cuánto matcheás antes de aplicar
            </div>
            <div
              style={{
                color: "#54615d",
                fontSize: 25,
                lineHeight: 1.35,
                marginTop: 22
              }}
            >
              Match score, ATS y gaps reales con IA para preparar mejores
              postulaciones.
            </div>
          </div>
          <div
            style={{
              background: "#ffffff",
              border: "1px solid #dfe9e6",
              borderRadius: 24,
              boxShadow: "0 18px 40px rgba(15, 23, 42, 0.10)",
              display: "flex",
              flexDirection: "column",
              padding: 30,
              width: 320
            }}
          >
            <div style={{ color: "#64716d", fontSize: 20 }}>Match Score</div>
            <div style={{ color: "#050505", fontSize: 82, fontWeight: 900 }}>
              87
            </div>
            {[
              ["Skills técnicas", "92%", "#0F6E56"],
              ["Seniority", "84%", "#1D9E75"],
              ["ATS", "76%", "#F0A500"],
              ["Brechas críticas", "18%", "#E24B4A"]
            ].map(([label, value, color]) => (
              <div key={label} style={{ marginTop: 16 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    color: "#111",
                    fontSize: 16,
                    fontWeight: 700
                  }}
                >
                  <span>{label}</span>
                  <span>{value}</span>
                </div>
                <div
                  style={{
                    background: "#edf2f1",
                    borderRadius: 999,
                    height: 9,
                    marginTop: 8,
                    overflow: "hidden"
                  }}
                >
                  <div
                    style={{
                      background: color,
                      borderRadius: 999,
                      height: 9,
                      width: value
                    }}
                  />
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

import { ImageResponse } from "next/og";

export const runtime = "edge";
// Google recomienda un favicon cuadrado de más de 48 px para mostrarlo en los resultados; el
// navegador lo reduce solo en la pestaña. `favicon.ico` (16 a 96 px) cubre a quien pide ese archivo.
export const size = {
  width: 96,
  height: 96
};
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "#2BD48A",
          borderRadius: 24,
          color: "#1D1D1B",
          display: "flex",
          fontSize: 60,
          fontWeight: 700,
          height: "100%",
          justifyContent: "center",
          letterSpacing: "-0.04em",
          width: "100%"
        }}
      >
        J
      </div>
    ),
    {
      ...size
    }
  );
}

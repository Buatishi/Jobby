import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = {
  width: 32,
  height: 32
};
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "#2BD48A",
          borderRadius: 8,
          color: "#1D1D1B",
          display: "flex",
          fontSize: 20,
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

import { ImageResponse } from "next/og";

export const runtime = "edge";

export function GET() {
  return new ImageResponse(
    <div
      style={{
        display: "flex",
        width: 1200,
        height: 630,
        background: "#f5f6f4",
        color: "#1c272d",
        fontFamily: "sans-serif",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "58%",
          padding: "48px",
        }}
      >
        <div style={{ fontSize: 28, fontWeight: 700 }}>find sherpas</div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            marginTop: 62,
            fontSize: 61,
            lineHeight: 1.04,
            fontWeight: 700,
            letterSpacing: "-2px",
          }}
        >
          <span>They know</span>
          <span>what they want.</span>
          <span>Does your search?</span>
        </div>
        <div style={{ fontSize: 25, marginTop: 35, maxWidth: 470 }}>
          On-site search optimization for ecommerce.
        </div>
        <div style={{ fontSize: 18, marginTop: "auto" }}>findsherpas.com</div>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 12,
          width: "42%",
          padding: 38,
          background: "#293b44",
          color: "white",
          fontSize: 68,
          lineHeight: 1.1,
        }}
      >
        <span>black</span>
        <span>dress</span>
        <span>for a</span>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            background: "#dce5e8",
            color: "#1c272d",
            padding: "8px 12px",
            fontSize: 56,
            fontWeight: 700,
          }}
        >
          <span>winter</span>
          <span>wedding</span>
        </div>
      </div>
    </div>,
    { width: 1200, height: 630 },
  );
}

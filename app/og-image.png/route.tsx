import { ImageResponse } from "next/og";

export const runtime = "edge";

export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "1200px",
          height: "630px",
          backgroundColor: "#09090b",
          padding: "80px",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        {/* Top accent line */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "4px",
            background: "linear-gradient(90deg, #0891b2, #06b6d4)",
          }}
        />

        {/* Brand mark */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              backgroundColor: "#ffffff",
              borderRadius: "10px",
            }}
          />
          <span
            style={{
              color: "#ffffff",
              fontSize: "22px",
              fontWeight: "600",
              letterSpacing: "-0.01em",
            }}
          >
            Find Sherpas
          </span>
        </div>

        {/* Main content */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            flexGrow: 1,
            justifyContent: "center",
          }}
        >
          <div
            style={{
              color: "#0891b2",
              fontSize: "16px",
              fontWeight: "600",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: "28px",
            }}
          >
            Internal search audit
          </div>

          <div
            style={{
              color: "#ffffff",
              fontSize: "60px",
              fontWeight: "700",
              letterSpacing: "-0.03em",
              lineHeight: "1.1",
              maxWidth: "860px",
            }}
          >
            Internal search audits for ecommerce
          </div>

          <div
            style={{
              color: "#71717a",
              fontSize: "24px",
              fontWeight: "400",
              marginTop: "28px",
              letterSpacing: "-0.01em",
            }}
          >
            Ranking · Relevance · Query interpretation
          </div>
        </div>

        {/* Bottom right: URL */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <span
            style={{
              color: "#3f3f46",
              fontSize: "16px",
              fontWeight: "400",
              letterSpacing: "0.02em",
            }}
          >
            findsherpas.com
          </span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    },
  );
}

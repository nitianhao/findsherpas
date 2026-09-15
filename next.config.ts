import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return ["/report/:path*", "/crm/:path*", "/stripe/:path*", "/api/:path*"].map(
      (source) => ({
        source,
        headers: [
          {
            key: "X-Robots-Tag",
            value: "noindex, nofollow, noarchive, nosnippet, noimageindex",
          },
        ],
      }),
    );
  },
};

export default nextConfig;

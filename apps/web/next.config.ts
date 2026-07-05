import type { NextConfig } from "next";

const sensitiveHeaders = [
  {
    key: "X-Robots-Tag",
    value: "noindex, nofollow, noarchive, noimageindex"
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin"
  }
];

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/dashboard/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/profile/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/jobs/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/ats/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/reality-gap/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/interview-kits/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/wizard/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/billing/:path*",
        headers: sensitiveHeaders
      },
      {
        source: "/api/:path*",
        headers: sensitiveHeaders
      }
    ];
  }
};

export default nextConfig;

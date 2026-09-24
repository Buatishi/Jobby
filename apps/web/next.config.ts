import type { NextConfig } from "next";

const securityHeaders = [
  {
    key: "X-Content-Type-Options",
    value: "nosniff"
  },
  {
    key: "X-Frame-Options",
    value: "SAMEORIGIN"
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin"
  }
];

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

// Sin variables se usa la API local de desarrollo: nunca un servicio de producción por
// defecto. Todo /api/backend/* pasa por esta reescritura (beforeFiles, antes que cualquier
// ruta propia), así que no hace falta otro proxy.
function getBackendBaseUrl() {
  return (
    process.env.API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  )
    .replace(/\/$/, "")
    .replace(/\/api\/v1$/, "");
}

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = getBackendBaseUrl();

    return {
      beforeFiles: [
        {
          source: "/api/backend/api/v1/:path*",
          destination: `${backendUrl}/api/v1/:path*`
        },
        {
          source: "/api/backend/:path*",
          destination: `${backendUrl}/api/v1/:path*`
        }
      ]
    };
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders
      },
      {
        source: "/admin/:path*",
        headers: sensitiveHeaders
      },
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

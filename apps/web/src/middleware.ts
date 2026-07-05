import { NextResponse, type NextRequest } from "next/server";

const aiCrawlerPatterns = [
  /GPTBot/i,
  /ChatGPT-User/i,
  /ClaudeBot/i,
  /Claude-User/i,
  /Google-Extended/i,
  /PerplexityBot/i,
  /Amazonbot/i,
  /Bytespider/i,
  /CCBot/i,
  /Applebot-Extended/i,
  /Meta-ExternalAgent/i,
  /YouBot/i,
  /Anthropic-ai/i,
  /OAI-SearchBot/i
];

const sensitivePrefixes = [
  "/api",
  "/dashboard",
  "/profile",
  "/jobs",
  "/ats",
  "/reality-gap",
  "/interview-kits",
  "/wizard",
  "/billing"
];

function isKnownAiCrawler(userAgent: string) {
  return aiCrawlerPatterns.some((pattern) => pattern.test(userAgent));
}

function isSensitivePath(pathname: string) {
  return sensitivePrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const userAgent = request.headers.get("user-agent") ?? "";

  if (isSensitivePath(pathname) && isKnownAiCrawler(userAgent)) {
    return new NextResponse("Automated access is not allowed for this route.", {
      status: 403,
      headers: {
        "X-Robots-Tag": "noindex, nofollow, noarchive, noimageindex"
      }
    });
  }

  const response = NextResponse.next();

  if (isSensitivePath(pathname)) {
    response.headers.set(
      "X-Robots-Tag",
      "noindex, nofollow, noarchive, noimageindex"
    );
  }

  return response;
}

export const config = {
  matcher: [
    "/api/:path*",
    "/dashboard/:path*",
    "/profile/:path*",
    "/jobs/:path*",
    "/ats/:path*",
    "/reality-gap/:path*",
    "/interview-kits/:path*",
    "/wizard/:path*",
    "/billing/:path*"
  ]
};

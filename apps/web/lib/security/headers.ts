// Cabeceras de seguridad de la web. La política de contenido arranca en modo "solo
// reporte": el navegador avisa en la consola qué bloquearía, pero no bloquea nada. Cuando
// no queden avisos con el uso real, se pasa a `Content-Security-Policy` (ver Decisión 28).
//
// 'unsafe-inline' en scripts y estilos lo exige Next.js para su arranque y los estilos en
// línea; una política con nonces es el paso siguiente. `unsafe-eval` no se permite.
export const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  // La API pasa por /api/backend (mismo origen). El navegador habla además con Supabase
  // (sesión) y con Sentry (errores).
  "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://*.sentry.io https://*.ingest.sentry.io https://*.ingest.us.sentry.io",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'self'"
].join("; ");

export const securityHeaders = [
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
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=()"
  },
  {
    key: "Content-Security-Policy-Report-Only",
    value: contentSecurityPolicy
  }
];

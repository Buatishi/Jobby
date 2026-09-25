"use client";

import { RouteError } from "@/components/route-error";

// Dentro del layout de la app: la barra lateral sigue visible y se puede navegar.
export default function SectionError(props: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <RouteError {...props} home="dashboard" />;
}

import type { Metadata } from "next";

import { CheckoutUnavailableView } from "@/components/checkout-unavailable-view";

export const metadata: Metadata = {
  title: "Jobby — Estamos trabajando en esto",
  // Es un aviso de paso, no una página para que la encuentre un buscador.
  robots: { index: false, follow: false }
};

export default function CheckoutUnavailablePage() {
  return <CheckoutUnavailableView />;
}

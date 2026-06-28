import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PricingSuccessPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-12">
      <Card>
        <CardHeader>
          <CardTitle>Pago confirmado</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-6 text-muted-foreground">
            Tu plan Premium se activará cuando Stripe confirme la suscripción por
            webhook. Esto suele tardar unos segundos.
          </p>
          <Button asChild>
            <Link href="/dashboard">Ir al dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}

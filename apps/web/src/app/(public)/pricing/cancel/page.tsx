import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PricingCancelPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-12">
      <Card>
        <CardHeader>
          <CardTitle>Checkout cancelado</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-6 text-muted-foreground">
            No se realizó ningún cargo. Podés volver a elegir un plan cuando
            quieras.
          </p>
          <div className="flex gap-3">
            <Button asChild>
              <Link href="/pricing">Volver a pricing</Link>
            </Button>
            <Button asChild variant="ghost">
              <Link href="/dashboard">Ir al dashboard</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BillingSuccessPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-12">
      <Card>
        <CardHeader>
          <CardTitle>¡Listo! Tu cuenta ya es Premium</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-6 text-muted-foreground">
            El estado final se refleja cuando Lemon Squeezy confirma el pago por
            webhook y el dashboard vuelve a cargar tus datos.
          </p>
          <Button asChild>
            <Link href="/dashboard">Ir al dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}

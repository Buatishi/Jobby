import Link from "next/link";
import { FileSearch } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

export default function AtsPage() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <p className="text-sm font-medium text-[#0F6E56]">ATS Analyzer</p>
        <h1 className="text-3xl font-semibold">ATS</h1>
        <p className="mt-2 text-muted-foreground">
          Los reportes ATS se generan desde un puesto analizado.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-md bg-[#0F6E56]/10 text-[#0F6E56]">
            <FileSearch className="h-5 w-5" />
          </div>
          <CardTitle>Elegí un job para ver su reporte ATS</CardTitle>
          <CardDescription>
            Primero analizá un puesto. Luego vas a poder abrir su reporte y
            revisar keywords, coincidencias y problemas de formato.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link href="/dashboard">Analizar nuevo job</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}

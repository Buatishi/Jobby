import Link from "next/link";
import { FileSearch } from "lucide-react";

import { PageBanner } from "@/components/page-banner";
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
    <main className="min-h-screen bg-white p-4 pb-14">
      <PageBanner
        description="Los reportes ATS se generan desde un puesto analizado."
        eyebrow="ATS Analyzer"
        title="ATS"
      />

      <Card className="mt-5">
        <CardHeader>
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-[14px] bg-brand-ink text-brand-bright">
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

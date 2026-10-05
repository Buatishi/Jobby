"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Download, Loader2, Printer } from "lucide-react";

import { PrintableCVDocument } from "@/components/cv/printable-cv-document";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import {
  applyOptimizedSections,
  type OptimizedSection,
  type PrintableCV,
  type PrintableCVContact
} from "@/lib/cv/printable-cv";

const CONTACT_FIELDS: Array<{ key: keyof PrintableCVContact; label: string }> = [
  { key: "full_name", label: "Nombre y apellido" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Teléfono" },
  { key: "location", label: "Ciudad" },
  { key: "linkedin_url", label: "LinkedIn" }
];

// Constante para que el arreglo vacío no cambie de identidad en cada render.
const NO_SECTIONS: OptimizedSection[] = [];

const INPUT_CLASS =
  "h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

// Por defecto entra cada sección que el CV respalda; las que tienen palabras sin
// respaldo las suma la persona a mano, sabiendo qué agrega.
export function defaultIncluded(sections: OptimizedSection[]): boolean[] {
  return sections.map((section) => !section.unverified_keywords?.length);
}

export function DownloadCVPanel({
  sections = NO_SECTIONS
}: {
  sections?: OptimizedSection[];
}) {
  const [cv, setCv] = useState<PrintableCV | null>(null);
  const [contact, setContact] = useState<PrintableCVContact | null>(null);
  const [included, setIncluded] = useState<boolean[]>(() => defaultIncluded(sections));
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => setIsMounted(true), []);
  useEffect(() => setIncluded(defaultIncluded(sections)), [sections]);

  const result = useMemo(() => {
    if (!cv || !contact) {
      return null;
    }
    return applyOptimizedSections(
      { ...cv, contact },
      sections.filter((_, index) => included[index])
    );
  }, [contact, cv, included, sections]);

  async function handleOpen() {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient<PrintableCV>("/api/v1/profiles/cv");
      setCv(data);
      setContact(data.contact);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo preparar el CV."
      );
    } finally {
      setIsLoading(false);
    }
  }

  if (!cv || !contact || !result) {
    return (
      <div>
        <Button
          disabled={isLoading}
          onClick={() => void handleOpen()}
          type="button"
          variant="outline"
        >
          {isLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          Descargar CV en PDF
        </Button>
        {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-md border border-border p-4">
      <div>
        <h3 className="font-medium">Tu CV listo para descargar</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Los datos de contacto salen de tu CV. Podés corregirlos acá: no se
          guardan.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {CONTACT_FIELDS.map((field) => (
          <label className="space-y-1 text-sm" key={field.key}>
            <span className="font-medium">{field.label}</span>
            <input
              className={INPUT_CLASS}
              onChange={(event) =>
                setContact({ ...contact, [field.key]: event.target.value })
              }
              value={contact[field.key]}
            />
          </label>
        ))}
      </div>

      {sections.length > 0 ? (
        <fieldset className="space-y-2 text-sm">
          <legend className="font-medium">Secciones optimizadas que se incluyen</legend>
          {sections.map((section, index) => (
            <label className="flex items-start gap-2" key={`${section.section_name}-${index}`}>
              <input
                checked={included[index] ?? false}
                className="mt-1"
                onChange={(event) =>
                  setIncluded(
                    included.map((value, position) =>
                      position === index ? event.target.checked : value
                    )
                  )
                }
                type="checkbox"
              />
              <span>
                {section.section_name}
                {section.unverified_keywords?.length ? (
                  <span className="text-muted-foreground">
                    {" "}
                    (sin respaldo en tu CV: {section.unverified_keywords.join(", ")})
                  </span>
                ) : null}
              </span>
            </label>
          ))}
          {result.unplaced.length > 0 ? (
            <p className="text-muted-foreground">
              No pudimos ubicar en tu CV:{" "}
              {result.unplaced.map((section) => section.section_name).join(", ")}.
              Copiá ese texto a mano si querés usarlo.
            </p>
          ) : null}
        </fieldset>
      ) : null}

      <div className="max-h-96 overflow-auto rounded-md border border-border bg-muted/30 p-2">
        <PrintableCVDocument cv={result.cv} />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => window.print()} type="button">
          <Printer className="mr-2 h-4 w-4" />
          Guardar como PDF
        </Button>
        <p className="text-xs text-muted-foreground">
          En la ventana de impresión elegí «Guardar como PDF».
        </p>
      </div>

      {isMounted
        ? createPortal(
            <div className="printable-cv">
              <PrintableCVDocument cv={result.cv} />
            </div>,
            document.body
          )
        : null}
    </div>
  );
}

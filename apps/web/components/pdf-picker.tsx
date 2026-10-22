"use client";

import { FileUp, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

type PdfPickerProps = {
  file: File | null;
  busy: boolean;
  pickLabel: string;
  uploadLabel: string;
  busyLabel: string;
  // Otros motivos para no dejar subir (por ejemplo, que todavía no cargó el estado).
  uploadDisabled?: boolean;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
};

/** El selector de un PDF y su botón de subir, igual en las tarjetas de «Mi perfil». */
export function PdfPicker({
  file,
  busy,
  pickLabel,
  uploadLabel,
  busyLabel,
  uploadDisabled = false,
  onFileChange,
  onUpload
}: PdfPickerProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <label className="flex h-11 min-w-0 flex-1 cursor-pointer items-center gap-3 rounded-full border border-dashed border-border bg-muted/30 px-5 text-sm">
        <FileUp className="h-4 w-4 flex-none text-muted-foreground" />
        <span className="truncate">{file ? file.name : pickLabel}</span>
        <input
          accept="application/pdf"
          className="sr-only"
          disabled={busy}
          onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          type="file"
        />
      </label>
      <Button
        className="sm:flex-none"
        disabled={busy || !file || uploadDisabled}
        onClick={onUpload}
        type="button"
      >
        {busy ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {busyLabel}
          </>
        ) : (
          uploadLabel
        )}
      </Button>
    </div>
  );
}

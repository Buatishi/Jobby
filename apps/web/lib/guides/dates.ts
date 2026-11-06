// «2026-11-02» → «2 de noviembre de 2026». Las fechas de las guías son días sin hora: se
// formatean en UTC para que la zona horaria del servidor no las corra un día.
export function formatGuideDate(isoDate: string): string {
  return new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("es-AR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC"
  });
}

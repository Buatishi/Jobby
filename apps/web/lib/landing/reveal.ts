// Avance (0 a 1) de la frase que se pinta al scrollear: arranca cuando el bloque
// entra por abajo y termina cuando ya pasó la mitad de la pantalla.
export function revealProgress(
  rectTop: number,
  rectHeight: number,
  viewportHeight: number
): number {
  const raw = (viewportHeight * 0.85 - rectTop) / (viewportHeight * 0.5 + rectHeight);

  return Math.max(0, Math.min(1, raw));
}

export function litWords(progress: number, totalWords: number): number {
  return Math.round(Math.max(0, Math.min(1, progress)) * totalWords);
}

export type WaitForMatchOptions = {
  /** Cada cuánto se vuelve a preguntar. */
  intervalMs?: number;
  /** Cuánto se espera antes de rendirse. */
  timeoutMs?: number;
  /** Corta la espera (la persona salió de la pantalla). */
  signal?: AbortSignal;
  /** Los tests lo reemplazan para no esperar de verdad. */
  sleep?: (ms: number) => Promise<void>;
};

const DEFAULT_INTERVAL_MS = 3_000;
const DEFAULT_TIMEOUT_MS = 90_000;

function wait(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

/**
 * ¿Ya existe el match del puesto? El análisis termina antes de que se calcule: el match
 * es otra tarea que el análisis encadena, y hasta que se guarda su ruta responde 404.
 * Cualquier error cuenta como «todavía no» y se vuelve a preguntar.
 *
 * Devuelve `true` apenas existe, y `false` si se agota el tiempo o se corta la espera.
 */
export async function waitForMatch(
  probe: () => Promise<unknown>,
  options: WaitForMatchOptions = {}
): Promise<boolean> {
  const {
    intervalMs = DEFAULT_INTERVAL_MS,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal,
    sleep = wait
  } = options;
  let waitedMs = 0;

  while (!signal?.aborted) {
    try {
      await probe();
      return true;
    } catch {
      // Todavía no se guardó: se vuelve a preguntar.
    }
    if (waitedMs >= timeoutMs) {
      return false;
    }
    await sleep(intervalMs);
    waitedMs += intervalMs;
  }

  return false;
}

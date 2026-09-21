/**
 * Manejo del arranque en frío de la API (Render Free se duerme tras 15 min sin tráfico
 * y tarda ~40 s en despertar). Tres piezas, todas sin costo y sin servicios externos:
 *
 * 1. `warmUpApi`: al abrir la web dispara un pedido liviano a `/health` (público, sin datos)
 *    para que la API despierte mientras la persona lee o inicia sesión.
 * 2. `fetchWithColdStartRetry`: reintenta con espera creciente cuando la API todavía no
 *    respondió. Solo para GET/HEAD: reintentar un POST podría duplicar una acción.
 * 3. `coldStartNotice`: estado observable que muestra un aviso si un pedido tarda de más.
 *
 * Ver docs/operacion/arranque-en-frio.md.
 */

export const WARMUP_STORAGE_KEY = "jobby:api-warmup-at";
export const WARMUP_TTL_MS = 10 * 60 * 1000;
export const WARMUP_PATH = "/api/backend/health";
export const SLOW_REQUEST_MS = 4_000;
export const RETRY_DELAYS_MS: readonly number[] = [
  1_000, 2_000, 4_000, 8_000, 15_000, 20_000
];

const RETRYABLE_METHODS = new Set(["GET", "HEAD"]);
const GATEWAY_STATUSES = new Set([502, 503, 504]);

type StorageLike = Pick<Storage, "getItem" | "setItem">;

export function getSessionStorage(): StorageLike | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.sessionStorage;
  } catch {
    return undefined;
  }
}

export function shouldWarmUp(
  storage: StorageLike | undefined,
  now: number
): boolean {
  try {
    const lastWarmUp = Number(storage?.getItem(WARMUP_STORAGE_KEY));
    return !(
      Number.isFinite(lastWarmUp) &&
      lastWarmUp > 0 &&
      now - lastWarmUp < WARMUP_TTL_MS
    );
  } catch {
    return true;
  }
}

type WarmUpOptions = {
  fetchFn?: typeof fetch;
  storage?: StorageLike;
  now?: () => number;
  path?: string;
};

/** Devuelve true si disparó el pedido. Nunca lanza ni espera la respuesta. */
export function warmUpApi(options: WarmUpOptions = {}): boolean {
  const {
    fetchFn = typeof fetch === "function" ? fetch : undefined,
    storage = getSessionStorage(),
    now = Date.now,
    path = WARMUP_PATH
  } = options;

  if (!fetchFn || !shouldWarmUp(storage, now())) {
    return false;
  }

  try {
    storage?.setItem(WARMUP_STORAGE_KEY, String(now()));
  } catch {
    // Sin storage disponible: se dispara igual, una vez por carga de página.
  }

  try {
    void fetchFn(path, {
      cache: "no-store",
      credentials: "omit",
      keepalive: true
    }).catch(() => undefined);
  } catch {
    return false;
  }

  return true;
}

export function isRetryableMethod(method: string | undefined): boolean {
  return RETRYABLE_METHODS.has((method ?? "GET").toUpperCase());
}

export function isGatewayStatus(status: number): boolean {
  return GATEWAY_STATUSES.has(status);
}

function isNetworkError(error: unknown): boolean {
  // fetch() rechaza con TypeError cuando no logra conectar; otros errores (por ejemplo
  // de autenticación) no son de red y no se reintentan.
  return error instanceof TypeError;
}

type RetryOptions = {
  method?: string;
  delays?: readonly number[];
  sleep?: (ms: number) => Promise<void>;
};

const defaultSleep = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

export async function fetchWithColdStartRetry(
  send: () => Promise<Response>,
  options: RetryOptions = {}
): Promise<Response> {
  const { method, delays = RETRY_DELAYS_MS, sleep = defaultSleep } = options;
  const canRetry = isRetryableMethod(method);

  for (let attempt = 0; ; attempt += 1) {
    let response: Response | undefined;
    let failure: unknown;

    try {
      response = await send();
    } catch (error) {
      failure = error;
    }

    const retryable =
      response === undefined
        ? isNetworkError(failure)
        : isGatewayStatus(response.status);

    if (!canRetry || !retryable || attempt >= delays.length) {
      if (response !== undefined) {
        return response;
      }
      throw failure;
    }

    await sleep(delays[attempt] as number);
  }
}

type Listener = () => void;

const listeners = new Set<Listener>();
let slowRequests = 0;

function notify() {
  listeners.forEach((listener) => listener());
}

export const coldStartNotice = {
  subscribe(listener: Listener) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
  getSnapshot: () => slowRequests > 0,
  getServerSnapshot: () => false,
  begin() {
    slowRequests += 1;
    notify();
  },
  end() {
    slowRequests = Math.max(0, slowRequests - 1);
    notify();
  }
};

export async function trackSlowRequest<T>(
  work: () => Promise<T>,
  slowAfterMs: number = SLOW_REQUEST_MS
): Promise<T> {
  let announced = false;
  const timer = setTimeout(() => {
    announced = true;
    coldStartNotice.begin();
  }, slowAfterMs);

  try {
    return await work();
  } finally {
    clearTimeout(timer);
    if (announced) {
      coldStartNotice.end();
    }
  }
}

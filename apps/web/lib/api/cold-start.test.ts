import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  WARMUP_PATH,
  WARMUP_STORAGE_KEY,
  WARMUP_TTL_MS,
  coldStartNotice,
  fetchWithColdStartRetry,
  isGatewayStatus,
  isRetryableMethod,
  shouldWarmUp,
  trackSlowRequest,
  warmUpApi
} from "./cold-start";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    }
  };
}

const okResponse = () => new Response("{}", { status: 200 });
const statusResponse = (status: number) => new Response("", { status });

describe("shouldWarmUp", () => {
  it("dispara cuando no hay registro previo", () => {
    expect(shouldWarmUp(memoryStorage(), 1_000)).toBe(true);
  });

  it("no dispara dentro del TTL y sí después", () => {
    const storage = memoryStorage({ [WARMUP_STORAGE_KEY]: "1000" });
    expect(shouldWarmUp(storage, 1_000 + WARMUP_TTL_MS - 1)).toBe(false);
    expect(shouldWarmUp(storage, 1_000 + WARMUP_TTL_MS)).toBe(true);
  });

  it("dispara si el storage no está disponible o falla", () => {
    expect(shouldWarmUp(undefined, 1_000)).toBe(true);
    const broken = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => undefined
    };
    expect(shouldWarmUp(broken, 1_000)).toBe(true);
  });
});

describe("warmUpApi", () => {
  it("hace un pedido liviano, sin credenciales, y registra la hora", () => {
    const fetchFn = vi.fn().mockResolvedValue(okResponse());
    const storage = memoryStorage();

    const fired = warmUpApi({ fetchFn, storage, now: () => 5_000 });

    expect(fired).toBe(true);
    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(fetchFn).toHaveBeenCalledWith(WARMUP_PATH, {
      cache: "no-store",
      credentials: "omit",
      keepalive: true
    });
    expect(storage.getItem(WARMUP_STORAGE_KEY)).toBe("5000");
  });

  it("no repite el pedido dentro del TTL", () => {
    const fetchFn = vi.fn().mockResolvedValue(okResponse());
    const storage = memoryStorage();

    warmUpApi({ fetchFn, storage, now: () => 5_000 });
    const second = warmUpApi({ fetchFn, storage, now: () => 6_000 });

    expect(second).toBe(false);
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it("absorbe errores de red sin lanzar", async () => {
    const fetchFn = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    expect(() =>
      warmUpApi({ fetchFn, storage: memoryStorage(), now: () => 1 })
    ).not.toThrow();
    await Promise.resolve();
  });

  it("absorbe un fetch que lanza de forma síncrona", () => {
    const fetchFn = vi.fn(() => {
      throw new Error("sync failure");
    }) as unknown as typeof fetch;

    expect(warmUpApi({ fetchFn, storage: memoryStorage(), now: () => 1 })).toBe(
      false
    );
  });
});

describe("clasificación de pedidos", () => {
  it("solo GET y HEAD son reintentables", () => {
    expect(isRetryableMethod(undefined)).toBe(true);
    expect(isRetryableMethod("get")).toBe(true);
    expect(isRetryableMethod("HEAD")).toBe(true);
    expect(isRetryableMethod("POST")).toBe(false);
    expect(isRetryableMethod("patch")).toBe(false);
    expect(isRetryableMethod("DELETE")).toBe(false);
  });

  it("solo 502, 503 y 504 son errores de puerta de enlace", () => {
    expect([502, 503, 504].every(isGatewayStatus)).toBe(true);
    expect([200, 401, 404, 500].some(isGatewayStatus)).toBe(false);
  });
});

describe("fetchWithColdStartRetry", () => {
  const delays = [10, 20, 30];

  it("reintenta un GET tras errores de red hasta que responde", async () => {
    const send = vi
      .fn<() => Promise<Response>>()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(okResponse());
    const sleep = vi.fn().mockResolvedValue(undefined);

    const response = await fetchWithColdStartRetry(send, {
      method: "GET",
      delays,
      sleep
    });

    expect(response.status).toBe(200);
    expect(send).toHaveBeenCalledTimes(3);
    expect(sleep.mock.calls.map((call) => call[0])).toEqual([10, 20]);
  });

  it("reintenta un GET ante 503 y devuelve la respuesta buena", async () => {
    const send = vi
      .fn<() => Promise<Response>>()
      .mockResolvedValueOnce(statusResponse(503))
      .mockResolvedValueOnce(okResponse());

    const response = await fetchWithColdStartRetry(send, {
      delays,
      sleep: async () => undefined
    });

    expect(response.status).toBe(200);
    expect(send).toHaveBeenCalledTimes(2);
  });

  it("agotados los reintentos devuelve el último error de puerta de enlace", async () => {
    const send = vi.fn(async () => statusResponse(504));

    const response = await fetchWithColdStartRetry(send, {
      delays,
      sleep: async () => undefined
    });

    expect(response.status).toBe(504);
    expect(send).toHaveBeenCalledTimes(delays.length + 1);
  });

  it("agotados los reintentos relanza el error de red", async () => {
    const send = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });

    await expect(
      fetchWithColdStartRetry(send, { delays, sleep: async () => undefined })
    ).rejects.toBeInstanceOf(TypeError);
    expect(send).toHaveBeenCalledTimes(delays.length + 1);
  });

  it("nunca reintenta un POST, ni por red ni por 503", async () => {
    const sleep = vi.fn().mockResolvedValue(undefined);

    const failing = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(
      fetchWithColdStartRetry(failing, { method: "POST", delays, sleep })
    ).rejects.toBeInstanceOf(TypeError);
    expect(failing).toHaveBeenCalledTimes(1);

    const gateway = vi.fn(async () => statusResponse(503));
    const response = await fetchWithColdStartRetry(gateway, {
      method: "POST",
      delays,
      sleep
    });
    expect(response.status).toBe(503);
    expect(gateway).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });

  it("no reintenta errores que no son de red ni respuestas que no son de puerta de enlace", async () => {
    const sleep = vi.fn().mockResolvedValue(undefined);

    const authFailure = vi.fn(async () => {
      throw new Error("auth");
    });
    await expect(
      fetchWithColdStartRetry(authFailure, { delays, sleep })
    ).rejects.toThrow("auth");
    expect(authFailure).toHaveBeenCalledTimes(1);

    const serverError = vi.fn(async () => statusResponse(500));
    const response = await fetchWithColdStartRetry(serverError, {
      delays,
      sleep
    });
    expect(response.status).toBe(500);
    expect(serverError).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });
});

describe("trackSlowRequest", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("no avisa si el pedido termina antes del umbral", async () => {
    const seen: boolean[] = [];
    const unsubscribe = coldStartNotice.subscribe(() =>
      seen.push(coldStartNotice.getSnapshot())
    );

    const work = trackSlowRequest(async () => "listo", 4_000);
    await vi.advanceTimersByTimeAsync(3_999);
    await expect(work).resolves.toBe("listo");

    expect(seen).toEqual([]);
    expect(coldStartNotice.getSnapshot()).toBe(false);
    unsubscribe();
  });

  it("avisa mientras el pedido tarda y lo retira al terminar", async () => {
    const seen: boolean[] = [];
    const unsubscribe = coldStartNotice.subscribe(() =>
      seen.push(coldStartNotice.getSnapshot())
    );

    const work = trackSlowRequest(
      () => new Promise<string>((resolve) => setTimeout(() => resolve("ok"), 9_000)),
      4_000
    );
    await vi.advanceTimersByTimeAsync(4_000);
    expect(coldStartNotice.getSnapshot()).toBe(true);

    await vi.advanceTimersByTimeAsync(5_000);
    await expect(work).resolves.toBe("ok");

    expect(seen).toEqual([true, false]);
    expect(coldStartNotice.getSnapshot()).toBe(false);
    unsubscribe();
  });

  it("retira el aviso aunque el pedido falle", async () => {
    const work = trackSlowRequest(
      () =>
        new Promise<string>((_, reject) =>
          setTimeout(() => reject(new Error("boom")), 6_000)
        ),
      4_000
    );
    const assertion = expect(work).rejects.toThrow("boom");

    await vi.advanceTimersByTimeAsync(4_000);
    expect(coldStartNotice.getSnapshot()).toBe(true);

    await vi.advanceTimersByTimeAsync(2_000);
    await assertion;
    expect(coldStartNotice.getSnapshot()).toBe(false);
  });

  it("cuenta pedidos lentos simultáneos", async () => {
    const slow = () =>
      new Promise<void>((resolve) => setTimeout(resolve, 8_000));
    const first = trackSlowRequest(slow, 4_000);
    const second = trackSlowRequest(slow, 4_000);

    await vi.advanceTimersByTimeAsync(4_000);
    expect(coldStartNotice.getSnapshot()).toBe(true);

    await vi.advanceTimersByTimeAsync(4_000);
    await Promise.all([first, second]);
    expect(coldStartNotice.getSnapshot()).toBe(false);
  });
});

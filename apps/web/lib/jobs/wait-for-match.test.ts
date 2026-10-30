import { describe, expect, it, vi } from "vitest";

import { waitForMatch } from "@/lib/jobs/wait-for-match";

function failingThenOk(failures: number) {
  let calls = 0;
  return vi.fn(async () => {
    calls += 1;
    if (calls <= failures) {
      throw new Error("Match no encontrado");
    }
    return { id: "match-1" };
  });
}

describe("waitForMatch", () => {
  it("answers at once when the match already exists", async () => {
    const probe = failingThenOk(0);
    const sleep = vi.fn(async () => undefined);

    await expect(waitForMatch(probe, { sleep })).resolves.toBe(true);

    expect(probe).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });

  it("keeps asking every interval until the match shows up", async () => {
    const probe = failingThenOk(2);
    const sleep = vi.fn(async () => undefined);

    await expect(
      waitForMatch(probe, { intervalMs: 3_000, sleep })
    ).resolves.toBe(true);

    expect(probe).toHaveBeenCalledTimes(3);
    expect(sleep.mock.calls).toEqual([[3_000], [3_000]]);
  });

  it("gives up when the time runs out", async () => {
    const probe = vi.fn(async () => {
      throw new Error("Match no encontrado");
    });
    const sleep = vi.fn(async () => undefined);

    await expect(
      waitForMatch(probe, { intervalMs: 3_000, timeoutMs: 9_000, sleep })
    ).resolves.toBe(false);

    // Una pregunta al empezar y una por cada espera de 3 s hasta los 9 s.
    expect(probe).toHaveBeenCalledTimes(4);
    expect(sleep).toHaveBeenCalledTimes(3);
  });

  it("counts any failure as not yet, not only a thrown Error", async () => {
    let calls = 0;
    const probe = vi.fn(async () => {
      calls += 1;
      if (calls === 1) {
        throw "sin red";
      }
      return null;
    });

    await expect(
      waitForMatch(probe, { sleep: async () => undefined })
    ).resolves.toBe(true);
  });

  it("stops asking once the person leaves the screen", async () => {
    const controller = new AbortController();
    const probe = vi.fn(async () => {
      throw new Error("Match no encontrado");
    });
    const sleep = vi.fn(async () => {
      controller.abort();
    });

    await expect(
      waitForMatch(probe, { signal: controller.signal, sleep })
    ).resolves.toBe(false);

    expect(probe).toHaveBeenCalledTimes(1);
  });

  it("does not ask at all when it was already cut", async () => {
    const controller = new AbortController();
    controller.abort();
    const probe = vi.fn(async () => ({ id: "match-1" }));

    await expect(
      waitForMatch(probe, { signal: controller.signal })
    ).resolves.toBe(false);

    expect(probe).not.toHaveBeenCalled();
  });
});

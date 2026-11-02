import { describe, expect, it } from "vitest";

import { getProfileStatus } from "@/lib/reality-gap/profile-status";

describe("getProfileStatus", () => {
  it.each([
    [{ saved: true, confirmed: true, rejected: false }, "activa"],
    [{ saved: true, confirmed: false, rejected: false }, "sin confirmar"],
    [{ saved: false, confirmed: false, rejected: false }, "no guardada"],
    [{ saved: true, confirmed: false, rejected: true }, "rechazada"],
    // Una skill que solo nombra LinkedIn y la persona había rechazado sigue rechazada.
    [{ saved: false, confirmed: false, rejected: true }, "rechazada"],
    // La API no manda confirmada y rechazada a la vez, pero si llegara, manda la baja.
    [{ saved: true, confirmed: true, rejected: true }, "rechazada"]
  ])("labels %j as %s", (skill, label) => {
    expect(getProfileStatus(skill)).toBe(label);
  });
});

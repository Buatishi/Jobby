import { describe, expect, it } from "vitest";

import { resolveWizardOwner } from "@/lib/wizard/owner";

describe("resolveWizardOwner", () => {
  it("is the id of the signed-in account", async () => {
    expect(await resolveWizardOwner(async () => ({ id: "user-1" }))).toBe("user-1");
  });

  it("is null when the account could not be loaded", async () => {
    expect(await resolveWizardOwner(async () => null)).toBeNull();
  });

  it("is null, not an error, when loading fails", async () => {
    const failing = async () => {
      throw new Error("sin conexión");
    };

    expect(await resolveWizardOwner(failing)).toBeNull();
  });
});

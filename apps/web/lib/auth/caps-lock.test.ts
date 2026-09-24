import { describe, expect, it } from "vitest";

import { isCapsLockOn } from "@/lib/auth/caps-lock";

describe("isCapsLockOn", () => {
  it("reads the Caps Lock modifier of the event", () => {
    expect(isCapsLockOn({ getModifierState: (key: string) => key === "CapsLock" })).toBe(
      true
    );
    expect(isCapsLockOn({ getModifierState: () => false })).toBe(false);
  });

  it("ignores other modifiers", () => {
    expect(isCapsLockOn({ getModifierState: (key: string) => key === "Shift" })).toBe(
      false
    );
  });

  it("is false when the event cannot tell", () => {
    expect(isCapsLockOn({})).toBe(false);
  });
});

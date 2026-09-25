import { describe, expect, it } from "vitest";

import {
  type CurrentUserProfile,
  hasPermission,
  Permission,
  planOf
} from "@/lib/auth/permissions";

function profile(permissions: string[]): CurrentUserProfile {
  return { id: "user-1", email: null, role: "any", tier: "free", permissions };
}

describe("hasPermission", () => {
  it("is true only when the API granted the permission", () => {
    expect(hasPermission(profile(["metrics:read"]), Permission.MetricsRead)).toBe(true);
    expect(hasPermission(profile([]), Permission.MetricsRead)).toBe(false);
  });

  it("does not look at the role name", () => {
    const admin = { ...profile([]), role: "admin" };

    expect(hasPermission(admin, Permission.MetricsRead)).toBe(false);
  });

  it("is false while the profile is loading or failed", () => {
    expect(hasPermission(null, Permission.MetricsRead)).toBe(false);
    expect(hasPermission(undefined, Permission.MetricsRead)).toBe(false);
  });
});

describe("planOf", () => {
  function withTier(tier: string): CurrentUserProfile {
    return { ...profile([]), tier };
  }

  it("follows the plan the API reported", () => {
    expect(planOf(withTier("premium"))).toBe("premium");
    expect(planOf(withTier("free"))).toBe("free");
  });

  it("treats an unknown plan as free", () => {
    expect(planOf(withTier("enterprise"))).toBe("free");
  });

  it("has no plan while the profile is loading or failed", () => {
    expect(planOf(null)).toBeNull();
    expect(planOf(undefined)).toBeNull();
  });
});

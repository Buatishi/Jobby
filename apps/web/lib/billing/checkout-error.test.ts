import { describe, expect, it } from "vitest";

import {
  ApiAuthenticationError,
  ApiConnectionError
} from "@/lib/api/client";
import { isCheckoutUnavailable } from "@/lib/billing/checkout-error";

describe("isCheckoutUnavailable", () => {
  it("treats an expired session as its own case", () => {
    expect(isCheckoutUnavailable(new ApiAuthenticationError())).toBe(false);
  });

  it("shows the notice for a failed checkout, an unreachable API or anything else", () => {
    expect(isCheckoutUnavailable(new Error("Los pagos todavía no están disponibles"))).toBe(true);
    expect(isCheckoutUnavailable(new ApiConnectionError())).toBe(true);
    expect(isCheckoutUnavailable("boom")).toBe(true);
  });
});

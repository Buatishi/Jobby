import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { apiClient } from "@/lib/api/client";
import {
  fetchAndRemember,
  forgetApiResources,
  rememberedResponse
} from "@/lib/api/use-api-resource";

const apiClientMock = vi.mocked(apiClient);

beforeEach(() => {
  forgetApiResources();
  apiClientMock.mockReset();
});

describe("fetchAndRemember", () => {
  it("remembers the last answer of each screen", async () => {
    apiClientMock.mockResolvedValueOnce([{ id: "job-1" }]);

    await fetchAndRemember("/api/v1/jobs");

    expect(rememberedResponse("/api/v1/jobs")).toEqual([{ id: "job-1" }]);
    expect(rememberedResponse("/api/v1/interview-kits")).toBeUndefined();
  });

  it("does not remember a failed request", async () => {
    apiClientMock.mockRejectedValueOnce(new Error("503"));

    await expect(fetchAndRemember("/api/v1/jobs")).rejects.toThrow("503");

    expect(rememberedResponse("/api/v1/jobs")).toBeUndefined();
  });

  it("forgets everything when the session changes", async () => {
    apiClientMock.mockResolvedValueOnce({ headline: "Backend Engineer" });
    await fetchAndRemember("/api/v1/profiles/me");

    forgetApiResources();

    expect(rememberedResponse("/api/v1/profiles/me")).toBeUndefined();
  });

  it("drops an answer that arrives after the session changed", async () => {
    let answer: (value: unknown) => void = () => undefined;
    apiClientMock.mockReturnValueOnce(
      new Promise((resolve) => {
        answer = resolve;
      })
    );

    const request = fetchAndRemember("/api/v1/jobs");
    forgetApiResources();
    answer([{ id: "job-of-the-previous-session" }]);
    await request;

    expect(rememberedResponse("/api/v1/jobs")).toBeUndefined();
  });
});

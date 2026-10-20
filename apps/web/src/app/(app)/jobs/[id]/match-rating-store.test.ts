import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ apiClient: vi.fn() }));

import { apiClient } from "@/lib/api/client";
import { createRatingStore } from "@/src/app/(app)/jobs/[id]/match-rating-store";

const apiClientMock = vi.mocked(apiClient);

/** Un pedido que queda abierto hasta que el test lo resuelva o lo rechace. */
function pendingRequest() {
  let resolve: (value: unknown) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  apiClientMock.mockReset();
});

describe("createRatingStore", () => {
  it("starts with the rating the report already had and nothing saved yet", () => {
    const store = createRatingStore("match-1", 3);

    expect(store.getState()).toEqual({ rating: 3, status: "idle" });
  });

  it("paints the chosen star before the API answers", () => {
    const request = pendingRequest();
    apiClientMock.mockReturnValueOnce(request.promise);
    const store = createRatingStore("match-1", null);

    void store.select(4);

    expect(store.getState()).toEqual({ rating: 4, status: "saving" });
  });

  it("sends the rating to the same endpoint as before", async () => {
    apiClientMock.mockResolvedValueOnce({ user_rating: 4 });
    const store = createRatingStore("match-1", null);

    await store.select(4);

    expect(apiClientMock).toHaveBeenCalledTimes(1);
    expect(apiClientMock).toHaveBeenCalledWith("/api/v1/matches/match-1/rating", {
      method: "PATCH",
      idempotent: true,
      body: JSON.stringify({ rating: 4 })
    });
  });

  it("notifies subscribers on every change and stops after unsubscribing", async () => {
    apiClientMock.mockResolvedValueOnce({ user_rating: 5 });
    const store = createRatingStore("match-1", null);
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);

    await store.select(5);
    expect(listener).toHaveBeenCalledTimes(2); // saving y saved

    unsubscribe();
    apiClientMock.mockResolvedValueOnce({ user_rating: 2 });
    await store.select(2);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("marks the rating as saved once the API answers", async () => {
    const request = pendingRequest();
    apiClientMock.mockReturnValueOnce(request.promise);
    const store = createRatingStore("match-1", null);

    const saving = store.select(5);
    expect(store.getState().status).toBe("saving");

    request.resolve({ user_rating: 5 });
    await saving;

    expect(store.getState()).toEqual({ rating: 5, status: "saved" });
  });

  it("goes back to the previous rating when the save fails", async () => {
    apiClientMock.mockRejectedValueOnce(new Error("503"));
    const store = createRatingStore("match-1", 2);

    await store.select(5);

    expect(store.getState()).toEqual({ rating: 2, status: "error" });
  });

  it("goes back to no rating when the first save fails", async () => {
    apiClientMock.mockRejectedValueOnce(new Error("Network down"));
    const store = createRatingStore("match-1", null);

    await store.select(3);

    expect(store.getState()).toEqual({ rating: null, status: "error" });
  });

  it("never reports success for a failed save", async () => {
    const request = pendingRequest();
    apiClientMock.mockReturnValueOnce(request.promise);
    const store = createRatingStore("match-1", null);
    const statuses: string[] = [];
    store.subscribe(() => statuses.push(store.getState().status));

    const saving = store.select(4);
    request.reject(new Error("503"));
    await saving;

    expect(statuses).toEqual(["saving", "error"]);
  });

  it("does not send a second request while one is in flight", async () => {
    const request = pendingRequest();
    apiClientMock.mockReturnValueOnce(request.promise);
    const store = createRatingStore("match-1", null);

    const first = store.select(4);
    await store.select(5);

    expect(apiClientMock).toHaveBeenCalledTimes(1);
    expect(store.getState()).toEqual({ rating: 4, status: "saving" });

    request.resolve({ user_rating: 4 });
    await first;
    expect(store.getState()).toEqual({ rating: 4, status: "saved" });
  });

  it("accepts a new rating after the previous request finished", async () => {
    apiClientMock
      .mockResolvedValueOnce({ user_rating: 4 })
      .mockResolvedValueOnce({ user_rating: 2 });
    const store = createRatingStore("match-1", null);

    await store.select(4);
    await store.select(2);

    expect(apiClientMock).toHaveBeenCalledTimes(2);
    expect(store.getState()).toEqual({ rating: 2, status: "saved" });
  });

  it("lets the user retry after a failure and clears the error", async () => {
    apiClientMock
      .mockRejectedValueOnce(new Error("503"))
      .mockResolvedValueOnce({ user_rating: 5 });
    const store = createRatingStore("match-1", null);

    await store.select(5);
    expect(store.getState().status).toBe("error");

    const retry = store.select(5);
    expect(store.getState()).toEqual({ rating: 5, status: "saving" });
    await retry;

    expect(store.getState()).toEqual({ rating: 5, status: "saved" });
  });
});

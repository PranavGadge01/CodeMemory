/**
 * Async state primitives for data-driven pages.
 *
 * The pages that consume the API resolve data before render, so this is a
 * discriminated union rather than a hook: the server component fetches, then
 * hands one of these three states to the page. Keeping it a plain type means
 * the loading/empty/error path is visible in the page's own code and stays
 * testable without React.
 */

import { ApiError } from "@/lib/api/client";

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: ApiError };

/** Wrap a promise in the discriminated union above. Never throws. */
export async function toAsyncState<T>(promise: Promise<T>): Promise<AsyncState<T>> {
  try {
    return { status: "success", data: await promise };
  } catch (error) {
    return {
      status: "error",
      error: error instanceof ApiError ? error : new ApiError("Unexpected error", "ERROR", 0),
    };
  }
}

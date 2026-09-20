/**
 * LeetCode API resources.
 *
 * Every LeetCode call the frontend makes lives here — connect, sync, status and
 * disconnect — funnelled through the shared transport in `client.ts`. Pages and
 * components import these functions rather than calling `fetch`, so the URL
 * surface and the wire types stay in one place.
 *
 * The account identifier is the LeetCode username. The backend takes no
 * password, cookie or session token anywhere in this flow, and neither does
 * this module.
 */

import { apiGet, apiPost, apiDelete } from "@/lib/api/client";
import type { LeetCodeStatusDTO, LeetCodeSyncResultDTO } from "@/lib/api/types";

/**
 * Connection and sync status. Cheap to poll: the backend serves it from the
 * persisted account record, so it survives a restart of either process.
 */
export function getLeetCodeStatus(): Promise<LeetCodeStatusDTO> {
  return apiGet<LeetCodeStatusDTO>("/leetcode/status");
}

/**
 * Connect to a public LeetCode account.
 *
 * Payload, per `LeetCodeConnectRequest` in `src/api/schemas/leetcode.py`:
 *
 *   { "username": "<leetcode username>" }
 *
 * Returns the updated status — the backend reports connection state rather than
 * a bare acknowledgement, so the caller can render what actually changed.
 */
export function connectLeetCode(username: string): Promise<LeetCodeStatusDTO> {
  return apiPost<LeetCodeStatusDTO>("/leetcode/connect", { username });
}

/**
 * Run a synchronous sync against the connected account. Takes no body: the
 * backend resolves the account server-side from the connection established
 * above, so there is nothing to send but the request itself.
 *
 * A first sync pulls a recent window of submissions and can take a while; the
 * caller is expected to show a syncing state rather than blocking silently.
 */
export function syncLeetCode(): Promise<LeetCodeSyncResultDTO> {
  return apiPost<LeetCodeSyncResultDTO>("/leetcode/sync");
}

/** Drop the connection. Imported submissions stay in the local index. */
export function disconnectLeetCode(): Promise<{ status: string }> {
  return apiDelete<{ status: string }>("/leetcode/connect");
}

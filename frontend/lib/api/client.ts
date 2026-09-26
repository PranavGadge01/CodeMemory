/**
 * Centralized API transport.
 *
 * The whole frontend talks to the FastAPI backend through this module. Pages
 * and components never call `fetch()` directly and never construct URLs —
 * they call a typed function in `lib/api/resources.ts`, which routes through
 * the helpers below.
 *
 * Error shape, per `src/api/errors.py`:
 *
 *   { "error": { "code": "...", "message": "..." } }
 *
 * That shape is preserved end to end: a failure surfaces as an `ApiError`
 * carrying the backend's own code and message, so the UI can report what
 * actually happened instead of guessing. There is deliberately no fallback to
 * mock data anywhere in this module — a failed request stays a failed request.
 */

/** The backend's canonical error body. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

/**
 * A failure talking to the API. `code` is the backend's own error code when the
 * server managed to respond with its error shape; "NETWORK_ERROR" means the
 * request never reached the server at all.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/**
 * Base URL for every request. `NEXT_PUBLIC_API_URL` is inlined at build time,
 * so the same value is available to server components and client components
 * alike. The default matches the local FastAPI server.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "http://localhost:8000/api/v1";

/** Absolute URL for a route-relative path, with optional query parameters. */
export function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = new URL(`${API_BASE_URL}${path}`);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) return null;
  try {
    return JSON.parse(text);
  } catch {
    // The server responded with something that is not JSON — most likely a
    // proxy or a crashed worker. Report it as a request failure rather than
    // letting a SyntaxError escape.
    throw new ApiError(
      `The API returned an unexpected response (HTTP ${response.status}).`,
      "BAD_RESPONSE",
      response.status,
    );
  }
}

/**
 * Run a request and either return the parsed body or throw an `ApiError`.
 * Every resource function below funnels through here, so error handling is
 * defined once.
 */
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      // The API is a local service; a stalled connection is a failure, not a
      // reason to hang the page.
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Could not reach the CodeMemory API. Check that the local server is running.",
      "NETWORK_ERROR",
      0,
    );
  }

  const body = await parseJson(response);

  if (!response.ok) {
    const errorBody = body as ApiErrorBody | null;
    const detail = errorBody?.error;
    throw new ApiError(
      detail?.message ?? `Request failed (HTTP ${response.status}).`,
      detail?.code ?? "ERROR",
      response.status,
    );
  }

  return body as T;
}

/** GET a JSON resource. Falsy/empty `params` are dropped from the query string. */
export function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>(buildUrl(path, params));
}

/** POST a JSON body and return the parsed response. */
export function apiPost<T>(path: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  return request<T>(buildUrl(path, params), {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** PUT a JSON body and return the parsed response. */
export function apiPut<T>(path: string, body: unknown): Promise<T> {
  return request<T>(buildUrl(path), {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/** DELETE a resource. */
export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(buildUrl(path), { method: "DELETE" });
}

/** True when the given failure is a network-level failure (server unreachable). */
export function isNetworkError(error: unknown): boolean {
  return error instanceof ApiError && error.code === "NETWORK_ERROR";
}

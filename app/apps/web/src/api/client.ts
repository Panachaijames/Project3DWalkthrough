// The one API client configuration (DESIGN.md 10.5). The web app calls /api/... on its own origin (Vite's dev and preview
// servers proxy it to the API); VITE_API_BASE can point it elsewhere. Imported once, for its side effect, by main.tsx.
//
// Every failure of a generated SDK call is turned into an ApiError here (one error interceptor), so the screens can tell
// a 404 (not found) from a server error or a dead API, and show the API's own message:
//   * an answer with the API's ErrorResponse body:      status, error.code, error.message, error.details
//   * FastAPI's 422 (HTTPValidationError):                status 422, code 'validation_error', the first msg
//   * any other answer:                                   status, code 'http_<status>', its text (or statusText)
//   * no answer at all (fetch threw: the API is down):    status 0, code 'network_error'
// An aborted request (a query cancelled, a loader interrupted) is passed through as it is.
import { client } from './generated/client.gen';

client.setConfig({ baseUrl: import.meta.env.VITE_API_BASE ?? '' });

export class ApiError extends Error {
  /** HTTP status; 0 when the API did not answer. */
  readonly status: number;
  /** The API's machine-readable code (project_not_found, invalid_heights ...), or network_error / validation_error / http_<n>. */
  readonly code: string;
  readonly details: Record<string, unknown> | null;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

export function isAbortError(err: unknown): boolean {
  return isRecord(err) && (err as { name?: unknown }).name === 'AbortError';
}

export const API_NOT_ANSWERING = 'the API did not answer (is it running?)';

/** The ApiError for whatever a generated call threw (`response` undefined: no answer). */
export function toApiError(err: unknown, response: Response | undefined): ApiError {
  if (err instanceof ApiError) return err;
  if (!response) {
    return new ApiError(0, 'network_error', API_NOT_ANSWERING);
  }
  const status = response.status;
  if (isRecord(err) && isRecord(err.error) && typeof err.error.code === 'string') {
    const body = err.error;
    const message = typeof body.message === 'string' && body.message ? body.message : body.code as string;
    return new ApiError(status, body.code as string, message, isRecord(body.details) ? body.details : null);
  }
  // The dev and preview servers' proxy answers 502 / 504 (and some proxies 503) with no body of the API's own when the
  // API is not running: that is "the API did not answer", not "Bad Gateway" (fix step, review finding "adversarial" 4).
  if (status === 502 || status === 503 || status === 504) {
    return new ApiError(status, 'network_error', API_NOT_ANSWERING);
  }
  if (isRecord(err) && Array.isArray(err.detail)) {
    const first = err.detail[0];
    const msg = isRecord(first) && typeof first.msg === 'string' ? first.msg : 'the request was not valid';
    return new ApiError(status, 'validation_error', msg, { detail: err.detail });
  }
  const text = typeof err === 'string' && err.trim() ? err.trim().slice(0, 200) : response.statusText || `HTTP ${status}`;
  return new ApiError(status, `http_${status}`, text);
}

client.interceptors.error.use((err, response) => (isAbortError(err) ? err : toApiError(err, response)));

/** The API did not answer at all (no response, or the proxy's empty 502 / 503 / 504). */
export function isUnreachable(err: unknown): boolean {
  return err instanceof ApiError && err.code === 'network_error';
}

/** Worth sending again by itself later: the API did not answer, or failed on its side (5xx), or was busy (408, 429). */
export function isRetryable(err: unknown): boolean {
  if (!(err instanceof ApiError)) return true;                 // a fetch that threw before any answer
  return err.code === 'network_error' || err.status >= 500 || err.status === 408 || err.status === 429;
}

/**
 * The saved heights a 412 revision_conflict carries (PUT furniture-heights with If-Match: they were changed elsewhere since
 * this tab's revision), or null for any other error.
 */
export function conflictOf(err: unknown): { revision: number; heights: Record<string, number> } | null {
  if (!(err instanceof ApiError) || err.status !== 412 || err.code !== 'revision_conflict' || !err.details) return null;
  const { revision, heights } = err.details as { revision?: unknown; heights?: unknown };
  if (typeof revision !== 'number' || !isRecord(heights)) return null;
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(heights)) if (typeof v === 'number') out[k] = v;
  return { revision, heights: out };
}

/**
 * A root-relative URL from the API (`/api/...`; the web app never builds API paths itself, DESIGN.md 10.3) made usable
 * from this page: prefixed with VITE_API_BASE when the API is on another origin. Absolute URLs pass unchanged.
 */
export function apiUrl(url: string): string {
  if (/^[a-z][a-z0-9+.-]*:/i.test(url)) return url;
  const base = client.getConfig().baseUrl ?? '';
  return `${base}${url}`;
}

export { client };

// The mock API as a fetch function, for vitest (happy-dom): vi.stubGlobal('fetch', mockFetch(mock)). The generated
// client reads globalThis.fetch on every request, so the app's own calls reach it. `delay` (ms) keeps requests pending;
// `fail` answers matching requests with an error first. The request's query string, headers and body bytes reach the
// mock too (the upload milestone's routes read If-Match, withSettings and the raw parts).
import type { MockApi } from './core';

export interface MockFetchOptions {
  /** Milliseconds before each answer (0: on the next microtasks). */
  delay?: number;
  /** Return a Response (or throw) to answer a request instead of the mock; undefined lets the mock answer. */
  intercept?: (method: string, path: string, body: string | null, req: Request) => Response | undefined | Promise<Response | undefined>;
  /** Called the moment a request is made (before its body is read). */
  onRequest?: (method: string, path: string) => void;
}

export function mockFetch(mock: MockApi, opts: MockFetchOptions = {}): typeof fetch {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const req = input instanceof Request ? input : new Request(input, init);
    const url = new URL(req.url, 'http://127.0.0.1/');
    const method = req.method.toUpperCase();
    opts.onRequest?.(method, url.pathname);
    if (req.signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError');
    const bytes = method === 'GET' || method === 'HEAD' ? null : Buffer.from(await req.arrayBuffer());
    const body = bytes ? bytes.toString('utf8') : null;
    if (opts.delay) await new Promise(r => setTimeout(r, opts.delay));
    if (req.signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError');
    const intercepted = await opts.intercept?.(method, url.pathname, body, req);
    if (intercepted) return intercepted;
    const headers: Record<string, string> = {};
    req.headers.forEach((v, k) => { headers[k.toLowerCase()] = v; });
    const res = mock.handle({ method, path: url.pathname, query: url.search.replace(/^\?/, ''), headers, body, bytes });
    return new Response(res.status === 204 ? null : new Uint8Array(res.body), { status: res.status, headers: res.headers });
  };
}

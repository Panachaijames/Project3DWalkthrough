// The raw files of a draft (docs/upload/DESIGN.md U-13.1, U-14.3): conversion report, drawing read, plan geometry,
// overlay, diff, model, stages. They are fetched by the URLs the API gives (BuildSourceInfo.urls, BuildResultInfo.urls;
// the web app never builds an API path) and typed by upload/contracts.ts. The plan is served gzip-encoded: the browser
// decodes it (Content-Encoding), so it is plain JSON here too.
// Failures become the same ApiError as the generated client's (api/client.ts), so the screens show one kind of reason.
import { ApiError, API_NOT_ANSWERING, apiUrl, isAbortError, toApiError } from '@/api/client';

/** GET a raw file by its API URL; an error answer becomes an ApiError (status 0: the API did not answer). */
export async function fetchRaw(url: string, signal?: AbortSignal): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(apiUrl(url), { signal, headers: { accept: 'application/json' } });
  } catch (err) {
    if (isAbortError(err)) throw err;
    throw new ApiError(0, 'network_error', API_NOT_ANSWERING);
  }
  if (!res.ok) {
    let body: unknown = null;
    try {
      const text = await res.text();
      try { body = JSON.parse(text); } catch { body = text; }
    } catch { /* no body */ }
    throw toApiError(body, res);
  }
  return res;
}

/** A raw JSON file by its API URL. */
export async function fetchRawJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetchRaw(url, signal);
  return (await res.json()) as T;
}

/**
 * React Query options for a raw JSON file. `token` names what produced it (the run id, or a counter that moves when a
 * prepare run finishes): a run's outputs never change, so a key is fresh for ever and a new run gives a new key.
 */
export function rawQueryOptions<T>(url: string | null | undefined, token: string | number) {
  return {
    queryKey: ['raw', url ?? '', token] as const,
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchRawJson<T>(url!, signal),
    enabled: !!url,
    staleTime: Infinity,
    retry: 1,
  };
}

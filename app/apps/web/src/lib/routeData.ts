// Loader helpers shared by the routes (DESIGN.md 15.1): address checks, and the API's 404s turned into the router's
// 404 response, which the routes' ErrorBoundary shows as the Not found page.
import type { FetchQueryOptions, QueryClient, QueryKey } from '@tanstack/react-query';
import { data, isRouteErrorResponse } from 'react-router';
import { ApiError, isUnreachable } from '../api/client';

/** ^[a-z0-9][a-z0-9-]{1,62}$ (DESIGN.md 10.1). */
export const PROJECT_ID = /^[a-z0-9][a-z0-9-]{1,62}$/;

export function notFound(message: string): never {
  throw data(message, { status: 404, statusText: 'Not Found' });
}

export function checkProjectId(id: string | undefined): string {
  if (!id || !PROJECT_ID.test(id)) notFound(`There is no project called ${JSON.stringify(id ?? '')}.`);
  return id;
}

/** A version number in the address: a whole number from 1, written without a sign or leading zeros. */
export function checkVersion(n: string | undefined): number {
  if (!n || !/^[1-9]\d{0,8}$/.test(n)) notFound(`There is no version ${JSON.stringify(n ?? '')}.`);
  return Number(n);
}

/**
 * queryClient.fetchQuery, but when the API does not answer and the cache has the data (older than staleTime), that data
 * (fix step, review finding "adversarial" 4: a version switch or Back with the API stopped replaced a working viewer with
 * an error page, for the version just on screen too). Any other failure, or nothing cached, still throws.
 */
export async function fetchOrCached<T, E, K extends QueryKey>(queryClient: QueryClient, options: FetchQueryOptions<T, E, T, K>): Promise<T> {
  try {
    return await queryClient.fetchQuery(options);
  } catch (err) {
    const cached = queryClient.getQueryData<T>(options.queryKey as QueryKey);
    if (cached !== undefined && isUnreachable(err)) return cached;
    throw err;
  }
}

/** Runs an API load; its 404 (project_not_found, version_not_found ...) becomes the router's 404 with the API's message. */
export async function loadOr404<T>(load: () => Promise<T>): Promise<T> {
  try {
    return await load();
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound(err.message);
    throw err;
  }
}

/** A 404 the ErrorBoundary shows as the Not found page (a router 404 response or an ApiError 404). */
export function isNotFoundError(err: unknown): boolean {
  return (err instanceof ApiError && err.status === 404) || (isRouteErrorResponse(err) && err.status === 404);
}

/** The message of a 404, for the Not found page. */
export function notFoundMessage(err: unknown): string | undefined {
  if (isRouteErrorResponse(err) && typeof err.data === 'string' && err.data) return err.data;
  if (err instanceof ApiError) return err.message;
  return undefined;
}

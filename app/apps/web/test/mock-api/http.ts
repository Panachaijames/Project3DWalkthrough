// The mock API's request and response shapes and its answer helpers (shared by core.ts and builds.ts).
import { createHash } from 'node:crypto';
import type { ErrorResponse } from '../../src/api/generated/types.gen';

export interface MockRequest {
  method: string;
  /** The URL's pathname (/api/...). */
  path: string;
  /** The URL's query string, without '?' ('' when none). */
  query?: string;
  /** Request headers, names in lower case (the adapters fill them; tests may leave them out). */
  headers?: Record<string, string>;
  /** The request body as text (PUT, POST). */
  body?: string | null;
  /** The request body as bytes (an upload part). */
  bytes?: Buffer | null;
}
export interface MockResponse {
  status: number;
  headers: Record<string, string>;
  body: Buffer;
}

export const JSON_TYPE = 'application/json';
export const enc = (s: string) => Buffer.from(s, 'utf8');
export const sha1Hex = (b: Buffer | string) => createHash('sha1').update(b).digest('hex');

export function json(status: number, value: unknown, headers: Record<string, string> = {}): MockResponse {
  return { status, headers: { 'content-type': JSON_TYPE, 'cache-control': 'no-cache', ...headers }, body: enc(JSON.stringify(value)) };
}
export function error(status: number, code: string, message: string, details?: Record<string, unknown>): MockResponse {
  const body: ErrorResponse = { error: { code, message, details: details ?? null } };
  return json(status, body);
}
export function noContent(): MockResponse {
  return { status: 204, headers: { 'cache-control': 'no-cache' }, body: Buffer.alloc(0) };
}
export function file(bytes: Buffer, mediaType: string, attachment?: string): MockResponse {
  const headers: Record<string, string> = {
    'content-type': mediaType,
    'cache-control': 'no-cache',
    etag: `"${sha1Hex(bytes)}"`,
    'x-content-type-options': 'nosniff',
  };
  if (attachment) {
    const ascii = attachment.replace(/[^\x20-\x7e]|["\\]/g, '_');
    headers['content-disposition'] = `attachment; filename="${ascii}"; filename*=UTF-8''${encodeURIComponent(attachment)}`;
  }
  return { status: 200, headers, body: bytes };
}
/** FastAPI's 422 for a malformed request (HTTPValidationError). */
export function validation(loc: (string | number)[], msg: string, type = 'value_error'): MockResponse {
  return json(422, { detail: [{ loc, msg, type }] });
}

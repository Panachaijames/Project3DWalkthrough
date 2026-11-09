// The browser side of an upload (docs/upload/DESIGN.md U-5.1, U-5.3): createUpload, then each part with `fetch(partUrl,
// { method: 'PUT', body })` (Blob.slice per part, Content-Type application/octet-stream), two parts in flight, progress
// per finished part, a failed part sent again after 1, 2, 5, 10 and 20 s and then given up (the screen shows Retry),
// then completeUpload. No XHR (a part is 8 MiB), no multipart library.
//
// Resume: the session id is kept in localStorage under `walkthrough-upload:<projectId>:<name>:<size>:<lastModified>`
// (every access in try/catch: storage can be missing or throw); picking the same file again (or Retry) reads the session
// back (getUpload) and sends only the parts it lacks. A session that is gone (404), expired, or for another file is
// forgotten and a new one made. The part URLs come from the API (the web app never builds an API path, D-10.3); the JSON
// routes go through the generated client.
import { ApiError, API_NOT_ANSWERING, apiUrl, isAbortError, isRetryable, toApiError } from '@/api/client';
import { cancelUpload, completeUpload, createUpload, getUpload } from '@/api/generated/sdk.gen';
import type { SourceFile, UploadSession } from '@/upload/contracts';

/** After a failed part: wait this long and send it again; past the last, the upload stops (U-5.3). */
export const PART_RETRY_DELAYS_MS: readonly number[] = [1_000, 2_000, 5_000, 10_000, 20_000];
/** Parts in flight at once. */
export const PARTS_IN_FLIGHT = 2;
/** The kinds the API takes (U-5.1): a name ending in .dwg or .dxf, any case. */
export const DRAWING_FILE = /\.(dwg|dxf)$/i;

export interface FileLike { name: string; size: number; lastModified: number; slice(start?: number, end?: number): Blob }

export interface UploadProgress {
  /** Parts the API has. */
  partsDone: number;
  parts: number;
  /** Bytes of the parts the API has. */
  bytesDone: number;
  bytes: number;
}

/** The API calls an upload makes (the generated client and fetch by default; tests pass their own). */
export interface UploadApi {
  create(req: { projectId: string; fileName: string; bytes: number }, signal: AbortSignal): Promise<UploadSession>;
  get(uploadId: string, signal: AbortSignal): Promise<UploadSession>;
  /** PUT the bytes of one part to its URL (from the session). */
  putPart(url: string, body: Blob, signal: AbortSignal): Promise<void>;
  complete(uploadId: string, signal: AbortSignal): Promise<SourceFile>;
  cancel(uploadId: string): Promise<void>;
}

export interface UploadOptions {
  api?: UploadApi;
  /** The storage for the resume key (default: window.localStorage, which may throw). */
  storage?: () => Storage | null | undefined;
  /** Waits ms (rejects when the signal aborts); tests pass a fast one. */
  sleep?: (ms: number, signal: AbortSignal) => Promise<void>;
  retryDelaysMs?: readonly number[];
  inFlight?: number;
  onProgress?: (p: UploadProgress) => void;
  /** The session once known (made or resumed). */
  onSession?: (s: UploadSession) => void;
  now?: () => number;
}

export interface UploadTask {
  /** The stored source, or the reason it failed (an UploadError, or UploadCancelled after cancel() or pause()). */
  readonly promise: Promise<SourceFile>;
  /** Stops the upload: aborts the parts in flight, cancels the session on the API, forgets the resume key (Remove). */
  cancel(): Promise<void>;
  /** Stops sending but keeps the session and its resume key, so picking the same file again resumes it (U-5.3): what
   *  leaving the Upload screen does (UR, V2-8: leaving cancelled the session, and the file started again at part 1). */
  pause(): void;
}

/** API refusals an upload can never get past by trying again: the file itself is refused (U-5.1). */
export const PERMANENT_UPLOAD_ERRORS: ReadonlySet<string> = new Set(['too_large', 'bad_kind', 'unsupported_version', 'not_a_drawing']);

export class UploadError extends Error {
  /** The API's code (too_large, bad_kind, unsupported_version, incomplete ...) or network_error. */
  readonly code: string;
  readonly status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = 'UploadError';
    this.code = code;
    this.status = status;
  }
}

export class UploadCancelled extends Error {
  constructor() {
    super('The upload was cancelled.');
    this.name = 'UploadCancelled';
  }
}

/** The resume key of a file (U-5.3). */
export function uploadStorageKey(projectId: string, file: Pick<FileLike, 'name' | 'size' | 'lastModified'>): string {
  return `walkthrough-upload:${projectId}:${file.name}:${file.size}:${file.lastModified}`;
}

const defaultStorage = (): Storage | null => {
  try { return typeof localStorage === 'undefined' ? null : localStorage; } catch { return null; }
};
function readKey(storage: () => Storage | null | undefined, key: string): string | null {
  try { return storage()?.getItem(key) ?? null; } catch { return null; }
}
function writeKey(storage: () => Storage | null | undefined, key: string, value: string | null): void {
  try {
    const s = storage();
    if (!s) return;
    if (value === null) s.removeItem(key); else s.setItem(key, value);
  } catch { /* storage full, blocked or missing: the upload still works, it just cannot resume */ }
}

function abortableSleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) { reject(signal.reason); return; }
    const t = setTimeout(() => { signal.removeEventListener('abort', onAbort); resolve(); }, ms);
    const onAbort = () => { clearTimeout(t); reject(signal.reason); };
    signal.addEventListener('abort', onAbort, { once: true });
  });
}

/** The generated client for the JSON routes, fetch for the parts. */
export const defaultUploadApi: UploadApi = {
  async create(req, signal) {
    const { data } = await createUpload({ body: req, signal, throwOnError: true });
    return data as UploadSession;
  },
  async get(uploadId, signal) {
    const { data } = await getUpload({ path: { uploadId }, signal, throwOnError: true });
    return data as UploadSession;
  },
  async putPart(url, body, signal) {
    let res: Response;
    try {
      res = await fetch(apiUrl(url), { method: 'PUT', body, signal, headers: { 'content-type': 'application/octet-stream' } });
    } catch (err) {
      if (isAbortError(err) || signal.aborted) throw err;
      throw new ApiError(0, 'network_error', API_NOT_ANSWERING);
    }
    if (!res.ok) {
      let parsed: unknown = null;
      try { const t = await res.text(); try { parsed = JSON.parse(t); } catch { parsed = t; } } catch { /* none */ }
      throw toApiError(parsed, res);
    }
  },
  async complete(uploadId, signal) {
    const { data } = await completeUpload({ path: { uploadId }, body: {}, signal, throwOnError: true });
    return data as SourceFile;
  },
  async cancel(uploadId) {
    await cancelUpload({ path: { uploadId }, throwOnError: true });
  },
};

/** Part i (1-based) of a file: [start, end) in bytes. */
export function partRange(i: number, partBytes: number, size: number): [number, number] {
  const start = (i - 1) * partBytes;
  return [start, Math.min(start + partBytes, size)];
}

function toUploadError(err: unknown): UploadError {
  if (err instanceof UploadError) return err;
  if (err instanceof ApiError) return new UploadError(err.message, err.code, err.status);
  const message = err instanceof Error && err.message ? err.message : 'the upload failed';
  return new UploadError(message, 'network_error', 0);
}

/** Sends one file (U-5.1, U-5.3). */
export function uploadFile(projectId: string, file: FileLike, opts: UploadOptions = {}): UploadTask {
  const api = opts.api ?? defaultUploadApi;
  const storage = opts.storage ?? defaultStorage;
  const sleep = opts.sleep ?? abortableSleep;
  const delays = opts.retryDelaysMs ?? PART_RETRY_DELAYS_MS;
  const inFlight = Math.max(1, opts.inFlight ?? PARTS_IN_FLIGHT);
  const now = opts.now ?? Date.now;
  const key = uploadStorageKey(projectId, file);
  const controller = new AbortController();
  const signal = controller.signal;
  let session: UploadSession | null = null;
  let cancelled = false;

  async function resumeOrCreate(): Promise<UploadSession> {
    const id = readKey(storage, key);
    if (id) {
      try {
        const s = await api.get(id, signal);
        const expired = Date.parse(s.expiresAt) <= now();
        if (s.projectId === projectId && s.fileName === file.name && s.bytes === file.size && !expired) return s;
      } catch (err) {
        if (signal.aborted) throw err;
        // gone (404), or not readable: a new session; anything else that is not retryable is the same
        if (isRetryable(err) && !(err instanceof ApiError && err.status === 404)) throw err;
      }
      writeKey(storage, key, null);
    }
    return api.create({ projectId, fileName: file.name, bytes: file.size }, signal);
  }

  async function sendPart(s: UploadSession, part: number): Promise<void> {
    const url = s.partUrls[part - 1];
    if (!url) throw new UploadError(`The API gave no address for part ${part}.`, 'bad_part', 0);
    const [start, end] = partRange(part, s.partBytes, file.size);
    for (let attempt = 0; ; attempt++) {
      try {
        await api.putPart(url, file.slice(start, end), signal);
        return;
      } catch (err) {
        if (signal.aborted) throw err;
        if (!isRetryable(err) || attempt >= delays.length) throw err;
        await sleep(delays[attempt]!, signal);
      }
    }
  }

  async function sendMissing(s: UploadSession): Promise<void> {
    const have = new Set(s.received);
    const sizeOf = (p: number) => { const [a, b] = partRange(p, s.partBytes, file.size); return b - a; };
    let partsDone = 0;
    let bytesDone = 0;
    for (const p of have) { if (p >= 1 && p <= s.parts) { partsDone++; bytesDone += sizeOf(p); } }
    const report = () => opts.onProgress?.({ partsDone, parts: s.parts, bytesDone, bytes: file.size });
    report();
    const queue: number[] = [];
    for (let p = 1; p <= s.parts; p++) if (!have.has(p)) queue.push(p);
    let failure: unknown = null;
    const worker = async () => {
      while (queue.length && failure === null) {
        const part = queue.shift()!;
        try {
          await sendPart(s, part);
        } catch (err) {
          if (failure === null) failure = err;
          return;
        }
        partsDone++;
        bytesDone += sizeOf(part);
        report();
      }
    };
    await Promise.all(Array.from({ length: Math.min(inFlight, queue.length) }, worker));
    if (failure !== null) throw failure;
  }

  async function run(): Promise<SourceFile> {
    try {
      session = await resumeOrCreate();
      writeKey(storage, key, session.id);
      opts.onSession?.(session);
      await sendMissing(session);
      let source: SourceFile;
      try {
        source = await api.complete(session.id, signal);
      } catch (err) {
        // 409 incomplete: a part the API does not have after all (sent twice, or lost): read the session, send the rest
        if (!(err instanceof ApiError && err.status === 409 && err.code === 'incomplete')) throw err;
        session = await api.get(session.id, signal);
        await sendMissing(session);
        source = await api.complete(session.id, signal);
      }
      writeKey(storage, key, null);
      return source;
    } catch (err) {
      if (cancelled || signal.aborted) throw new UploadCancelled();
      // a session the API refuses outright (expired between parts, 404) cannot be resumed: forget it
      if (err instanceof ApiError && err.status === 404) writeKey(storage, key, null);
      throw toUploadError(err);
    }
  }

  const promise = run();
  // the task's own rejection is the caller's to handle; never an unhandled rejection here
  promise.catch(() => undefined);

  return {
    promise,
    async cancel() {
      if (cancelled) return;
      cancelled = true;
      controller.abort(new UploadCancelled());
      writeKey(storage, key, null);
      const s = session;
      if (s) {
        try { await api.cancel(s.id); } catch { /* gone already, or the API is down: it expires in 24 h */ }
      }
    },
    pause() {
      if (cancelled || signal.aborted) return;
      controller.abort(new UploadCancelled());          // the parts in flight stop; the session and the key stay
    },
  };
}

/** Bytes as text for a file row: '1.2 MB', '512 KB', '0 B' (decimal units, one decimal from MB). */
export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return '';
  if (n < 1000) return `${n} B`;
  if (n < 1_000_000) return `${Math.round(n / 1000)} KB`;
  if (n < 1_000_000_000) return `${(n / 1_000_000).toFixed(1)} MB`;
  return `${(n / 1_000_000_000).toFixed(2)} GB`;
}

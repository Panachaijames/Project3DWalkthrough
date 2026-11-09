// The upload client (docs/upload/DESIGN.md U-5.1, U-5.3; ACCEPTANCE 2.3 U6): parts cut with Blob.slice and PUT to the
// session's part URLs, two in flight, retries after 1, 2, 5, 10 and 20 s then a failure the screen offers Retry for,
// resume from localStorage (only the missing parts sent; storage that throws), cancel, the API's refusals; and the real
// client (the generated SDK + fetch) against the mock API, bytes and sha1 included.
import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import '@/api/client';
import { ApiError } from '@/api/client';
import type { SourceFile, UploadSession } from '@/upload/contracts';
import {
  formatBytes, PART_RETRY_DELAYS_MS, partRange, UploadCancelled, UploadError, uploadFile, uploadStorageKey,
  type UploadApi, type UploadProgress,
} from '@/upload/upload';
import { createMockApi } from '../mock-api/core';
import { mockFetch } from '../mock-api/fetch';

afterEach(() => { vi.unstubAllGlobals(); });

/** A file of `size` bytes (content: the byte index mod 251). */
function fileOf(name: string, size: number, lastModified = 1_700_000_000_000): File {
  const bytes = new Uint8Array(size);
  for (let i = 0; i < size; i++) bytes[i] = i % 251;
  return new File([bytes], name, { lastModified });
}

/** An in-memory Storage. */
function memoryStorage(): Storage {
  const m = new Map<string, string>();
  return {
    get length() { return m.size; },
    clear: () => m.clear(),
    getItem: k => m.get(k) ?? null,
    key: i => [...m.keys()][i] ?? null,
    removeItem: k => { m.delete(k); },
    setItem: (k, v) => { m.set(k, String(v)); },
  };
}

interface FakeApi extends UploadApi {
  sessions: Map<string, UploadSession & { data: Map<number, Uint8Array> }>;
  puts: { part: number; bytes: number }[];
  maxInFlight: number;
  cancelled: string[];
  failPart: (part: number, attempt: number) => Error | null;
}

/** An UploadApi in memory: parts of `partBytes`, slow enough to see two in flight. */
function fakeApi(partBytes: number, opts: { putDelay?: number } = {}): FakeApi {
  let n = 0;
  let inFlight = 0;
  const attempts = new Map<number, number>();
  const api: FakeApi = {
    sessions: new Map(),
    puts: [],
    maxInFlight: 0,
    cancelled: [],
    failPart: () => null,
    async create(req) {
      const id = `u${String(++n).padStart(24, '0')}`;
      const parts = Math.max(1, Math.ceil(req.bytes / partBytes));
      const s = {
        id, projectId: req.projectId, fileName: req.fileName, bytes: req.bytes, partBytes, parts, received: [] as number[],
        expiresAt: '2999-01-01T00:00:00Z', partUrls: Array.from({ length: parts }, (_, i) => `/api/uploads/${id}/parts/${i + 1}`),
        completeUrl: `/api/uploads/${id}/complete`, url: `/api/uploads/${id}`, data: new Map<number, Uint8Array>(),
      };
      api.sessions.set(id, s);
      return { ...s, received: [...s.received] };
    },
    async get(id) {
      const s = api.sessions.get(id);
      if (!s) throw new ApiError(404, 'upload_not_found', 'There is no such upload.');
      return { ...s, received: [...s.data.keys()].sort((a, b) => a - b) };
    },
    async putPart(url, body, signal) {
      const m = /\/api\/uploads\/(u\d+)\/parts\/(\d+)$/.exec(url)!;
      const part = Number(m[2]);
      const attempt = (attempts.get(part) ?? 0) + 1;
      attempts.set(part, attempt);
      inFlight++;
      api.maxInFlight = Math.max(api.maxInFlight, inFlight);
      try {
        await new Promise((resolve, reject) => {
          const t = setTimeout(resolve, opts.putDelay ?? 5);
          signal.addEventListener('abort', () => { clearTimeout(t); reject(signal.reason); }, { once: true });
        });
        const fail = api.failPart(part, attempt);
        if (fail) throw fail;
        api.sessions.get(m[1]!)!.data.set(part, new Uint8Array(await body.arrayBuffer()));
        api.puts.push({ part, bytes: body.size });
      } finally {
        inFlight--;
      }
    },
    async complete(id) {
      const s = api.sessions.get(id)!;
      const missing = [];
      for (let i = 1; i <= s.parts; i++) if (!s.data.has(i)) missing.push(i);
      if (missing.length) throw new ApiError(409, 'incomplete', 'parts missing', { missing });
      const all = Buffer.concat([...Array(s.parts)].map((_, i) => Buffer.from(s.data.get(i + 1)!)));
      return { sha1: createHash('sha1').update(all).digest('hex'), name: s.fileName, bytes: all.length, kind: 'dwg', formatVersion: 'AC1032', uploadedAt: '2026-11-04T00:00:00Z' } satisfies SourceFile;
    },
    async cancel(id) { api.cancelled.push(id); api.sessions.delete(id); },
  };
  return api;
}

const noSleep = (delays: number[]) => async (ms: number) => { delays.push(ms); };

describe('parts', () => {
  it('cuts a file into parts of partBytes, the last the rest', () => {
    expect(partRange(1, 8, 20)).toEqual([0, 8]);
    expect(partRange(2, 8, 20)).toEqual([8, 16]);
    expect(partRange(3, 8, 20)).toEqual([16, 20]);
  });

  it('sends every part once, two in flight, reports progress per part, completes with the sha1 of the whole file', async () => {
    const api = fakeApi(10, { putDelay: 15 });
    const file = fileOf('L1.dwg', 95);
    const progress: UploadProgress[] = [];
    const storage = memoryStorage();
    const task = uploadFile('bank-sampeng', file, { api, storage: () => storage, onProgress: p => progress.push({ ...p }) });
    const source = await task.promise;
    expect(api.puts.map(p => p.part).sort((a, b) => a - b)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    expect(api.puts.find(p => p.part === 10)!.bytes).toBe(5);
    expect(api.maxInFlight).toBe(2);
    expect(progress[0]).toEqual({ partsDone: 0, parts: 10, bytesDone: 0, bytes: 95 });
    expect(progress.at(-1)).toEqual({ partsDone: 10, parts: 10, bytesDone: 95, bytes: 95 });
    expect(progress.map(p => p.partsDone)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    const want = createHash('sha1').update(Buffer.from(await file.arrayBuffer())).digest('hex');
    expect(source.sha1).toBe(want);
    expect(storage.getItem(uploadStorageKey('bank-sampeng', file))).toBeNull();   // forgotten once complete
  });
});

describe('retries', () => {
  it('a failed part is sent again after 1, 2, 5, 10 and 20 s; after that the upload fails (Retry on the screen)', async () => {
    expect(PART_RETRY_DELAYS_MS).toEqual([1_000, 2_000, 5_000, 10_000, 20_000]);
    const api = fakeApi(10);
    api.failPart = part => (part === 2 ? new ApiError(503, 'network_error', 'the API did not answer (is it running?)') : null);
    const delays: number[] = [];
    const task = uploadFile('p1', fileOf('a.dwg', 30), { api, sleep: noSleep(delays), storage: () => memoryStorage() });
    await expect(task.promise).rejects.toBeInstanceOf(UploadError);
    await expect(task.promise).rejects.toThrow('the API did not answer (is it running?)');
    expect(delays).toEqual([1_000, 2_000, 5_000, 10_000, 20_000]);
  });

  it('a part that fails twice then goes through: the upload completes', async () => {
    const api = fakeApi(10);
    api.failPart = (part, attempt) => (part === 3 && attempt <= 2 ? new TypeError('Failed to fetch') : null);
    const delays: number[] = [];
    const source = await uploadFile('p1', fileOf('a.dwg', 30), { api, sleep: noSleep(delays), storage: () => memoryStorage() }).promise;
    expect(source.bytes).toBe(30);
    expect(delays).toEqual([1_000, 2_000]);
  });

  it('a refusal (4xx) is not retried', async () => {
    const api = fakeApi(10);
    api.failPart = () => new ApiError(422, 'bad_part', 'Part 1 must be 10 bytes.');
    const delays: number[] = [];
    await expect(uploadFile('p1', fileOf('a.dwg', 30), { api, sleep: noSleep(delays) }).promise).rejects.toThrow('Part 1 must be 10 bytes.');
    expect(delays).toEqual([]);
  });

  it('createUpload refused (413 too_large): fails at once with the API\'s reason and code', async () => {
    const api = fakeApi(10);
    api.create = async () => { throw new ApiError(413, 'too_large', 'This file is larger than 300 MiB, the upload limit.'); };
    const err = await uploadFile('p1', fileOf('big.dwg', 30), { api }).promise.then(() => null, (e: unknown) => e as UploadError);
    if (!err) throw new Error('expected a refusal');
    expect(err).toBeInstanceOf(UploadError);
    expect(err.code).toBe('too_large');
    expect(err.message).toBe('This file is larger than 300 MiB, the upload limit.');
  });
});

describe('resume (U-5.3)', () => {
  it('picking the same file again resumes its session: only the parts the session lacks are sent', async () => {
    const api = fakeApi(10);
    const storage = memoryStorage();
    const file = fileOf('L2.dwg', 50);
    api.failPart = part => (part >= 4 ? new ApiError(422, 'bad_part', 'stop here') : null);
    await expect(uploadFile('p1', file, { api, storage: () => storage, inFlight: 1 }).promise).rejects.toThrow('stop here');
    const id = storage.getItem(uploadStorageKey('p1', file));
    expect(id).toMatch(/^u\d{24}$/);
    expect(api.puts.map(p => p.part)).toEqual([1, 2, 3]);
    // a reload, the same file picked again
    api.failPart = () => null;
    api.puts.length = 0;
    const again = fileOf('L2.dwg', 50);
    const source = await uploadFile('p1', again, { api, storage: () => storage }).promise;
    expect(api.puts.map(p => p.part).sort()).toEqual([4, 5]);
    expect(api.sessions.size).toBe(1);
    expect(source.bytes).toBe(50);
    expect(storage.getItem(uploadStorageKey('p1', file))).toBeNull();
  });

  it('the key names the project, the file name, size and date', () => {
    expect(uploadStorageKey('bank', { name: 'I1201.dwg', size: 500, lastModified: 42 })).toBe('walkthrough-upload:bank:I1201.dwg:500:42');
  });

  it('a session that is gone (404) is forgotten and a new one made', async () => {
    const api = fakeApi(10);
    const storage = memoryStorage();
    const file = fileOf('x.dwg', 20);
    storage.setItem(uploadStorageKey('p1', file), 'u000000000000000000000099');
    const source = await uploadFile('p1', file, { api, storage: () => storage }).promise;
    expect(source.bytes).toBe(20);
    expect(api.puts.map(p => p.part).sort()).toEqual([1, 2]);
  });

  it('storage that throws on every access: the upload still works (it just cannot resume)', async () => {
    const api = fakeApi(10);
    const throwing = {
      getItem() { throw new Error('SecurityError'); },
      setItem() { throw new Error('QuotaExceededError'); },
      removeItem() { throw new Error('SecurityError'); },
    } as unknown as Storage;
    const source = await uploadFile('p1', fileOf('x.dwg', 25), { api, storage: () => throwing }).promise;
    expect(source.bytes).toBe(25);
    const none = await uploadFile('p1', fileOf('y.dwg', 5), { api, storage: () => { throw new Error('no storage'); } }).promise;
    expect(none.bytes).toBe(5);
  });

  it('complete answers 409 incomplete: the session is read again and the missing parts sent', async () => {
    const api = fakeApi(10);
    const realComplete = api.complete.bind(api);
    let first = true;
    api.complete = async (id, signal) => {
      if (first) { first = false; api.sessions.get(id)!.data.delete(2); }
      return realComplete(id, signal);
    };
    const source = await uploadFile('p1', fileOf('x.dwg', 30), { api, storage: () => memoryStorage() }).promise;
    expect(source.bytes).toBe(30);
    expect(api.puts.filter(p => p.part === 2).length).toBe(2);
  });
});

describe('cancel', () => {
  it('stops the parts in flight, cancels the session on the API and forgets the key', async () => {
    const api = fakeApi(10, { putDelay: 50 });
    const storage = memoryStorage();
    const file = fileOf('x.dwg', 100);
    const task = uploadFile('p1', file, { api, storage: () => storage });
    await new Promise(r => setTimeout(r, 20));
    expect(storage.getItem(uploadStorageKey('p1', file))).not.toBeNull();
    await task.cancel();
    await expect(task.promise).rejects.toBeInstanceOf(UploadCancelled);
    expect(api.cancelled.length).toBe(1);
    expect(storage.getItem(uploadStorageKey('p1', file))).toBeNull();
    expect(api.puts.length).toBeLessThan(10);
  });

  it('pause (leaving the Upload screen, UR V2-8) keeps the session and its key: the same file resumes', async () => {
    const api = fakeApi(10, { putDelay: 30 });
    const storage = memoryStorage();
    const file = fileOf('x.dwg', 100);
    const task = uploadFile('p1', file, { api, storage: () => storage });
    await new Promise(r => setTimeout(r, 75));
    task.pause();
    await expect(task.promise).rejects.toBeInstanceOf(UploadCancelled);
    const sent = api.puts.length;
    expect(sent).toBeGreaterThan(0);
    expect(api.cancelled.length).toBe(0);
    expect(storage.getItem(uploadStorageKey('p1', file))).not.toBeNull();
    const again = uploadFile('p1', file, { api, storage: () => storage });
    await again.promise;
    expect(api.sessions.size).toBe(1);                                   // the same session, resumed
    expect(api.puts.length).toBe(10);                                    // only the parts it lacked were sent again
  });
});

describe('the real client against the mock API', () => {
  it('createUpload, PUT each part to its URL (octet-stream), completeUpload: the stored source has the file\'s sha1', async () => {
    const mock = createMockApi();
    mock.uploads.config.partBytes = 1000;
    vi.stubGlobal('fetch', mockFetch(mock));
    const head = Buffer.from('AC1032');
    const body = Buffer.alloc(2500, 7);
    const all = Buffer.concat([head, body]);
    const file = new File([all], 'I1201 - LEVEL 1.dwg', { lastModified: 1 });
    const progress: UploadProgress[] = [];
    const source = await uploadFile('bank-sampeng', file, { storage: () => memoryStorage(), onProgress: p => progress.push(p) }).promise;
    expect(source.sha1).toBe(createHash('sha1').update(all).digest('hex'));
    expect(source).toMatchObject({ name: 'I1201 - LEVEL 1.dwg', bytes: 2506, kind: 'dwg', formatVersion: 'AC1032' });
    const puts = mock.requests.filter(r => r.method === 'PUT');
    expect(puts.map(r => r.path)).toEqual(expect.arrayContaining([1, 2, 3].map(n => expect.stringMatching(new RegExp(`/parts/${n}$`)))));
    expect(puts.every(r => r.headers?.['content-type'] === 'application/octet-stream')).toBe(true);
    expect(puts.map(r => r.bytes?.length).sort()).toEqual([1000, 1000, 506]);
    expect(progress.at(-1)).toMatchObject({ partsDone: 3, parts: 3, bytesDone: 2506 });
    expect(mock.uploads.sources('bank-sampeng').map(s => s.sha1)).toEqual([source.sha1]);
  });

  it('the API\'s refusals reach the screen as plain messages: not a drawing, older than R13', async () => {
    const mock = createMockApi();
    vi.stubGlobal('fetch', mockFetch(mock));
    const refusal = (f: File) => uploadFile('bank-sampeng', f, { storage: () => null }).promise.then(() => null, (e: unknown) => e as UploadError);
    expect((await refusal(new File(['hello'], 'notes.dwg')))?.code).toBe('bad_kind');
    const old = await refusal(new File(['AC1009 old'], 'old.dwg'));
    expect(old?.code).toBe('unsupported_version');
    expect(old?.message).toMatch(/older than R13/);
  });
});

describe('formatBytes', () => {
  it('B, KB, MB, GB', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(512_000)).toBe('512 KB');
    expect(formatBytes(1_210_000)).toBe('1.2 MB');
    expect(formatBytes(17_800_000)).toBe('17.8 MB');
  });
});

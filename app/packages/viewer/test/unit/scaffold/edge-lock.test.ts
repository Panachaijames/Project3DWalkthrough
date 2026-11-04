// tools/edge-lock.mjs, the stale-lock takeover (fix step, 3 Nov code review): two waiters that both read the same dead
// holder must not both end up holding the lock. The lock file here is the test's own (WT_EDGE_LOCK_FILE), never the
// machine's %TEMP%\wt-edge.lock.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, rmSync, utimesSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

interface Holder { step: string; pid: number; startedAt: string }
interface EdgeLock {
  LOCK_FILE: string;
  holder(): Holder | null;
  tryCreate(step: string): boolean;
  takeOverStale(stale: Holder): boolean;
}

const TMP = path.join(process.env.WT_TMP || os.tmpdir(), 'edge-lock-unit');
const FILE = path.join(TMP, 'test-edge.lock');
let L: EdgeLock;
let deadPid = 0;

beforeAll(async () => {
  rmSync(TMP, { recursive: true, force: true });
  mkdirSync(TMP, { recursive: true });
  process.env.WT_EDGE_LOCK_FILE = FILE;
  L = await import(pathToFileURL(fileURLToPath(new URL('../../../../../tools/edge-lock.mjs', import.meta.url))).href) as EdgeLock;
  deadPid = spawnSync(process.execPath, ['-e', '0']).pid!;                 // a process that has ended
});
afterAll(() => {
  delete process.env.WT_EDGE_LOCK_FILE;
  rmSync(TMP, { recursive: true, force: true });
});

const writeStale = (): Holder => {
  const stale = { step: 'crashed', pid: deadPid, startedAt: '2026-11-03T00:00:00.000Z' };
  writeFileSync(FILE, JSON.stringify(stale));
  return stale;
};

describe('edge-lock: taking over a stale lock', () => {
  it('uses the test lock file', () => {
    expect(L.LOCK_FILE).toBe(FILE);
  });

  it('two waiters that read the same dead holder: the second leaves the first one\'s new lock alone', () => {
    writeStale();
    const seenByA = L.holder()!, seenByB = L.holder()!;                   // both read the dead holder
    expect(L.takeOverStale(seenByA)).toBe(true);                         // A removes it ...
    expect(L.tryCreate('waiter-a')).toBe(true);                          // ... and holds the lock
    expect(L.takeOverStale(seenByB)).toBe(false);                        // B, late: the lock is A's now, not the dead one
    expect(L.holder()?.step).toBe('waiter-a');
    expect(L.tryCreate('waiter-b')).toBe(false);                         // one holder only
    rmSync(FILE);
  });

  it('a live holder is never taken over; a takeover in progress makes the others wait; a takeover folder left by a crash is cleared after 30 s', () => {
    writeFileSync(FILE, JSON.stringify({ step: 'live', pid: process.pid, startedAt: 'x' }));
    expect(L.takeOverStale({ step: 'live', pid: process.pid, startedAt: 'x' })).toBe(false);
    expect(L.holder()?.step).toBe('live');
    const stale = writeStale();
    mkdirSync(`${FILE}.takeover`);                                       // someone else is inside the takeover
    expect(L.takeOverStale(stale)).toBe(false);
    expect(existsSync(FILE)).toBe(true);
    const old = new Date(Date.now() - 60_000);
    utimesSync(`${FILE}.takeover`, old, old);                            // ... and died there
    expect(L.takeOverStale(stale)).toBe(false);                          // this look clears the folder
    expect(existsSync(`${FILE}.takeover`)).toBe(false);
    expect(L.takeOverStale(stale)).toBe(true);                           // the next one takes over
    expect(existsSync(FILE)).toBe(false);
  });
});

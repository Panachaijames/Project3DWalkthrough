// One headless Edge at a time on this machine (DESIGN.md 3, 18.36): a lock file %TEMP%\wt-edge.lock, created with the
// `wx` flag, holding { step, pid, startedAt }. A lock whose pid is no longer alive is stale and taken over. A waiting run
// prints who holds it (once a minute) and waits up to 45 minutes.
//   import { acquire, release } from '../tools/edge-lock.mjs';
//   await acquire('scaffold');  ...  release();
// Playwright's globalSetup / globalTeardown and every CDP runner (tools/cdp.mjs) use it; vitest and pytest do not.
//
// Taking over a stale lock (fix step, 3 Nov code review): two waiters could both read the same dead holder; the first
// unlinked it and made its own lock, then the second, whose re-check had come before that unlink, unlinked the NEW lock
// and made one too: two Edge runs at once. A takeover now happens only inside a mutex (the folder <lock>.takeover, made
// with mkdir, which only one process can do), and the holder is read again inside it: a waiter that comes second finds the
// first one's live lock (or none) and leaves it alone. A takeover folder left by a process that died inside it (it is held
// for microseconds) is cleared after 30 s. WT_EDGE_LOCK_FILE names another lock file (the unit test's own).
import { closeSync, mkdirSync, openSync, readFileSync, rmdirSync, statSync, unlinkSync, writeSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export const LOCK_FILE = process.env.WT_EDGE_LOCK_FILE || path.join(process.env.TEMP || os.tmpdir(), 'wt-edge.lock');
const TAKEOVER_DIR = `${LOCK_FILE}.takeover`;
const TAKEOVER_STALE_MS = 30_000;
const sleep = ms => new Promise(r => setTimeout(r, ms));
let held = false;

function alive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch (err) { return err.code === 'EPERM'; }
}

function readHolder() {
  try { return JSON.parse(readFileSync(LOCK_FILE, 'utf8')); } catch { return null; }
}

/** The current holder ({ step, pid, startedAt }) or null. */
export function holder() {
  return readHolder();
}

/** Creates the lock for `step` (wx); true when this process now holds it, false when the file exists. */
export function tryCreate(step) {
  let fd;
  try {
    fd = openSync(LOCK_FILE, 'wx');
  } catch (err) {
    if (err.code === 'EEXIST') return false;
    throw err;
  }
  try { writeSync(fd, JSON.stringify({ step, pid: process.pid, startedAt: new Date().toISOString() })); } finally { closeSync(fd); }
  return true;
}

/**
 * Removes the lock of `stale` (a holder read before, whose pid is gone) if, inside the takeover mutex, the lock file is
 * still that holder's. True when it was removed (the caller then tries tryCreate like any waiter).
 */
export function takeOverStale(stale) {
  try {
    mkdirSync(TAKEOVER_DIR);
  } catch (err) {
    if (err.code !== 'EEXIST') throw err;
    try { if (Date.now() - statSync(TAKEOVER_DIR).mtimeMs > TAKEOVER_STALE_MS) rmdirSync(TAKEOVER_DIR); } catch { /* gone meanwhile */ }
    return false;                                       // another waiter is taking over: look again next time
  }
  try {
    const now = readHolder();
    if (!now || now.pid !== stale.pid || now.startedAt !== stale.startedAt || alive(now.pid)) return false;
    unlinkSync(LOCK_FILE);
    return true;
  } catch {
    return false;
  } finally {
    try { rmdirSync(TAKEOVER_DIR); } catch { /* already gone */ }
  }
}

/** Takes the lock for `step`; waits (printing the holder) while another live process holds it. */
export async function acquire(step, { waitMs = 45 * 60 * 1000, pollMs = 2000 } = {}) {
  const t0 = Date.now();
  let toldAt = 0;
  for (;;) {
    if (tryCreate(step)) {
      held = true;
      process.once('exit', release);
      return;
    }
    const h = readHolder();
    if (h && h.pid === process.pid) { held = true; return; }
    if (h && !alive(h.pid)) {
      if (takeOverStale(h)) console.log(`edge-lock: took over a stale lock of '${h.step}' (pid ${h.pid} is gone)`);
      else await sleep(50);                            // another waiter is inside the takeover: look again soon
      continue;
    }
    if (Date.now() - t0 > waitMs) {
      throw new Error(`edge-lock: waited ${Math.round(waitMs / 60000)} min for '${h?.step}' (pid ${h?.pid}, since ${h?.startedAt}); giving up`);
    }
    if (Date.now() - toldAt > 60000) {
      console.log(`edge-lock: waiting for '${h?.step ?? '?'}' (pid ${h?.pid ?? '?'}, since ${h?.startedAt ?? '?'}): another browser run is going`);
      toldAt = Date.now();
    }
    await sleep(pollMs);
  }
}

/** Releases the lock if this process holds it. */
export function release() {
  if (!held) return;
  held = false;
  const h = readHolder();
  if (h && h.pid === process.pid) {
    try { unlinkSync(LOCK_FILE); } catch { /* already gone */ }
  }
}

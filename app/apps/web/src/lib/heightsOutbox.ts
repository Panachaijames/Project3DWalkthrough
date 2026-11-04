// Furniture heights typed in the staff app but not saved yet, kept in this browser until the API has them (fix step,
// review finding "adversarial" 1: a height typed while the API was not answering was sent once more on leaving the version,
// or on a reload or a closed tab, and then dropped without a word; coming back showed the old height under
// "Heights saved"). Pure helpers and localStorage: no React.
//   key    walkthrough-unsaved-heights:<projectId>:<version>
//   value  { heights, base: { revision, heights }, at }: the tab's newest map (the kinds that differ from the model's, as
//          heightschange gives it) and the saved heights it was typed over (for If-Match and the merge)
// The version page's saver writes its version's entry while a map is unsaved and removes it once the API has it; on the
// next visit the page starts from the entry and sends it; versions not on screen are sent by sendUnsent (main.tsx, at
// start-up and whenever the window comes back online or into focus). localStorage, not sessionStorage: a closed tab keeps
// it too. A blocked storage (a private window) only loses that safety net.
import type { HeightMap } from '@walkthrough/viewer';
import type { HeightOverrides } from '../api/generated/types.gen';

export const UNSENT_PREFIX = 'walkthrough-unsaved-heights:';

export interface VersionKey { projectId: string; version: number }
export interface SavedBase { revision: number; heights: HeightMap }
export interface UnsentEntry { heights: HeightMap; base: SavedBase; at: string }

const keyOf = (p: VersionKey) => `${UNSENT_PREFIX}${p.projectId}:${p.version}`;
const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

function storage(): Storage | null {
  try { return typeof localStorage === 'undefined' ? null : localStorage; } catch { return null; }
}

/** A height map read back from storage: whole numbers only (anything else is dropped). */
function heightsOf(v: unknown): HeightMap | null {
  if (!isRecord(v)) return null;
  const out: HeightMap = {};
  for (const [k, n] of Object.entries(v)) if (typeof n === 'number' && Number.isInteger(n)) out[k] = n;
  return out;
}

export function parseUnsent(raw: string | null): UnsentEntry | null {
  if (!raw) return null;
  try {
    const v: unknown = JSON.parse(raw);
    if (!isRecord(v) || !isRecord(v.base)) return null;
    const heights = heightsOf(v.heights), baseHeights = heightsOf(v.base.heights), revision = v.base.revision;
    if (!heights || !baseHeights || typeof revision !== 'number' || !Number.isInteger(revision) || revision < 0) return null;
    return { heights, base: { revision, heights: baseHeights }, at: typeof v.at === 'string' ? v.at : '' };
  } catch {
    return null;
  }
}

export function readUnsent(p: VersionKey): UnsentEntry | null {
  try { return parseUnsent(storage()?.getItem(keyOf(p)) ?? null); } catch { return null; }
}

/** Stores the entry, or removes it (null). */
export function writeUnsent(p: VersionKey, entry: UnsentEntry | null): void {
  try {
    const st = storage();
    if (!st) return;
    if (entry) st.setItem(keyOf(p), JSON.stringify(entry)); else st.removeItem(keyOf(p));
  } catch { /* storage blocked or full */ }
}

/** Every unsent entry in this browser. */
export function allUnsent(): { path: VersionKey; entry: UnsentEntry }[] {
  const out: { path: VersionKey; entry: UnsentEntry }[] = [];
  try {
    const st = storage();
    if (!st) return out;
    for (let i = 0; i < st.length; i++) {
      const key = st.key(i);
      const m = key ? /^walkthrough-unsaved-heights:([a-z0-9][a-z0-9-]{1,62}):([1-9]\d{0,8})$/.exec(key) : null;
      const entry = m ? parseUnsent(st.getItem(key!)) : null;
      if (m && entry) out.push({ path: { projectId: m[1]!, version: Number(m[2]) }, entry });
    }
  } catch { /* storage blocked */ }
  return out;
}

export const baseOf = (o: Pick<HeightOverrides, 'revision' | 'heights'>): SavedBase => ({ revision: o.revision, heights: { ...o.heights } });

/**
 * This tab's changes, applied over heights saved elsewhere: every kind whose height in `mine` differs from `base` (the saved
 * heights it was typed over) takes `mine`'s value (absent = back to the model's); every other kind keeps `theirs`.
 */
export function mergeChanges(base: HeightMap, mine: HeightMap, theirs: HeightMap): HeightMap {
  const out: HeightMap = { ...theirs };
  for (const k of new Set([...Object.keys(base), ...Object.keys(mine)])) {
    if (mine[k] === base[k]) continue;
    if (Object.prototype.hasOwnProperty.call(mine, k)) out[k] = mine[k]!; else delete out[k];
  }
  return out;
}

export function sameHeights(a: HeightMap, b: HeightMap): boolean {
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every(k => a[k] === b[k]);
}

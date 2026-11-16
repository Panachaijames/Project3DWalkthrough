// Furniture heights typed in the staff app but not saved yet, kept in this browser until the API has them (fix step,
// review finding "adversarial" 1: a height typed while the API was not answering was sent once more on leaving the version,
// or on a reload or a closed tab, and then dropped without a word; coming back showed the old height under
// "Heights saved"). Pure helpers and localStorage: no React.
//   key    walkthrough-unsaved-heights:<projectId>:<version>
//   value  { heights, pieceEdits?, base: { revision, heights, pieceEdits? }, at }: the tab's newest map (the kinds that
//          differ from the model's, as heightschange gives it) and the saved heights it was typed over (for If-Match and
//          the merge)
// The version page's saver writes its version's entry while a map is unsaved and removes it once the API has it; on the
// next visit the page starts from the entry and sends it; versions not on screen are sent by sendUnsent (main.tsx, at
// start-up and whenever the window comes back online or into focus). localStorage, not sessionStorage: a closed tab keeps
// it too. A blocked storage (a private window) only loses that safety net.
//
// Step BX (docs/boxes/DESIGN.md 6.1): the deleted furniture boxes are saved with the heights (the same PUT, revision and
// If-Match). An entry carries `pieceEdits` (the tab's edits map) ONLY while the tab's edits are unsaved: an entry without
// it is heights-only and its replay sends `{heights}`, which can never erase deletions saved elsewhere. `base.pieceEdits`
// is the saved edits the entry was made over (for the per-id merge), present only when not empty. Old entries (without
// these fields) parse as they always did.
import type { HeightMap, PieceEditMap } from '@walkthrough/viewer';
import type { HeightOverrides } from '../api/generated/types.gen';

export const UNSENT_PREFIX = 'walkthrough-unsaved-heights:';

export interface VersionKey { projectId: string; version: number }
export interface SavedBase {
  revision: number;
  heights: HeightMap;
  /** The saved deleted boxes (step BX); present only when there are some. */
  pieceEdits?: PieceEditMap;
}
export interface UnsentEntry {
  heights: HeightMap;
  /** The tab's deleted boxes, present only while they are unsaved (an empty map then means "every box restored"). */
  pieceEdits?: PieceEditMap;
  base: SavedBase;
  at: string;
}

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

/**
 * An edits map read leniently (the API's answer, a 412's details, storage, the viewer's event): only an entry whose value
 * is an object with `removed` exactly true counts, as `{removed: true}`; anything else is dropped. Not an object: {}.
 */
export function editsOf(v: unknown): PieceEditMap {
  const out: PieceEditMap = {};
  if (!isRecord(v)) return out;
  for (const [id, e] of Object.entries(v)) if (isRecord(e) && e.removed === true) out[id] = { removed: true };
  return out;
}

const hasEdits = (e: PieceEditMap | undefined): e is PieceEditMap => !!e && Object.keys(e).length > 0;

/** A SavedBase with `pieceEdits` only when not empty (so a base without deletions is `{revision, heights}` exactly). */
export function savedBase(revision: number, heights: HeightMap, pieceEdits?: PieceEditMap): SavedBase {
  return hasEdits(pieceEdits) ? { revision, heights: { ...heights }, pieceEdits: copyEdits(pieceEdits) } : { revision, heights: { ...heights } };
}

export function parseUnsent(raw: string | null): UnsentEntry | null {
  if (!raw) return null;
  try {
    const v: unknown = JSON.parse(raw);
    if (!isRecord(v) || !isRecord(v.base)) return null;
    const heights = heightsOf(v.heights), baseHeights = heightsOf(v.base.heights), revision = v.base.revision;
    if (!heights || !baseHeights || typeof revision !== 'number' || !Number.isInteger(revision) || revision < 0) return null;
    const entry: UnsentEntry = { heights, base: savedBase(revision, baseHeights, editsOf(v.base.pieceEdits)), at: typeof v.at === 'string' ? v.at : '' };
    // present = the tab's edits were unsaved (an empty map too: "every box restored"); absent = a heights-only entry
    return isRecord(v.pieceEdits) ? { heights, pieceEdits: editsOf(v.pieceEdits), base: entry.base, at: entry.at } : entry;
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

/** The saved state an API answer (or a refetch, a 412's details) stands for: `pieceEdits` read leniently, kept when not empty. */
export const baseOf = (o: Pick<HeightOverrides, 'revision' | 'heights'> & { pieceEdits?: unknown }): SavedBase =>
  savedBase(o.revision, o.heights, editsOf(o.pieceEdits));

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

/** One piece's edit as comparable text ('' = no edit); today only `removed`, later steps add members. */
function editText(e: PieceEdit | undefined): string {
  if (!e) return '';
  const keys = Object.keys(e).sort() as (keyof PieceEdit)[];
  return JSON.stringify(keys.map(k => [k, e[k]]));
}
type PieceEdit = PieceEditMap[string];

export const copyEdits = (e: PieceEditMap): PieceEditMap => Object.fromEntries(Object.entries(e).map(([id, x]) => [id, { ...x }]));

/** The same edits, whatever the order of the ids. */
export function sameEdits(a: PieceEditMap, b: PieceEditMap): boolean {
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every(id => Object.prototype.hasOwnProperty.call(b, id) && editText(a[id]) === editText(b[id]));
}

/**
 * This tab's deleted boxes, applied over edits saved elsewhere (a per-id three-way merge, as mergeChanges for the heights):
 * every id whose edit in `mine` differs from `base` (the saved edits the tab worked on) takes `mine`'s (absent = restored);
 * every other id keeps `theirs`. A set union would undo this tab's restores. The result may be open (a support restored
 * here, a piece on it deleted there): the viewer and the API close it.
 */
export function mergeEdits(base: PieceEditMap, mine: PieceEditMap, theirs: PieceEditMap): PieceEditMap {
  const out: PieceEditMap = copyEdits(theirs);
  const has = (m: PieceEditMap, id: string) => Object.prototype.hasOwnProperty.call(m, id);
  for (const id of new Set([...Object.keys(base), ...Object.keys(mine)])) {
    if (editText(base[id]) === editText(mine[id])) continue;
    if (has(mine, id)) out[id] = { ...mine[id] }; else delete out[id];
  }
  return out;
}

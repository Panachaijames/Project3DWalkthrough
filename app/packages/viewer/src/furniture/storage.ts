// Typed heights and the doorways tick in localStorage (DESIGN.md 11.2, 18.31; port of furniture_boxes.js persist / restore).
// Owner: builder C.
//   key    `<storageKeyPrefix><photoName>:<stamp>` (ctx.options.storageKey; the prototypes' key had no stamp).
//   value  the prototypes' shape { "<kind>": mm, ..., "keepDoorways": false }, the key removed when there is nothing to keep.
//   'local' (offline file): the kinds whose height differs from the STARTING heights (the model's, with the saved ones over
//           them), so a Reset to the model's heights over saved ones still holds after a reload; 'host' (staff app): no
//           heights, only the doorways tick (a per-browser preference in both modes, never sent to the API).
// Storage may be missing or blocked (a private window, site data off): the heights and the tick then last for the visit.
import type { FurnitureKind, HeightMap, ReadStoredState, StoredFurnitureState, WriteStoredState } from '../contracts';
import { heightFromData } from './logic';

const hasOwn = (o: object, key: string) => Object.prototype.hasOwnProperty.call(o, key);

/** Junk is ignored; heights are whole mm 10 - 5000 for the given kinds only; only `keepDoorways: false` turns the tick off. */
export const readStoredState: ReadStoredState = (raw, kinds) => {
  const out: StoredFurnitureState = { heights: {}, keepDoorways: true };
  try {
    const typed = JSON.parse(raw || '{}') as Record<string, unknown>;
    const heights: HeightMap = {};
    for (const k of kinds as FurnitureKind[]) {
      const v = heightFromData(typed[k.key]);                 // null / a number / a string: TypeError on null, as the prototype
      if (v !== null) heights[k.key] = v;
    }
    out.heights = heights;
    if (typed.keepDoorways === false) out.keepDoorways = false;
  } catch { /* nothing saved, or not JSON */ }
  return out;
};

/** The text to store, or null when there is nothing to keep (the key is then removed). Heights in the order of s.heights. */
export const writeStoredState: WriteStoredState = (s, mode, baseline) => {
  const typed: Record<string, number | boolean> = {};
  if (mode === 'local') {
    for (const [key, mm] of Object.entries(s.heights)) {
      if (!hasOwn(baseline, key) || baseline[key] !== mm) typed[key] = mm;
    }
  }
  if (!s.keepDoorways) typed.keepDoorways = false;
  return Object.keys(typed).length ? JSON.stringify(typed) : null;
};

/** localStorage, or null where there is none or it is blocked (reading the property throws a SecurityError then). */
function storage(): Storage | null {
  try { return typeof localStorage === 'undefined' ? null : localStorage; } catch { return null; }
}

/** The stored text under the key, or null (none, blocked). */
export function loadStored(key: string): string | null {
  try { return storage()?.getItem(key) ?? null; } catch { return null; }
}

/** Stores the text (null removes the key); a blocked or full storage is ignored: the state lasts for this visit only. */
export function saveStored(key: string, text: string | null): void {
  try {
    const st = storage();
    if (!st) return;
    if (text === null) st.removeItem(key); else st.setItem(key, text);
  } catch { /* storage blocked: the heights and the tick last for this visit only */ }
}

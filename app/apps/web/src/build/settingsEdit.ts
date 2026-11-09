// The settings changes the Build page's steps make (docs/upload/DESIGN.md U-2, U-8, U-9, U-12.3), as pure functions of
// BuildSettings (the settings saver keeps them as functions, so a 412 re-applies them on the saved settings), and the
// checks the steps show before the API does (U-13.2 settings_issues: keys, levels, boxes, heights). No React here.
import type { Vec2 } from '@walkthrough/viewer';
import type {
  Bbox,
  BuildDefaults,
  BuildSettings,
  FloorArea,
  FloorSetup,
  ItemRef,
  LayerRole,
  OpeningFix,
  OutlineEdgeFix,
  ProjectNaming,
  SetAside,
  Sha1,
  Units,
} from '@/upload/contracts';

export type Change = (s: BuildSettings) => BuildSettings;

export const UNITS: readonly Units[] = ['mm', 'cm', 'm', 'in', 'ft'];
export const UNIT_NAMES: Record<Units, string> = { mm: 'millimetres', cm: 'centimetres', m: 'metres', in: 'inches', ft: 'feet' };

/** ^[A-Za-z0-9_]{1,32}$ (U-13.2). */
export const FLOOR_KEY = /^[A-Za-z0-9_]{1,32}$/;
export const PHOTO_NAME = /^[A-Za-z0-9_.-]{1,64}$/;
export const MAX_PREFIX = /^[A-Z]{2,4}$/;
export const MAX_FILE_NAME = /^[A-Za-z0-9_.-]{1,60}\.ms$/;
/** Heights 0.05 - 50 m (U-13.2). */
export const MIN_HEIGHT = 0.05;
export const MAX_HEIGHT = 50;
/** The defaults of a new box area (U-9.1). */
export const DEFAULT_PAD = 0.5;
export const DEFAULT_MATCH = 'all' as const;
/** At most this many set-asides in one build (U-13.2). */
export const MAX_SET_ASIDE = 20_000;

/** A layer's role in the settings (a layer not listed is 'other', U-1 contracts). */
export const roleOf = (s: BuildSettings, layer: string): LayerRole => s.layers[layer] ?? 'other';

/** Sets the role of the given layers (one select, or "apply to all rows shown"). */
export const setRoles = (names: readonly string[], role: LayerRole): Change => s => {
  const layers = { ...s.layers };
  for (const n of names) layers[n] = role;
  return { ...s, layers };
};

/** The units of one source, confirmed (a change re-reads that source at once, U-7.4). */
export const setUnits = (sha1: Sha1, units: Units): Change => s => ({
  ...s,
  sources: s.sources.map(src => (src.sha1 === sha1 ? { ...src, units, unitsConfirmed: true } : src)),
});

/** Staff confirm the units the reader used. */
export const confirmUnits = (sha1: Sha1): Change => s => ({
  ...s,
  sources: s.sources.map(src => (src.sha1 === sha1 ? { ...src, unitsConfirmed: true } : src)),
});

export const updateFloor = (index: number, patch: Partial<FloorSetup>): Change => s => ({
  ...s,
  floors: s.floors.map((f, i) => (i === index ? { ...f, ...patch } : f)),
});

/** A new floor at the top: the next free key L<n>, the first source, the whole file, 3 m above the last. */
export const addFloor = (): Change => s => {
  const keys = new Set(s.floors.map(f => f.key));
  let n = s.floors.length + 1;
  while (keys.has(`L${n}`)) n++;
  const last = s.floors[s.floors.length - 1];
  const level = last ? round3(last.level + (last.wallHeight > 0 ? last.wallHeight : 3)) : 0;
  const floor: FloorSetup = {
    key: `L${n}`,
    name: `Level ${n}`,
    source: s.sources[0]?.sha1 ?? '',
    area: { kind: 'wholeFile' },
    level,
    wallHeight: last && last.wallHeight > 0 ? last.wallHeight : 3,
    slabThickness: null,
    doorHead: null,
    windowSill: null,
    windowHead: null,
    align: { method: 'auto' },
  };
  return { ...s, floors: [...s.floors, floor] };
};

export const removeFloor = (index: number): Change => s => ({ ...s, floors: s.floors.filter((_, i) => i !== index) });

/** Moves a floor up (-1) or down (+1) the list. */
export const moveFloor = (index: number, by: -1 | 1): Change => s => {
  const j = index + by;
  if (j < 0 || j >= s.floors.length) return s;
  const floors = s.floors.slice();
  [floors[index], floors[j]] = [floors[j]!, floors[index]!];
  return { ...s, floors };
};

/** A box area on the floor's sheet with the default pad and match (U-9.1). */
export const boxArea = (bbox: Bbox, pad: number = DEFAULT_PAD, match: 'all' | 'any' = DEFAULT_MATCH): FloorArea => ({
  kind: 'box',
  bbox: [round3(Math.min(bbox[0], bbox[2])), round3(Math.min(bbox[1], bbox[3])), round3(Math.max(bbox[0], bbox[2])), round3(Math.max(bbox[1], bbox[3]))],
  pad,
  match,
});

export const setDefaults = (patch: Partial<BuildDefaults>): Change => s => ({ ...s, defaults: { ...s.defaults, ...patch } });

export const setProject = (patch: Partial<BuildSettings['project'] & ProjectNaming>): Change => s => ({ ...s, project: { ...s.project, ...patch } });

/** The office (U-8.4). The same office again is no change at all (the saver then sends nothing: UR, V3-1). */
export const setOffice = (office: string | null): Change => s => (s.office === office ? s : { ...s, office });

/** Builder options (U-10.5) staff set on the Floors step (UR, V2-1): the outline suggestions and the offset (U-9.6:
 *  'auto' resets a pinned offset to the bank rule, for a project re-drawn in a new frame). */
export const setOptions = (patch: Partial<BuildSettings['options']>): Change => s => ({ ...s, options: { ...s.options, ...patch } });

/** How furniture pieces are read (U-10.5's pieceLayer: 'insert' the bank's rule, 'drawn' the suite's). */
export const setPieceLayer = (pieceLayer: BuildSettings['furniture']['pieceLayer']): Change => s =>
  (s.furniture.pieceLayer === pieceLayer ? s : { ...s, furniture: { ...s.furniture, pieceLayer } });

/** The ItemRef of a plan entry (U-7.5, U-12.3): every field from the plan geometry, never derived here. */
export function itemRef(plan: { source: Sha1; refOf(key: string): { sig: string; rsig: string; elementId: string | null; layer: string } | null },
  floor: string, key: string): ItemRef | null {
  const r = plan.refOf(key);
  if (!r) return null;
  return { floor, source: plan.source, key, sig: r.sig, rsig: r.rsig, elementId: r.elementId, layer: r.layer };
}

/** The identity of a set-aside: floor, source and key (U-12.3). */
const refId = (r: Pick<ItemRef, 'floor' | 'source' | 'key'>) => `${r.floor}\u0000${r.source}\u0000${r.key}`;

/** Sets the items aside (refs already in the settings are kept once). Linear in the set-asides and the refs (UR, V3-5:
 *  20,000 refs took 2.8 s, and 10,000 onto 10,000 3.3 s, each paid on every application). */
export const addSetAside = (refs: readonly ItemRef[], note = ''): Change => s => {
  const have = s.fixes.setAside;
  const seen = new Set(have.map(refId));
  const add: SetAside[] = [];
  for (const r of refs) {
    const id = refId(r);
    if (seen.has(id)) continue;
    seen.add(id);
    add.push({ ...r, note });
  }
  return add.length ? { ...s, fixes: { ...s.fixes, setAside: have.concat(add) } } : s;
};

/** Each key with every key that holds it ('a/b/c' -> 'a/b/c', 'a/b', 'a'): an INSERT's set-aside covers its subtree. */
export function keyAndHolders(key: string): string[] {
  const out = [key];
  for (let i = key.lastIndexOf('/'); i > 0; i = key.lastIndexOf('/', i - 1)) out.push(key.slice(0, i));
  return out;
}

/** Restores items: drops the set-asides of these keys on the floor (and those of their enclosing blocks, U-10.6). Linear
 *  in the set-asides and the keys' depth (UR, V3-5). */
export const restoreSetAside = (floor: string, keys: readonly string[]): Change => s => {
  const drop = new Set<string>();
  for (const k of keys) for (const h of keyAndHolders(k)) drop.add(h);
  const setAside = s.fixes.setAside.filter(r => !(r.floor === floor && drop.has(r.key)));
  return setAside.length === s.fixes.setAside.length ? s : { ...s, fixes: { ...s.fixes, setAside } };
};

/** The selected keys that are set aside on this floor (themselves, or inside a set-aside block), in selection order
 *  (UR, V3-5: each render spread every set-aside key for every selected key). */
export function asideOf(selected: Iterable<string>, setAsideKeys: ReadonlySet<string>): string[] {
  const out: string[] = [];
  for (const k of selected) if (keyAndHolders(k).some(h => setAsideKeys.has(h))) out.push(k);
  return out;
}

const near = (a: Vec2, b: Vec2, tol = 0.005) => Math.abs(a[0] - b[0]) <= tol && Math.abs(a[1] - b[1]) <= tol;
const sameSegment = (f: { floor: string; a: Vec2; b: Vec2 }, g: { floor: string; a: Vec2; b: Vec2 }) =>
  f.floor === g.floor && ((near(f.a, g.a) && near(f.b, g.b)) || (near(f.a, g.b) && near(f.b, g.a)));

/** An opening fix (U-12.3): replaces the fix of the same opening; kind null with no head and sill drops it. */
export const setOpeningFix = (fix: OpeningFix): Change => s => {
  const rest = s.fixes.openings.filter(f => !sameSegment(f, fix));
  const keep = fix.kind !== null || fix.head !== null || fix.sill !== null;
  return { ...s, fixes: { ...s.fixes, openings: keep ? [...rest, fix] : rest } };
};

/** An outline suggestion accepted as a wall or glass, or refused (U-12.3). */
export const setOutlineEdge = (fix: OutlineEdgeFix): Change => s => {
  const rest = s.fixes.outlineEdges.filter(f => !sameSegment(f, fix));
  return { ...s, fixes: { ...s.fixes, outlineEdges: [...rest, fix] } };
};

/** A grey furniture family given a kind (U-12.3): settings.furniture.words[kind] gains it (and leaves any other kind). */
export const setFurnitureWord = (family: string, kind: string): Change => s => {
  const words: Record<string, string[]> = {};
  for (const [k, list] of Object.entries(s.furniture.words)) {
    const rest = list.filter(w => w !== family);
    if (rest.length) words[k] = rest;
  }
  if (kind) words[kind] = [...(words[kind] ?? []), family];
  return { ...s, furniture: { ...s.furniture, words } };
};

export const round3 = (v: number) => Math.round(v * 1000) / 1000;

/** The default wall height of floor i (U-9.2): the next floor's level minus this one's; null for the top floor. */
export function defaultWallHeight(floors: readonly Pick<FloorSetup, 'level'>[], i: number): number | null {
  const next = floors[i + 1];
  const here = floors[i];
  if (!here || !next) return null;
  const h = round3(next.level - here.level);
  return h > 0 ? h : null;
}

export interface Issue { path: string; message: string }

/** What the API's settings_issues() would refuse in the floors (U-13.2), said before the save is sent. */
export function floorIssues(s: BuildSettings): Issue[] {
  const out: Issue[] = [];
  const keys = new Set<string>();
  const sources = new Set(s.sources.map(x => x.sha1));
  s.floors.forEach((f, i) => {
    const at = `floors/${i}`;
    if (!FLOOR_KEY.test(f.key)) out.push({ path: `${at}/key`, message: `"${f.key}" is not a floor key: letters, digits and _ only, at most 32` });
    else if (keys.has(f.key)) out.push({ path: `${at}/key`, message: `the key ${f.key} is used twice` });
    keys.add(f.key);
    if (!f.name.trim()) out.push({ path: `${at}/name`, message: 'a floor needs a name' });
    if (!sources.has(f.source)) out.push({ path: `${at}/source`, message: `${f.name || f.key} has no source file` });
    if (!Number.isFinite(f.level)) out.push({ path: `${at}/level`, message: `${f.name || f.key} has no level` });
    if (i > 0) {
      const prev = s.floors[i - 1]!;
      if (Number.isFinite(f.level) && Number.isFinite(prev.level) && !(f.level > prev.level)) {
        out.push({ path: `${at}/level`, message: `the levels must rise floor by floor: ${f.name || f.key} is not above ${prev.name || prev.key}` });
      }
    }
    if (!(f.wallHeight >= MIN_HEIGHT && f.wallHeight <= MAX_HEIGHT)) {
      out.push({ path: `${at}/wallHeight`, message: `${f.name || f.key} has no wall height (0.05 - 50 m)` });
    }
    for (const k of ['slabThickness', 'doorHead', 'windowSill', 'windowHead'] as const) {
      const v = f[k];
      if (v !== null && !(v >= (k === 'windowSill' ? 0 : MIN_HEIGHT) && v <= MAX_HEIGHT)) out.push({ path: `${at}/${k}`, message: `${k} must be 0.05 - 50 m` });
    }
    if (f.area.kind === 'box') {
      const [x0, y0, x1, y1] = f.area.bbox;
      if (!(x0 < x1 && y0 < y1)) out.push({ path: `${at}/area`, message: `${f.name || f.key}'s area is empty: draw or pick a box` });
      if (!(f.area.pad >= 0 && f.area.pad <= 50)) out.push({ path: `${at}/area/pad`, message: 'the pad must be 0 - 50 m' });
    }
  });
  return out;
}

/** What the API would refuse in the project naming (U-13.2). */
export function namingIssues(s: BuildSettings): Issue[] {
  const out: Issue[] = [];
  if (!PHOTO_NAME.test(s.project.photoName)) out.push({ path: 'project/photoName', message: 'photo name: letters, digits, _ . - only, at most 64' });
  if (!MAX_PREFIX.test(s.project.maxPrefix)) out.push({ path: 'project/maxPrefix', message: 'Max prefix: 2 - 4 capital letters' });
  if (!MAX_FILE_NAME.test(s.project.maxFileName)) out.push({ path: 'project/maxFileName', message: 'Max file name: letters, digits, _ . - only, ending in .ms' });
  return out;
}

/** A number typed in a field (a comma taken as a decimal point); null when empty or not a number. */
export function parseNumber(text: string): number | null {
  const t = text.trim().replace(',', '.');
  if (!t) return null;
  const v = Number(t);
  return Number.isFinite(v) ? v : null;
}

/** A metre value shown in a field: '3.7', '0', '' for null. */
export const showNumber = (v: number | null | undefined): string => (v === null || v === undefined || !Number.isFinite(v) ? '' : String(round3(v)));

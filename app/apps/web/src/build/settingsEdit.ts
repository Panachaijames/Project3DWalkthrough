// The settings changes the Build page's steps make (docs/upload/DESIGN.md U-2, U-8, U-9, U-12.3), as pure functions of
// BuildSettings (the settings saver keeps them as functions, so a 412 re-applies them on the saved settings), and the
// checks the steps show before the API does (U-13.2 settings_issues: keys, levels, boxes, heights). No React here.
// The rooms milestone (docs/rooms/DESIGN.md R-1.2, R-1.3, R-5.1, R-6.2, R-12.6; R6) adds, at the end: which way a draft
// is built and the switch (setRules), the default ceiling height, the new fixes (closings, rooms, stairs; each matched
// by its own points, never by a list index, so a 412 re-applies it on the right record) and "the floor runs past it".
import type { Vec2 } from '@walkthrough/viewer';
import type {
  Bbox,
  BuildDefaults,
  BuildSettings,
  ClosingFix,
  FloorArea,
  FloorSetup,
  ItemRef,
  LayerRole,
  OpeningFix,
  OutlineEdgeFix,
  ProjectNaming,
  RoomFix,
  SetAside,
  Sha1,
  StairFix,
  Units,
} from '@/upload/contracts';
import { NEW_RULES, OLD_RULES } from '@/upload/contracts';
import type { RulesState } from './testids';

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

/** The furniture reader's smallest-piece limits staff set on the Floors step (U-10.4: `minSize`, m, default 0.08: a
 *  piece whose long side is shorter is left out; `minDepth`, m or null, default null: a piece thinner than it is left
 *  out). After the final check of 9 Nov: no screen had them, so the house built through the screens read 7 thin items
 *  more than its settings (0.25 / 0.25 m) do. The same values again are no change (the saver then sends nothing). */
export const setFurnitureLimits = (patch: Partial<Pick<BuildSettings['furniture'], 'minSize' | 'minDepth'>>): Change => s => {
  const minSize = patch.minSize === undefined ? s.furniture.minSize : patch.minSize;
  const minDepth = patch.minDepth === undefined ? s.furniture.minDepth : patch.minDepth;
  return minSize === s.furniture.minSize && minDepth === s.furniture.minDepth ? s : { ...s, furniture: { ...s.furniture, minSize, minDepth } };
};

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
// (also used by the rooms milestone's fixes at the end of the file)
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

/** The furniture kit's kinds (vendor/furniture_kit.py KINDS, in its legend order). */
export const FURNITURE_KINDS: { kind: string; label: string }[] = [
  { kind: 'atm', label: 'ATM / kiosk' }, { kind: 'computer', label: 'Computer / monitor' }, { kind: 'printer', label: 'Printer / copier' },
  { kind: 'phone', label: 'Telephone' }, { kind: 'tv', label: 'TV / wall screen' }, { kind: 'partition', label: 'Privacy screen / panel' },
  { kind: 'curtain', label: 'Curtain' }, { kind: 'lamp', label: 'Lamp' }, { kind: 'plant', label: 'Plant' },
  { kind: 'sanitary', label: 'Sanitary fitting' }, { kind: 'appliance', label: 'Appliance' }, { kind: 'bed', label: 'Bed' },
  { kind: 'seat', label: 'Chair / stool' }, { kind: 'sofa', label: 'Sofa / armchair' }, { kind: 'seat-back', label: 'Seat back' },
  { kind: 'table', label: 'Table / desk' }, { kind: 'coffee-table', label: 'Coffee / side table' }, { kind: 'bar-table', label: 'Bar table' },
  { kind: 'counter', label: 'Counter top' }, { kind: 'cabinet', label: 'Cabinet / casework' }, { kind: 'tall-cabinet', label: 'Tall cabinet / wardrobe' },
  { kind: 'other', label: 'Other furniture' },
];
const KIND_KEYS = new Set(FURNITURE_KINDS.map(k => k.kind));

/** White space as Python's str.split() sees it (str.isspace), by code point: the builder removes the same set. */
const WHITE = new Set([0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680, 0x2000, 0x2001, 0x2002,
  0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000]);

/** The one form a family name and a family word are compared in, the builder's own (services/builder/walkthrough_builder/
 *  build/furniture.py `family_form`): every run of white space removed, lower case. So 'TF2092P' (a family as its flag
 *  shows it, which is what the Check step saves), 'TF2092 P' (the acceptance settings' way: the furniture kit's
 *  camel-case split) and 'tf2092p' are one family. After the final check of 9 Nov: the builder compared the word as
 *  written with the camel-split name, so a family like TF2092P, A$C238E5230 or SmartTable kept no kind. */
export const familyForm = (name: string): string =>
  Array.from(name).filter(c => !WHITE.has(c.codePointAt(0)!)).join('').toLowerCase();

/** The kind the settings give a family, or '': the first kind in the kit's order (sorted by key, as the builder tries
 *  them) holding a word in the family's form. The select shows this, so it shows the kind the next build gives. */
export function kindOfFamily(s: BuildSettings, family: string): string {
  const form = familyForm(family);
  if (!form) return '';
  for (const kind of Object.keys(s.furniture.words).sort()) {
    if (KIND_KEYS.has(kind) && (s.furniture.words[kind] ?? []).some(w => familyForm(w) === form)) return kind;
  }
  return '';
}

/** A grey furniture family given a kind (U-12.3): settings.furniture.words[kind] gains the family exactly as its flag
 *  shows it, and every word in the family's form leaves every kind (one family, one kind: a word saved before in
 *  another way, e.g. 'TF2092 P', is replaced, not kept beside it). '' (No kind) only takes the family out. */
export const setFurnitureWord = (family: string, kind: string): Change => s => {
  const form = familyForm(family);
  const words: Record<string, string[]> = {};
  for (const [k, list] of Object.entries(s.furniture.words)) {
    const rest = list.filter(w => familyForm(w) !== form);
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
    const c = f.ceilingHeight;
    if (c !== null && c !== undefined && !(c >= MIN_CEILING && c <= MAX_CEILING)) {
      out.push({ path: `${at}/ceilingHeight`, message: `${f.name || f.key}: a ceiling height is 0.5 - 20 m (empty: the default)` });
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

/** The furniture size limits' bounds (U-13.2 settings_issues: 0 - 10 m each; no depth limit is null). */
export const MAX_FURNITURE_LIMIT = 10;

/** What the API would refuse in the furniture size limits (U-13.2), in its words. */
export function furnitureIssues(s: BuildSettings): Issue[] {
  const out: Issue[] = [];
  const { minSize, minDepth } = s.furniture;
  if (!(minSize >= 0 && minSize <= MAX_FURNITURE_LIMIT)) out.push({ path: 'furniture/minSize', message: 'the smallest piece is 0 - 10 m' });
  if (minDepth !== null && !(minDepth >= 0 && minDepth <= MAX_FURNITURE_LIMIT)) out.push({ path: 'furniture/minDepth', message: 'the smallest depth is 0 - 10 m' });
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

// =====================================================================================================================
// The rooms milestone (docs/rooms/DESIGN.md R-1.2, R-1.3, R-5.1, R-6.2, R-6.4, R-12.6)
// =====================================================================================================================

/** The line on the Floors, Build and Check steps (R-12.6), and the checklist's warning line. */
export const RULES_NEW_TEXT = 'Floor plates, ceilings and stairs are built the new way.';
export const RULES_EARLIER_TEXT = 'This draft is built the earlier way: only rooms the walls close get a floor, and stairs stay lines.';
export const USE_NEW_TEXT = 'Use the new floor plates, ceilings and stairs';
/** The API's sentence for the combinations it refuses (R-1.2; R5.md section 1). */
export const RULES_NEED_NETWORK = 'ceilings and climbable stairs need floor plates from the wall network';

/** Which way a draft is built, read from its options (R-12.6: no date, no recipe): the new way when the floor plates
 *  come from the wall network. A missing key is the old rule (R-1.2), so a settings document of before the milestone
 *  reads 'earlier'. */
export const rulesOf = (s: Pick<BuildSettings, 'options'>): RulesState => (s.options.slabs === 'network' ? 'new' : 'earlier');

/** The three options set together, NEW_RULES or OLD_RULES (R-1.3: one saved change). The same rules again: no change. */
export const setRules = (rules: RulesState): Change => s => {
  const want = rules === 'new' ? NEW_RULES : OLD_RULES;
  const o = s.options;
  if (o.slabs === want.slabs && o.ceilings === want.ceilings && o.stairs === want.stairs) return s;
  return { ...s, options: { ...o, slabs: want.slabs, ceilings: want.ceilings, stairs: want.stairs } };
};

/** Ceilings on or off (the fold's second control; only with the new floor plates). */
export const setCeilings = (on: boolean): Change => s => {
  const ceilings = on ? 'auto' as const : 'off' as const;
  return s.options.ceilings === ceilings ? s : { ...s, options: { ...s.options, ceilings } };
};

/** Ceilings are built: the new floor plates and ceilings 'auto'. */
export const ceilingsOn = (s: Pick<BuildSettings, 'options'>): boolean => s.options.slabs === 'network' && s.options.ceilings === 'auto';

/** A typed ceiling height: 0.5 - 20 m (R-12.4); empty is the default rule. */
export const MIN_CEILING = 0.5;
export const MAX_CEILING = 20;

/** The default ceiling height of floor i (R-5.1): min(3.00, wall height - 0.30), never above the underside of the floor
 *  above less 2 cm (next level - level - next slab thickness - 0.02); null when that leaves no ceiling (under 0.5 m). */
export function defaultCeilingHeight(s: Pick<BuildSettings, 'floors' | 'defaults'>, i: number): number | null {
  const f = s.floors[i];
  if (!f || !(f.wallHeight > 0)) return null;
  let h = Math.min(3.0, f.wallHeight - 0.3);
  const next = s.floors[i + 1];
  if (next) h = Math.min(h, next.level - f.level - (next.slabThickness ?? s.defaults.slabThickness) - 0.02);
  h = round3(h);
  return h >= MIN_CEILING ? h : null;
}

export const closingsOf = (s: BuildSettings): ClosingFix[] => s.fixes.closings ?? [];
export const roomFixesOf = (s: BuildSettings): RoomFix[] => s.fixes.rooms ?? [];
export const stairFixesOf = (s: BuildSettings): StairFix[] => s.fixes.stairs ?? [];

/** Sheet points of the new fixes are kept to the millimetre. */
const mm = (p: Vec2): Vec2 => [round3(p[0]), round3(p[1])];
const ROOM_NAME_MAX = 200;
/** A room name as the API takes it (R5.md N-3): one line of plain text, at most 200 characters; blank is no name. */
export function cleanRoomName(name: string | null | undefined): string | null {
  if (name === null || name === undefined) return null;
  const one = Array.from(name).map(c => { const k = c.codePointAt(0)!; return k < 0x20 || (k >= 0x7f && k <= 0x9f) ? ' ' : c; }).join('').trim();
  return one ? Array.from(one).slice(0, ROOM_NAME_MAX).join('') : null;
}

/** A closing line staff drew or asked for (use 'line'), or one of the app's closings left out (use 'none'), R-6.2. The
 *  same segment on the floor again (either order, 5 mm) takes the new use; a segment of no length is no change. */
export const addClosing = (fix: ClosingFix): Change => s => {
  const f: ClosingFix = { floor: fix.floor, a: mm(fix.a), b: mm(fix.b), use: fix.use };
  if (near(f.a, f.b)) return s;
  const list = closingsOf(s);
  const i = list.findIndex(g => sameSegment(g, f));
  if (i >= 0 && list[i]!.use === f.use) return s;
  const closings = i >= 0 ? list.map((g, k) => (k === i ? f : g)) : [...list, f];
  return { ...s, fixes: { ...s.fixes, closings } };
};

/** Takes a closing fix back (Remove in "Fixes on this floor"): the fix of that floor, segment and use. */
export const removeClosing = (fix: ClosingFix): Change => s => {
  const list = closingsOf(s);
  const closings = list.filter(g => !(g.use === fix.use && sameSegment(g, fix)));
  return closings.length === list.length ? s : { ...s, fixes: { ...s.fixes, closings } };
};

const defaultRoom = (f: RoomFix) => f.name === null && f.slab === 'auto' && f.ceiling === 'auto';
const sameRoom = (f: RoomFix, g: RoomFix) => f.floor === g.floor && near(f.at, g.at, 0.0005) && f.name === g.name && f.slab === g.slab && f.ceiling === g.ceiling;

/** A room fix (R-6.2): a name, "no floor here" (slab 'none'), "floor here" ('floor'), "it is outdoors" ('none' on an
 *  area with no room), "no ceiling". It replaces the fix whose point is `was` (the panel's fix of that room; default:
 *  the new fix's own point, 1 mm); a fix that asks for nothing (no name, auto, auto) takes it out ("set back"). */
export const setRoomFix = (fix: RoomFix, was: Vec2 | null = null): Change => s => {
  const f: RoomFix = { floor: fix.floor, at: mm(fix.at), name: cleanRoomName(fix.name), slab: fix.slab, ceiling: fix.ceiling };
  const list = roomFixesOf(s);
  const key = was ?? f.at;
  const i = list.findIndex(g => g.floor === f.floor && near(g.at, key, 0.001));
  if (defaultRoom(f)) return i < 0 ? s : { ...s, fixes: { ...s.fixes, rooms: list.filter((_, k) => k !== i) } };
  if (i >= 0 && sameRoom(list[i]!, f)) return s;
  const rooms = i >= 0 ? list.map((g, k) => (k === i ? f : g)) : [...list, f];
  return { ...s, fixes: { ...s.fixes, rooms } };
};

/** Takes a room fix back (Remove in the list): the fix of that floor and point. */
export const removeRoomFix = (fix: Pick<RoomFix, 'floor' | 'at'>): Change => s => {
  const list = roomFixesOf(s);
  const rooms = list.filter(g => !(g.floor === fix.floor && near(g.at, fix.at, 0.001)));
  return rooms.length === list.length ? s : { ...s, fixes: { ...s.fixes, rooms } };
};

const defaultStair = (f: StairFix) => f.bottom === null && f.use === 'auto';
const sameStair = (f: StairFix, g: StairFix) => f.floor === g.floor && near(f.at, g.at, 0.0005) && f.use === g.use
  && (f.bottom === null ? g.bottom === null : g.bottom !== null && near(f.bottom, g.bottom, 0.0005));

/** A stair fix (R-6.2, R-7.6): its bottom (a point on the bottom tread), keep as lines, climb it as drawn. It replaces
 *  the fix whose point is `was` (default: its own point); bottom null with use 'auto' takes it out ("Decide
 *  automatically"). */
export const setStairFix = (fix: StairFix, was: Vec2 | null = null): Change => s => {
  const f: StairFix = { floor: fix.floor, at: mm(fix.at), bottom: fix.bottom ? mm(fix.bottom) : null, use: fix.use };
  const list = stairFixesOf(s);
  const key = was ?? f.at;
  const i = list.findIndex(g => g.floor === f.floor && near(g.at, key, 0.001));
  if (defaultStair(f)) return i < 0 ? s : { ...s, fixes: { ...s.fixes, stairs: list.filter((_, k) => k !== i) } };
  if (i >= 0 && sameStair(list[i]!, f)) return s;
  const stairs = i >= 0 ? list.map((g, k) => (k === i ? f : g)) : [...list, f];
  return { ...s, fixes: { ...s.fixes, stairs } };
};

export const removeStairFix = (fix: Pick<StairFix, 'floor' | 'at'>): Change => s => {
  const list = stairFixesOf(s);
  const stairs = list.filter(g => !(g.floor === fix.floor && near(g.at, fix.at, 0.001)));
  return stairs.length === list.length ? s : { ...s, fixes: { ...s.fixes, stairs } };
};

/** The set-aside tick "The floor runs past it" (R-2.1 point 7; SetAside.floorPast, default false: written only when
 *  true). The same value again: no change. */
export const setFloorPast = (floor: string, key: string, on: boolean): Change => s => {
  let changed = false;
  const setAside = s.fixes.setAside.map(r => {
    if (r.floor !== floor || r.key !== key || !!r.floorPast === on) return r;
    changed = true;
    const next: SetAside = { ...r };
    if (on) next.floorPast = true; else delete next.floorPast;
    return next;
  });
  return changed ? { ...s, fixes: { ...s.fixes, setAside } } : s;
};

/** The cap of "other fixes" (U-13.2), which counts the new lists too (R-12.4). */
export const MAX_OTHER_FIXES = 5000;
export const otherFixCount = (s: BuildSettings): number =>
  s.fixes.openings.length + s.fixes.outlineEdges.length + closingsOf(s).length + roomFixesOf(s).length + stairFixesOf(s).length;

/** What the API's settings_issues would refuse of the rooms milestone's settings (R-1.2, R-12.4; R5.md section 1): the
 *  old floor plates with ceilings or climbable stairs, the fix cap, a room name that is not one line of 200 characters.
 *  (The ceiling heights are floorIssues'.) */
export function roomsIssues(s: BuildSettings): Issue[] {
  const out: Issue[] = [];
  const o = s.options;
  if ((o.slabs ?? 'closed-rooms') === 'closed-rooms') {
    if (o.ceilings === 'auto') out.push({ path: 'options/ceilings', message: `${RULES_NEED_NETWORK}: turn the ceilings off, or build the new way` });
    if (o.stairs === 'climb') out.push({ path: 'options/stairs', message: `${RULES_NEED_NETWORK}: keep the stairs as lines, or build the new way` });
  }
  const n = otherFixCount(s);
  if (n > MAX_OTHER_FIXES) out.push({ path: 'fixes', message: `at most 5,000 fixes besides the set-asides (there are ${n})` });
  roomFixesOf(s).forEach((r, i) => {
    if (r.name !== null && r.name !== cleanRoomName(r.name)) out.push({ path: `fixes/rooms/${i}/name`, message: 'a room name is one line of at most 200 characters' });
  });
  return out;
}

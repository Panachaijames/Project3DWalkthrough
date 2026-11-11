// parseBuiltModel / parseReplayData (DESIGN.md 5.6, 7): hand-written checks, no validator library at run time (ajv compiles
// its validators with `new Function`, which a strict Content-Security-Policy forbids; ajv is a test-only dependency).
// Owner: builder A.
//
// parseBuiltModel mirrors app/docs/built-model.schema.json rule for rule (structure, types, enums, patterns, the closed
// objects), then the cross-reference rules of 5.6 and, for BuiltModel v2, of rooms/DESIGN.md R-12.1 (written by the rooms
// scaffold R0 together with the schema and the API's builtmodel.py: the three checkers change together). Issue paths are
// JSON Pointers, as ajv and the API's jsonschema give them:
// a wrong value at its own path (/parts/3/z1), a missing or extra property at its parent object (/floors/1), a duplicate at
// its later occurrence (/openings/5/id). Any schema issue, and any cross-reference issue outside the furniture, throws a
// ModelError listing every issue. The furniture rules (kind in furnitureKinds, `on` names a piece, approach ids are opening
// ids, the kinds' counts; and, as furniture_boxes.js was just as lenient, a piece's floor and unique piece ids) only warn,
// one console.warn('[viewer] model: <path>: <message>') each: the furniture code then does what furniture_boxes.js did.
import type {
  BuiltModel, ModelErrorLike, ModelIssue, ParseBuiltModel, ParseReplayData, ReplayData, StepKey,
} from '../contracts';

/** Thrown when a model does not parse; `issues` carry JSON Pointer paths (/parts/12/z1). */
export class ModelError extends Error implements ModelErrorLike {
  readonly issues: ModelIssue[];

  constructor(issues: ModelIssue[], message?: string) {
    super(message ?? `[viewer] model: ${issues.length} issue(s)` +
      (issues.length ? `: ${issues.slice(0, 3).map(i => `${i.path}: ${i.message}`).join('; ')}` : ''));
    this.name = 'ModelError';
    this.issues = issues;
  }
}

// ------------------------------------------------------------------------------------------------------------- helpers
type Json = unknown;
type Obj = Record<string, unknown>;
type Check = (v: Json, path: string, out: ModelIssue[]) => void;

/** JSON Pointer of a child (RFC 6901 escaping). */
export const ptr = (base: string, key: string | number): string =>
  `${base}/${String(key).replace(/~/g, '~0').replace(/\//g, '~1')}`;

const isObj = (v: Json): v is Obj => v !== null && typeof v === 'object' && !Array.isArray(v);
const isNum = (v: Json): v is number => typeof v === 'number' && Number.isFinite(v);
const isInt = (v: Json): v is number => isNum(v) && Number.isInteger(v);
const isStr = (v: Json): v is string => typeof v === 'string';
const issue = (out: ModelIssue[], path: string, message: string) => { out.push({ path, message }); };

const num: Check = (v, p, out) => { if (!isNum(v)) issue(out, p, 'must be number'); };
const int: Check = (v, p, out) => { if (!isInt(v)) issue(out, p, 'must be integer'); };
const str: Check = (v, p, out) => { if (!isStr(v)) issue(out, p, 'must be string'); };
const bool: Check = (v, p, out) => { if (typeof v !== 'boolean') issue(out, p, 'must be boolean'); };
const nonEmpty: Check = (v, p, out) => {
  if (!isStr(v)) issue(out, p, 'must be string');
  else if (v.length < 1) issue(out, p, 'must NOT have fewer than 1 characters');
};
const strOrNull: Check = (v, p, out) => { if (v !== null && !isStr(v)) issue(out, p, 'must be string,null'); };
const numOrNull: Check = (v, p, out) => { if (v !== null && !isNum(v)) issue(out, p, 'must be number,null'); };
const positive: Check = (v, p, out) => {
  if (!isNum(v)) issue(out, p, 'must be number');
  else if (!(v > 0)) issue(out, p, 'must be > 0');
};
const pattern = (re: RegExp): Check => (v, p, out) => {
  if (!isStr(v)) issue(out, p, 'must be string');
  else if (!re.test(v)) issue(out, p, `must match pattern "${re.source}"`);
};
const oneOf = (values: readonly unknown[]): Check => (v, p, out) => {
  if (!values.includes(v)) issue(out, p, 'must be equal to one of the allowed values');
};
const arrayOf = (item: Check, minItems = 0): Check => (v, p, out) => {
  if (!Array.isArray(v)) { issue(out, p, 'must be array'); return; }
  if (v.length < minItems) issue(out, p, `must NOT have fewer than ${minItems} items`);
  v.forEach((x, i) => item(x, ptr(p, i), out));
};
/** prefixItems + items: false + minItems n: exactly n items, each checked. */
const tuple = (...items: Check[]): Check => (v, p, out) => {
  if (!Array.isArray(v)) { issue(out, p, 'must be array'); return; }
  if (v.length < items.length) issue(out, p, `must NOT have fewer than ${items.length} items`);
  else if (v.length > items.length) issue(out, p, `must NOT have more than ${items.length} items`);
  items.forEach((check, i) => { if (i < v.length) check(v[i], ptr(p, i), out); });
};
interface ObjectSpec { required?: string[]; props: Record<string, Check>; closed?: boolean }
const object = (spec: ObjectSpec): Check => (v, p, out) => {
  if (!isObj(v)) { issue(out, p, 'must be object'); return; }
  for (const key of spec.required ?? []) if (!(key in v)) issue(out, p, `must have required property '${key}'`);
  if (spec.closed) for (const key of Object.keys(v)) if (!(key in spec.props)) issue(out, p, `must NOT have additional property '${key}'`);
  for (const [key, check] of Object.entries(spec.props)) if (key in v) check(v[key], ptr(p, key), out);
};
/** An object keyed by floor key (perFloor / pictureFrame): property names checked, each value checked. */
const perFloor = (value: Check): Check => (v, p, out) => {
  if (!isObj(v)) { issue(out, p, 'must be object'); return; }
  for (const [key, x] of Object.entries(v)) {
    if (!FLOOR_KEY.test(key)) issue(out, p, `property name '${key}' must match pattern "${FLOOR_KEY.source}"`);
    value(x, ptr(p, key), out);
  }
};

// ------------------------------------------------------------------------------------------------- the schema ($defs)
export const FLOOR_KEY = /^[A-Za-z0-9_]{1,32}$/;
export const PART_KINDS = ['wall', 'column', 'lintel', 'sill', 'parapet', 'glass', 'pane', 'mullion', 'railing', 'balustrade',
  'single', 'step', 'low', 'builtin', 'deck', 'post', 'slab', 'tread', 'landing', 'ceiling'] as const;

const floorKey = pattern(FLOOR_KEY);
const vec2 = tuple(num, num);
const ring = arrayOf(vec2, 3);
const rings = arrayOf(ring);
const colour = pattern(/^#[0-9a-fA-F]{6}$/);
const flatSegments = arrayOf(num);
const side = oneOf([1, -1]);

const floor = object({
  closed: true,
  required: ['key', 'name', 'level', 'wallHeight', 'slabThickness'],
  props: {
    key: floorKey, name: nonEmpty, level: num, wallHeight: positive,
    slabThickness: (v, p, out) => { if (!isNum(v)) issue(out, p, 'must be number'); else if (v < 0) issue(out, p, 'must be >= 0'); },
    stack: nonEmpty, sheetShift: vec2,
  },
});
const part = object({
  closed: true,
  required: ['floor', 'kind', 'z0', 'z1', 'follow', 'o', 'h'],
  props: {
    floor: floorKey, kind: oneOf(PART_KINDS), z0: num, z1: num, follow: bool, o: ring, h: rings, label: str,
    fit: oneOf(['top', 'clip', 'storey']), plinth: bool, stair: nonEmpty,
  },
});
const stairLines = object({ closed: true, required: ['below', 'above'], props: { below: flatSegments, above: flatSegments, panels: flatSegments } });
const voidMark = object({ required: ['what', 'x', 'y', 'area'], props: { what: str, x: num, y: num, area: num } });
const closure = object({ required: ['object', 'width', 'x', 'y'], props: { object: str, width: num, x: num, y: num } });
const nonNegInt: Check = (v, p, out) => { if (!isInt(v)) issue(out, p, 'must be integer'); else if (v < 0) issue(out, p, 'must be >= 0'); };
const stairOutline = object({
  required: ['x', 'y', 'bbox', 'flights', 'withWord'],
  props: { id: str, x: num, y: num, bbox: tuple(num, num, num, num), flights: nonNegInt, withWord: nonNegInt },
});
const room = object({
  required: ['floor', 'name', 'label', 'area', 'x', 'y'],
  props: { floor: floorKey, name: str, label: str, area: numOrNull, x: num, y: num, callout: bool, space: nonEmpty },
});
const intAtLeast = (min: number): Check => (v, p, out) => { if (!isInt(v)) issue(out, p, 'must be integer'); else if (v < min) issue(out, p, `must be >= ${min}`); };
// BuiltModel v2 (rooms/DESIGN.md R-8.5, R-3.4): open objects, as the openings are
const stairway = object({
  required: ['id', 'from', 'to', 'kind', 'risers', 'riser', 'going', 'width', 'bottom', 'top', 'walk', 'direction', 'treads', 'landings'],
  props: {
    id: nonEmpty, from: floorKey, to: floorKey, kind: str, risers: intAtLeast(2), riser: positive, going: positive, width: positive,
    bottom: vec2, top: vec2, walk: arrayOf(vec2, 2), direction: str, treads: intAtLeast(1), landings: intAtLeast(0),
  },
});
const space = object({
  required: ['id', 'floor', 'o', 'h', 'area', 'name', 'names', 'source', 'ceiling'],
  props: {
    id: nonEmpty, floor: floorKey, o: ring, h: rings,
    area: (v, p, out) => { if (!isNum(v)) issue(out, p, 'must be number'); else if (v < 0) issue(out, p, 'must be >= 0'); },
    name: str, names: arrayOf(str), source: oneOf(['network', 'outline', 'staff']), ceiling: bool,
  },
});
const opening = object({
  required: ['id', 'floor', 'kind', 'x', 'y', 'nx', 'ny', 'width'],
  props: {
    id: nonEmpty, floor: floorKey, kind: oneOf(['door', 'window', 'passage']), subtype: str, label: str,
    x: num, y: num, nx: num, ny: num, width: positive, wallThickness: num, exterior: bool, inside: arrayOf(side),
    sill: num, head: num, lintel: oneOf(['lintel', 'transom', null]), lintelTop: num, eitherKind: bool,
  },
});
const probe = object({
  required: ['floor', 'id', 'what', 'x', 'y', 'nx', 'ny', 'inside'],
  props: { floor: floorKey, id: str, what: str, x: num, y: num, nx: num, ny: num, inside: arrayOf(side, 1), top: num, label: strOrNull },
});
const skin = object({ closed: true, required: ['o', 'h', 'z0', 'z1', 'glass'], props: { o: ring, h: rings, z0: num, z1: num, glass: bool } });
const posInt: Check = (v, p, out) => { if (!isInt(v)) issue(out, p, 'must be integer'); else if (v < 1) issue(out, p, 'must be >= 1'); };
const pictureFrame = object({
  closed: true,
  required: ['file', 'size', 'pxPerMetreX', 'pxPerMetreY', 'originPx', 'yDown'],
  props: {
    file: str, size: tuple(posInt, posInt), pxPerMetreX: positive, pxPerMetreY: positive, originPx: vec2,
    yDown: (v, p, out) => { if (v !== true) issue(out, p, 'must be equal to constant'); }, _: str,
  },
});
const furnitureKind = object({
  closed: true,
  required: ['key', 'label', 'colour', 'height', 'base', 'onTop', 'support', 'blocks', 'count'],
  props: {
    key: (v, p, out) => {
      pattern(/^[a-z][a-z0-9-]{0,31}$/)(v, p, out);
      if (v === 'none') issue(out, p, 'must NOT be valid');
    },
    label: nonEmpty, colour, height: posInt, base: nonNegInt, onTop: bool, support: bool, blocks: bool, count: nonNegInt,
  },
});
const furniturePiece = object({
  closed: true,
  required: ['id', 'floor', 'kind', 'family', 'block', 'layer', 'handle', 'x', 'y', 'w', 'd', 'rot', 'on', 'approach', 'n', 'note'],
  props: {
    id: nonEmpty, floor: floorKey, kind: str, family: str, block: str, layer: str, handle: str, x: num, y: num,
    w: positive, d: positive,
    rot: (v, p, out) => {
      if (!isNum(v)) issue(out, p, 'must be number');
      else if (v < 0) issue(out, p, 'must be >= 0');
      else if (!(v < 180)) issue(out, p, 'must be < 180');
    },
    on: strOrNull, approach: arrayOf(str), n: posInt, note: str,
  },
});

const ROOT_REQUIRED = ['project', 'shortName', 'source', 'units', 'offset', 'photoName', 'maxPrefix', 'floors', 'railingHeight',
  'singleLineHeight', 'doorHeadDefault', 'parts', 'stairs', 'voids', 'closures', 'stairOutlines', 'rooms', 'openings', 'probes',
  'colliderSkins'];
const builtModel = object({
  closed: true,
  required: ROOT_REQUIRED,
  props: {
    project: nonEmpty, shortName: nonEmpty, projectNo: strOrNull, source: arrayOf(str),
    units: (v, p, out) => { if (v !== 'm') issue(out, p, 'must be equal to constant'); },
    offset: vec2, photoName: pattern(/^[A-Za-z0-9_.-]{1,64}$/), maxPrefix: pattern(/^[A-Z]{2,4}$/),
    floors: arrayOf(floor, 1), railingHeight: positive, singleLineHeight: positive, doorHeadDefault: positive,
    pictureFrame: perFloor(pictureFrame), parts: arrayOf(part), stairs: perFloor(stairLines), voids: perFloor(arrayOf(voidMark)),
    closures: perFloor(arrayOf(closure)), stairOutlines: perFloor(arrayOf(stairOutline)), rooms: arrayOf(room),
    openings: arrayOf(opening), probes: arrayOf(probe), colliderSkins: perFloor(arrayOf(skin)),
    furnitureKinds: arrayOf(furnitureKind), furniture: arrayOf(furniturePiece),
    stairways: arrayOf(stairway), spaces: arrayOf(space),
  },
});

/** The schema checks alone (exported for tests): every issue, JSON Pointer paths. */
export function schemaIssues(json: unknown): ModelIssue[] {
  const out: ModelIssue[] = [];
  builtModel(json, '', out);
  if (isObj(json) && 'furniture' in json && !('furnitureKinds' in json)) {
    issue(out, '', "must have property furnitureKinds when property furniture is present");
  }
  return out;
}

// ------------------------------------------------------------------------------------------ cross-reference rules (5.6)
/** The cross-reference rules of 5.6 on a schema-valid model: `strict` issues throw, `furniture` issues only warn. */
export function crossIssues(m: BuiltModel): { strict: ModelIssue[]; furniture: ModelIssue[] } {
  const strict: ModelIssue[] = [], furniture: ModelIssue[] = [];
  const keys = m.floors.map(f => f.key), known = new Set(keys);
  keys.forEach((k, i) => { if (keys.indexOf(k) !== i) issue(strict, `/floors/${i}/key`, `duplicate floor key '${k}'`); });
  m.floors.forEach((f, i) => {
    const before = m.floors[i - 1];
    if (before && f.level < before.level) issue(strict, `/floors/${i}/level`, `floors must be in level order (${f.level} is below ${before.level})`);
  });
  m.parts.forEach((p, i) => {
    if (!known.has(p.floor)) issue(strict, `/parts/${i}/floor`, `no floor '${p.floor}'`);
    if (!(p.z1 > p.z0)) issue(strict, `/parts/${i}/z1`, `z1 (${p.z1}) must be above z0 (${p.z0})`);
    if (p.plinth && p.kind !== 'slab') issue(strict, `/parts/${i}/plinth`, `plinth only on slabs (this is a ${p.kind})`);
  });
  for (const name of ['stairs', 'voids', 'closures', 'stairOutlines', 'colliderSkins', 'pictureFrame'] as const) {
    for (const k of Object.keys(m[name] ?? {})) if (!known.has(k)) issue(strict, ptr(`/${name}`, k), `no floor '${k}'`);
  }
  for (const [k, s] of Object.entries(m.stairs)) {
    for (const a of ['below', 'above', 'panels'] as const) {
      const list = s[a];
      if (list && list.length % 4) issue(strict, ptr(ptr('/stairs', k), a), `${list.length} numbers: not a multiple of 4 (x1, y1, x2, y2 per line)`);
    }
  }
  for (const coll of ['rooms', 'openings', 'probes'] as const) {
    m[coll].forEach((x, i) => { if (!known.has(x.floor)) issue(strict, `/${coll}/${i}/floor`, `no floor '${x.floor}'`); });
  }
  const ids = m.openings.map(o => o.id), openingIds = new Set(ids);
  ids.forEach((id, i) => { if (ids.indexOf(id) !== i) issue(strict, `/openings/${i}/id`, `duplicate opening id '${id}'`); });

  // BuiltModel v2 (rooms/DESIGN.md R-12.1): stairways rise within one stack; a part's `stair` names a stairway and the part
  // lies on that stairway's `from` floor; every tread and landing has one; stairway and space ids are unique; a drawn name's
  // `space` names a space of its own floor. (`walk` has at least 2 points: the schema.)
  const stackOf = new Map(m.floors.map(f => [f.key, f.stack ?? 'main'])), levelOf = new Map(m.floors.map(f => [f.key, f.level]));
  const stairFrom = new Map<string, string>();
  (m.stairways ?? []).forEach((s, i) => {
    if (stairFrom.has(s.id)) issue(strict, `/stairways/${i}/id`, `duplicate stairway id '${s.id}'`);
    else stairFrom.set(s.id, s.from);
    if (!known.has(s.from)) issue(strict, `/stairways/${i}/from`, `no floor '${s.from}'`);
    if (!known.has(s.to)) issue(strict, `/stairways/${i}/to`, `no floor '${s.to}'`);
    else if (known.has(s.from)) {
      if (stackOf.get(s.to) !== stackOf.get(s.from)) issue(strict, `/stairways/${i}/to`, `'${s.to}' is not in the stack of '${s.from}'`);
      else if (!(levelOf.get(s.to)! > levelOf.get(s.from)!)) issue(strict, `/stairways/${i}/to`, `'${s.to}' is not above '${s.from}'`);
    }
  });
  m.parts.forEach((p, i) => {
    if (p.stair === undefined) {
      if (p.kind === 'tread' || p.kind === 'landing') issue(strict, `/parts/${i}`, `a ${p.kind} must name its stairway (stair)`);
      return;
    }
    const from = stairFrom.get(p.stair);
    if (from === undefined) issue(strict, `/parts/${i}/stair`, `no stairway '${p.stair}'`);
    else if (from !== p.floor) issue(strict, `/parts/${i}/stair`, `stairway '${p.stair}' rises from '${from}', but the part is on '${p.floor}'`);
  });
  const spaceFloor = new Map<string, string>();
  (m.spaces ?? []).forEach((s, i) => {
    if (!known.has(s.floor)) issue(strict, `/spaces/${i}/floor`, `no floor '${s.floor}'`);
    if (spaceFloor.has(s.id)) issue(strict, `/spaces/${i}/id`, `duplicate space id '${s.id}'`);
    else spaceFloor.set(s.id, s.floor);
  });
  m.rooms.forEach((r, i) => {
    if (r.space === undefined) return;
    const on = spaceFloor.get(r.space);
    if (on === undefined) issue(strict, `/rooms/${i}/space`, `no space '${r.space}'`);
    else if (on !== r.floor) issue(strict, `/rooms/${i}/space`, `space '${r.space}' is on '${on}', but the name is on '${r.floor}'`);
  });

  if (m.furniture) {
    const kinds = new Set((m.furnitureKinds ?? []).map(k => k.key));
    const pieceIds = m.furniture.map(p => p.id), pieceSet = new Set(pieceIds);
    pieceIds.forEach((id, i) => { if (pieceIds.indexOf(id) !== i) issue(furniture, `/furniture/${i}/id`, `duplicate furniture id '${id}'`); });
    m.furniture.forEach((p, i) => {
      if (!kinds.has(p.kind)) issue(furniture, `/furniture/${i}/kind`, `kind '${p.kind}' is not in furnitureKinds`);
      if (!known.has(p.floor)) issue(furniture, `/furniture/${i}/floor`, `no floor '${p.floor}'`);
      if (p.on !== null && !pieceSet.has(p.on)) issue(furniture, `/furniture/${i}/on`, `'${p.on}' names no piece`);
      p.approach.forEach((a, j) => { if (!openingIds.has(a)) issue(furniture, `/furniture/${i}/approach/${j}`, `'${a}' names no opening`); });
    });
    const count: Record<string, number> = {};
    for (const p of m.furniture) count[p.kind] = (count[p.kind] ?? 0) + 1;
    (m.furnitureKinds ?? []).forEach((k, i) => {
      if ((count[k.key] ?? 0) !== k.count) issue(furniture, `/furnitureKinds/${i}/count`, `count ${k.count}, but ${count[k.key] ?? 0} pieces`);
    });
  }
  return { strict, furniture };
}

export const parseBuiltModel: ParseBuiltModel = json => {
  const schema = schemaIssues(json);
  if (schema.length) throw new ModelError(schema);
  const model = json as BuiltModel;
  const { strict, furniture } = crossIssues(model);
  if (strict.length) throw new ModelError([...strict, ...furniture]);
  for (const w of furniture) console.warn(`[viewer] model: ${w.path}: ${w.message}`);
  return model;
};

// ------------------------------------------------------------------------------------------------ ReplayData v1 (7.1)
export const STEP_KEYS: readonly StepKey[] = ['read', 'sort', 'align', 'pair', 'merge', 'raise', 'finish'];

const multipleOf = (n: number, what: string): Check => (v, p, out) => {
  arrayOf(num)(v, p, out);
  if (Array.isArray(v) && v.length % n) issue(out, p, `${v.length} numbers: not a multiple of ${n} (${what})`);
};
const replayRing = object({ required: ['o', 'h'], props: { o: ring, h: rings } });
const recordOf = (value: Check): Check => (v, p, out) => {
  if (!isObj(v)) { issue(out, p, 'must be object'); return; }
  for (const [key, x] of Object.entries(v)) value(x, ptr(p, key), out);
};
const replayFloor = object({
  required: ['sheet', 'lines', 'pieces', 'rings'],
  props: {
    sheet: vec2,
    lines: recordOf(multipleOf(4, 'x1, y1, x2, y2 per line')),
    pieces: recordOf(multipleOf(8, 'x0, y0 ... x3, y3 per piece')),
    rings: recordOf(arrayOf(replayRing)),
  },
});
const stepTexts = (required: boolean): Check => (v, p, out) => {
  if (!isObj(v)) { issue(out, p, 'must be object'); return; }
  for (const k of STEP_KEYS) {
    if (k in v) str(v[k], ptr(p, k), out);
    else if (required) issue(out, p, `must have required property '${k}'`);
  }
};
const replayData = object({
  required: ['source', 'intro', 'layers', 'floors', 'captions'],
  props: {
    source: (v, p, out) => { if (!isObj(v)) issue(out, p, 'must be object'); },
    panelIntro: str,
    intro: arrayOf(str),
    layers: arrayOf(tuple(str, str)),
    floors: perFloor(replayFloor),
    captions: stepTexts(true),
    stats: (v, p, out) => { if (!isObj(v)) issue(out, p, 'must be object'); },
    introTitle: str,
    layersTitle: str,
    stepTitles: stepTexts(false),
    colors: recordOf(colour),
  },
});

/** The replay data checks (exported for tests): its own structure, then one entry per model floor and no other. */
export function replayIssues(json: unknown, model: BuiltModel): ModelIssue[] {
  const out: ModelIssue[] = [];
  replayData(json, '', out);
  if (out.length || !isObj(json)) return out;
  const floors = json.floors as Obj;
  const known = new Set(model.floors.map(f => f.key));
  for (const f of model.floors) if (!(f.key in floors)) issue(out, '/floors', `must have the model's floor '${f.key}'`);
  for (const k of Object.keys(floors)) if (!known.has(k)) issue(out, ptr('/floors', k), `the model has no floor '${k}'`);
  return out;
}

export const parseReplayData: ParseReplayData = (json, model) => {
  const issues = replayIssues(json, model);
  if (issues.length) throw new ModelError(issues, `[viewer] replay data: ${issues.length} issue(s): ` +
    issues.slice(0, 3).map(i => `${i.path}: ${i.message}`).join('; '));
  return json as ReplayData;
};

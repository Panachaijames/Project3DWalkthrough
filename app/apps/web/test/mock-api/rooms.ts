// The mock API's rooms milestone (docs/rooms/DESIGN.md R-1.3, R-6, R-12.4, R-12.6; WORK_BREAKDOWN R6 "the mock API's new
// overlay"): the reference building (fixtures/rooms; ACCEPTANCE 2.5) as two DXF sources the mock knows by their sha1
// (settings.reference.json) or by their names (rooms-reference-ground.dxf / -upper.dxf): a plan drawn from the frozen
// overlay's own outlines, a drawing read and layer suggestions to match, the reference settings as the proposal, and the
// frozen overlay (fixtures/rooms/overlay.reference.json) as every build's overlay, with the fixes of the build's
// settings applied the simple way (a staff line is drawn, a removed closing goes, a name, "no ceiling", "no floor here",
// "it is outdoors", "floor here", a stair kept as lines or climbed from its picked bottom; their flags go). The mock
// never builds: this is enough for the screens to show "waiting for Rebuild" and then the result. Node only.
import path from 'node:path';
import type { Vec2 } from '../../../../packages/viewer/src/contracts';
import type * as C from '../../src/upload/contracts';
import { flat, insidePoint, polyContains, ringContains } from '../../src/plan/geom';
import { FIXTURES_DIR, readJson } from './fixtures';

export const ROOMS_FILES = {
  overlay: path.join(FIXTURES_DIR, 'rooms', 'overlay.reference.json'),
  settings: path.join(FIXTURES_DIR, 'rooms', 'settings.reference.json'),
  flags: path.join(FIXTURES_DIR, 'rooms', 'flags.every-kind.json'),
  houseOverlay: path.join(FIXTURES_DIR, 'upload', 'overlay', 'house-rooms.overlay.json'),
};

const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
export const referenceOverlay = () => clone(readJson(ROOMS_FILES.overlay) as C.BuildOverlay);
export const referenceSettings = () => clone(readJson(ROOMS_FILES.settings) as C.BuildSettings);

/** The reference building's floor (0 ground, 1 upper) a source is, or -1: by the fixture's sha1, else by its name. */
export function referenceFloorOf(src: { sha1: string; name: string }): number {
  const s = referenceSettings();
  const i = s.sources.findIndex(x => x.sha1 === src.sha1);
  if (i >= 0) return i;
  const m = /rooms-reference-(ground|upper)\.dxf$/i.exec(src.name);
  return m ? (m[1]!.toLowerCase() === 'ground' ? 0 : 1) : -1;
}

const LAYER_OF: Record<string, string> = {
  wall: 'A-WALL', column: 'A-WALL', lintel: 'A-WALL', sill: 'A-WALL', parapet: 'A-WALL', glass: 'A-GLAZ', pane: 'A-GLAZ',
  railing: 'A-FLOR-HRAL', balustrade: 'A-FLOR-HRAL', tread: 'S-STRS', landing: 'S-STRS', step: 'S-STRS',
};
const LAYERS = ['A-WALL', 'A-DOOR', 'A-AREA-IDEN', 'A-FLOR-HRAL', 'S-STRS', 'A-GLAZ', '0'];

/** 12 hex of a string (a stand-in signature: the mock never re-matches). */
function hex12(s: string): string {
  let h1 = 0x811c9dc5, h2 = 0x01000193;
  for (let i = 0; i < s.length; i++) {
    h1 = Math.imul(h1 ^ s.charCodeAt(i), 16777619) >>> 0;
    h2 = Math.imul(h2 + s.charCodeAt(i), 2246822519) >>> 0;
  }
  return (h1.toString(16).padStart(8, '0') + h2.toString(16).padStart(8, '0')).slice(0, 12);
}

/** The plan of a reference floor: its parts' outlines, the stair outlines, the doors and the room names, in the frozen
 *  overlay's own sheet metres (origin [0, 0], 1 cm). */
export function referencePlan(source: C.Sha1, floor: number): C.PlanGeometry {
  const of = referenceOverlay().floors[floor]!;
  const items: C.PlanGeometry['items'] = { key: [], layer: [], type: [], first: [], count: [], sig: [], rsig: [], eid: [] };
  const pts: number[] = [];
  let n = 0;
  const add = (layer: string, type: number, ps: Vec2[]) => {
    const key = (0x100 + n++).toString(16).toUpperCase();
    items.key.push(key); items.layer.push(LAYERS.indexOf(layer)); items.type.push(type); items.first.push(pts.length / 2);
    items.count.push(ps.length); items.sig.push(hex12(`${floor}:${key}`)); items.rsig.push(''); items.eid.push(-1);
    for (const [x, y] of ps) pts.push(Math.round(x * 100), Math.round(y * 100));
  };
  for (const p of of.parts) if (LAYER_OF[p.kind] && p.o.length >= 3) add(LAYER_OF[p.kind]!, 1, p.o);
  for (const s of of.stairs ?? []) if (s.outline.length >= 3) add('S-STRS', 1, s.outline);
  for (const o of of.openings) add('A-DOOR', 0, [o.a, o.b]);
  for (const r of of.rooms) add('A-AREA-IDEN', 4, [[r.x, r.y]]);
  return { format: 'plan-geometry/1', source, units: 'mm', origin: [0, 0], quantum: 0.01, layers: LAYERS.slice(), items, elementIds: [], pts };
}

/** A drawing read that matches the reference plan (layers with their item counts; no level tags, one area). */
export function referenceDrawing(source: { sha1: C.Sha1; name: string }, plan: C.PlanGeometry): C.DrawingRead {
  const xs = plan.pts.filter((_, i) => i % 2 === 0).map(v => v / 100), ys = plan.pts.filter((_, i) => i % 2 === 1).map(v => v / 100);
  const ext: C.Bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  const layer = (name: string, li: number): C.LayerRead => {
    const mine = plan.items.layer.map((l, i) => (l === li ? i : -1)).filter(i => i >= 0);
    const texts = mine.filter(i => plan.items.type[i] === 4).length;
    return {
      name, normalised: name, state: { on: true, frozen: false, locked: false, plot: true }, linetype: 'Continuous', colour: 7,
      items: mine.length, byType: { LWPOLYLINE: mine.length - texts, ...(texts ? { TEXT: texts } : {}) }, inBlocks: 0,
      closedShapes: mine.filter(i => plan.items.type[i] === 1).length, solidHatches: 0, hatchPatterns: {}, length: mine.length * 3,
      doorArcs: 0, doorArcsWithLeaf: 0, texts, inserts: 0, topBlocks: [], linetypes: {}, pairs: { glassLike: 0, wallLike: 0 },
      extents: mine.length ? ext : null,
    };
  };
  return {
    format: 'drawing-read/1', source: { sha1: source.sha1, name: source.name }, reader: { version: 'mock', seconds: 0.1, peakMemoryMB: null },
    dxf: { acadVersion: 'AC1032', insUnits: 4, auditErrors: 0, auditFixes: 0 },
    units: { declared: 'mm', votes: { mm: 3, cm: 0, m: 0, in: 0, ft: 0 }, dimensionMedian: null, used: 'mm', verdict: 'agree', note: '' },
    extents: ext,
    counts: { items: plan.items.key.length, byType: { LWPOLYLINE: plan.items.key.length }, dimensions: 0 },
    layers: plan.layers.map(layer),
    blocks: [],
    texts: [],
    levelTags: [],
    gridLabels: [],
    areas: [{ id: 'a1', bbox: [ext[0] - 1, ext[1] - 1, ext[2] + 1, ext[3] + 1], items: plan.items.key.length, wallItems: 4, looks: 'plan' }],
  };
}

/** Suggestions for the reference layers: the reference settings' roles, "by name". */
export function referenceSuggestions(): Record<string, C.LayerSuggestion> {
  const roles = referenceSettings().layers;
  const out: Record<string, C.LayerSuggestion> = {};
  for (const n of LAYERS) {
    const role = roles[n] ?? 'other';
    out[n] = { role, from: role === 'other' ? 'default' : 'name', evidence: [`named like a ${role} layer: ${n}`] };
  }
  return out;
}

// ------------------------------------------------------------------------------------------------- the overlay
const dist = (a: Vec2, b: Vec2) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const sameEnds = (a: Vec2, b: Vec2, c: Vec2, d: Vec2, tol: number) =>
  (dist(a, c) <= tol && dist(b, d) <= tol) || (dist(a, d) <= tol && dist(b, c) <= tol);

/** The reference overlay for a build of the reference building: floors and sources re-keyed to the settings', the
 *  fixes of the settings applied the simple way (see the top of the file). */
export function roomsOverlayFor(settings: C.BuildSettings, sourceFloor: (sha1: string) => number): C.BuildOverlay {
  const ref = referenceOverlay();
  const floors: C.OverlayFloor[] = [];
  const keyMap = new Map<string, string>();
  for (const f of settings.floors) {
    const i = sourceFloor(f.source);
    const of = ref.floors[i];
    if (!of) continue;
    keyMap.set(of.key, f.key);
    floors.push({
      ...of, key: f.key, source: f.source, area: f.area,
      setAside: settings.fixes.setAside.filter(s => s.floor === f.key).map(s => s.key),
    });
  }
  let flags = ref.flags.filter(g => g.floor === null || keyMap.has(g.floor)).map(g => ({
    ...g, floor: g.floor === null ? null : keyMap.get(g.floor)!, id: g.floor === null ? g.id : g.id.replace(`:${g.floor}:`, `:${keyMap.get(g.floor)}:`),
  }));
  const gone = new Set<string>();
  for (const of of floors) {
    const fl = flags.filter(g => g.floor === of.key);
    // closing lines and removed closings
    const closings = (of.closings ?? []).filter(c => !(settings.fixes.closings ?? []).some(x => x.floor === of.key && x.use === 'none' && c.kind !== 'staff' && sameEnds(x.a, x.b, c.a, c.b, 0.3)));
    (settings.fixes.closings ?? []).forEach((x, i) => { if (x.floor === of.key && x.use === 'line') closings.push({ kind: 'staff', a: x.a, b: x.b, fix: i }); });
    for (const g of fl) {
      if (g.kind === 'doorway' && g.ref.a && g.ref.b && !closings.some(c => c.kind === 'doorway' && sameEnds(c.a, c.b, g.ref.a!, g.ref.b!, 0.3))) gone.add(g.id);
    }
    of.closings = closings;
    // unfloored areas: "it is outdoors" answers one, a closing line across its mouth or "floor here" floors it
    const unfloored = (of.unfloored ?? []).map(u => ({ ...u }));
    const keep: typeof unfloored = [];
    for (const u of unfloored) {
      const ring = flat(u.o);
      const inside = (p: Vec2) => ringContains(ring, p[0], p[1]);
      const fixes = (settings.fixes.rooms ?? []).filter(r => r.floor === of.key && inside(r.at));
      const closed = !!u.mouth && closings.some(c => c.kind === 'staff' && sameEnds(c.a, c.b, u.mouth![0], u.mouth![1], 0.6));
      if (closed || fixes.some(r => r.slab === 'floor')) {
        for (const g of fl) if (g.kind === 'slab-gap' && g.ref.a && u.mouth && sameEnds(g.ref.a, g.ref.b!, u.mouth[0], u.mouth[1], 0.05)) gone.add(g.id);
        continue;
      }
      if (fixes.some(r => r.slab === 'none')) {
        u.answered = true;
        for (const g of fl) if (g.kind === 'slab-gap' && g.at && inside(g.at)) gone.add(g.id);
        if (u.mouth) for (const g of fl) if (g.kind === 'slab-gap' && g.ref.a && sameEnds(g.ref.a, g.ref.b!, u.mouth[0], u.mouth[1], 0.05)) gone.add(g.id);
      }
      keep.push(u);
    }
    of.unfloored = keep;
    // RR (CODE-1 + BRK-2): "It is floor" on a cut X hole: a 'floor here' room fix inside an X shaft or void keeps it as
    // floor (the hole, its ring in the plate and its flag go), as build/slabs.py cut_slab does
    const floorFixes = (settings.fixes.rooms ?? []).filter(r => r.floor === of.key && r.slab === 'floor');
    const keptX = (h: { what: string; o: Vec2[] }) => (h.what === 'shaft' || h.what === 'void')
      && floorFixes.some(r => ringContains(flat(h.o), r.at[0], r.at[1]));
    for (const h of (of.holes ?? []).filter(keptX)) {
      const at = floorFixes.find(r => ringContains(flat(h.o), r.at[0], r.at[1]))!.at;
      of.slabs = of.slabs.map(sl => ({ ...sl, h: sl.h.filter(ring => !ringContains(flat(ring), at[0], at[1])) }));
      for (const g of fl) {
        if (g.kind === 'hole-skipped' && g.severity === 'info' && g.bbox && at[0] >= g.bbox[0] && at[0] <= g.bbox[2] && at[1] >= g.bbox[1] && at[1] <= g.bbox[3]) gone.add(g.id);
      }
    }
    // rooms: a name, no ceiling, no floor here (a hole)
    const holes = (of.holes ?? []).filter(h => !keptX(h));
    of.spaces = (of.spaces ?? []).map(s => {
      const r = (settings.fixes.rooms ?? []).find(x => x.floor === of.key && polyContains(flat(s.o), s.h.map(flat), x.at[0], x.at[1]));
      if (!r) return s;
      if (r.slab === 'none') holes.push({ what: 'no floor', o: s.o, h: s.h });
      return { ...s, name: r.name ?? s.name, names: r.name ? [r.name] : s.names, ceiling: r.ceiling === 'none' ? false : s.ceiling, source: s.source };
    });
    of.holes = holes;
    // stairs: kept as lines, or climbed (from the picked bottom)
    of.stairs = (of.stairs ?? []).map(st => {
      const ring = flat(st.outline);
      const fx = (settings.fixes.stairs ?? []).find(x => x.floor === of.key && ringContains(ring, x.at[0], x.at[1]));
      if (!fx) return st;
      if (fx.use === 'lines') return { ...st, state: 'lines' as const, why: 'kept by staff', walk: null, bottom: null, to: null };
      if (fx.bottom || fx.use === 'climb') {
        const bottom = fx.bottom ?? st.bottom ?? st.outline[0]!;
        const far = st.outline.reduce((a, p) => (dist(p, bottom) > dist(a, bottom) ? p : a), st.outline[0]!);
        for (const g of fl) if (g.kind === 'stair' && g.ref.stair === st.id) gone.add(g.id);
        return { ...st, state: 'climb' as const, why: null, text: null, walk: st.walk ?? [bottom, far], bottom: st.bottom ?? bottom };
      }
      return st;
    });
  }
  flags = flags.filter(g => !gone.has(g.id));
  return { format: 'build-overlay/1', floors, flags };
}

/** A point inside a reference room or area (sheet m), for tests. */
export function insideOf(o: Vec2[], h: Vec2[][] = []): [number, number] {
  return insidePoint(flat(o), h.map(flat)) ?? [o[0]![0], o[0]![1]];
}

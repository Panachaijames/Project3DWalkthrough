// The build overlay, the flags and the diff in the plan's local frame (docs/upload/DESIGN.md U-12.1: converted once when
// they arrive, never drawn in absolute sheet metres). Owner U7. Pure: no DOM.
// Which records show: the overlay's floor's own (the canvas shows one source's sheet); with no overlay, every flag and
// diff record that has a place (the caller filters by floor then).
import type { Vec2 } from '@walkthrough/viewer';
import type { DiffBody, Flag, FloorArea, OverlayFloor } from '@/upload/contracts';
import type { PlanData, QBox } from './decode';
import { insidePoint, ringBox } from './geom';
import { marksOf } from './marks';

export type LRing = number[];          // x, y, x, y ... in quanta

/** The rooms milestone's overlay fields in the local frame (R-12.4, R-12.6; R6). `at` is a point well inside (local),
 *  `sheetAt` the same point in sheet metres (the test hook's). */
export interface LocalSpace { id: string; name: string; area: number; o: LRing; h: LRing[]; ceiling: boolean; box: QBox; at: Vec2; sheetAt: Vec2 }
export interface LocalStair {
  id: string; state: 'climb' | 'lines'; outline: LRing; walk: LRing | null; bottom: Vec2 | null; box: QBox; at: Vec2; sheetAt: Vec2;
}
/** One of overlay.closings: `index` is its index there (onClosing reports it); staff lines are never clicked. */
export interface LocalClosing { index: number; kind: 'staff' | 'bridge' | 'doorway'; a: Vec2; b: Vec2 }
export interface LocalUnfloored { index: number; area: number; o: LRing; mouth: [Vec2, Vec2] | null; answered: boolean }
export interface LocalMarks {
  lines: [Vec2, Vec2][];
  removed: [Vec2, Vec2][];
  rooms: Set<string>;
  points: { at: Vec2; kind: 'room' | 'floor' | 'outdoors' }[];
  outdoors: Set<number>;
  bottoms: Vec2[];
}

export interface LocalOverlay {
  parts: { kind: string; o: LRing; h: LRing[] }[];
  slabs: { o: LRing; h: LRing[] }[];
  openings: { id: string; kind: 'door' | 'window' | 'passage'; a: Vec2; b: Vec2; flagged: boolean; fixed: boolean; label: string }[];
  furniture: { id: string; kind: string; corners: LRing }[];
  rooms: { name: string; at: Vec2 }[];
  setAside: string[];
  // the rooms milestone (empty with the old rule)
  spaces: LocalSpace[];
  holes: { what: string; o: LRing; h: LRing[] }[];
  stairs: LocalStair[];
  closings: LocalClosing[];
  unfloored: LocalUnfloored[];
  /** The fixes waiting for a Rebuild (plan/marks.ts), or null. */
  marks: LocalMarks | null;
}

export interface LocalFlag { id: string; severity: 'check' | 'info'; at: Vec2; box: QBox | null; title: string }

export interface LocalDiff {
  added: { kind: string; o: LRing }[];
  removed: { kind: string; o: LRing }[];
  openingsAdded: { a: Vec2; b: Vec2 }[];
  openingsRemoved: { a: Vec2; b: Vec2 }[];
}

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const okPoint = (p: unknown): p is Vec2 => Array.isArray(p) && p.length >= 2 && finite(p[0]) && finite(p[1]);

function ring(d: PlanData, o: readonly Vec2[] | undefined): LRing {
  const out: LRing = [];
  for (const p of o ?? []) {
    if (!okPoint(p)) continue;
    const [x, y] = d.toLocal(p[0], p[1]);
    out.push(x, y);
  }
  return out;
}

const local = (d: PlanData, p: Vec2): Vec2 => d.toLocal(p[0], p[1]);

/** The opening's number for its label: the id's last part ("L1-007" -> "007"). */
export function openingLabel(id: string): string {
  const i = id.lastIndexOf('-');
  return i >= 0 && i < id.length - 1 ? id.slice(i + 1) : id;
}

const okRing = (o: unknown): o is Vec2[] => Array.isArray(o);
const ZERO_BOX: QBox = [0, 0, 0, 0];

/** The rooms milestone's fields (R-12.4), each record checked as it is read (the overlay is a raw file). */
function roomsFields(d: PlanData, o: OverlayFloor): Pick<LocalOverlay, 'spaces' | 'holes' | 'stairs' | 'closings' | 'unfloored' | 'marks'> {
  const spaces: LocalSpace[] = [];
  for (const s of Array.isArray(o.spaces) ? o.spaces : []) {
    if (!s || !okRing(s.o)) continue;
    const lo = ring(d, s.o);
    if (lo.length < 6) continue;
    const lh = (Array.isArray(s.h) ? s.h : []).map(h => ring(d, h)).filter(h => h.length >= 6);
    const at = insidePoint(lo, lh) ?? [lo[0]!, lo[1]!];
    spaces.push({
      id: String(s.id ?? ''), name: String(s.name ?? ''), area: finite(s.area) ? s.area : 0, o: lo, h: lh, ceiling: s.ceiling !== false,
      box: ringBox(lo) ?? ZERO_BOX, at, sheetAt: d.toSheet(at[0], at[1]),
    });
  }
  const holes = (Array.isArray(o.holes) ? o.holes : []).filter(h => h && okRing(h.o))
    .map(h => ({ what: String(h.what ?? ''), o: ring(d, h.o), h: (Array.isArray(h.h) ? h.h : []).map(x => ring(d, x)).filter(x => x.length >= 6) }))
    .filter(h => h.o.length >= 6);
  const stairs: LocalStair[] = [];
  for (const s of Array.isArray(o.stairs) ? o.stairs : []) {
    if (!s || !okRing(s.outline)) continue;
    const outline = ring(d, s.outline);
    if (outline.length < 6) continue;
    const walk = okRing(s.walk) ? ring(d, s.walk) : null;
    const at = insidePoint(outline) ?? [outline[0]!, outline[1]!];
    stairs.push({
      id: String(s.id ?? ''), state: s.state === 'climb' ? 'climb' : 'lines', outline, walk: walk && walk.length >= 4 ? walk : null,
      bottom: okPoint(s.bottom) ? local(d, s.bottom) : null, box: ringBox(outline) ?? ZERO_BOX, at, sheetAt: d.toSheet(at[0], at[1]),
    });
  }
  const closings: LocalClosing[] = [];
  (Array.isArray(o.closings) ? o.closings : []).forEach((c, index) => {
    if (!c || !okPoint(c.a) || !okPoint(c.b)) return;
    const kind = c.kind === 'staff' || c.kind === 'doorway' ? c.kind : 'bridge';
    closings.push({ index, kind, a: local(d, c.a), b: local(d, c.b) });
  });
  const unfloored: LocalUnfloored[] = [];
  (Array.isArray(o.unfloored) ? o.unfloored : []).forEach((u, index) => {
    if (!u || !okRing(u.o)) return;
    const lo = ring(d, u.o);
    if (lo.length < 6) return;
    const m = Array.isArray(u.mouth) && u.mouth.length === 2 && okPoint(u.mouth[0]) && okPoint(u.mouth[1])
      ? [local(d, u.mouth[0]), local(d, u.mouth[1])] as [Vec2, Vec2] : null;
    unfloored.push({ index, area: finite(u.area) ? u.area : 0, o: lo, mouth: m, answered: !!u.answered });
  });
  const mk = marksOf(o);
  const marks: LocalMarks | null = mk ? {
    lines: mk.lines.filter(l => okPoint(l.a) && okPoint(l.b)).map(l => [local(d, l.a), local(d, l.b)]),
    removed: mk.removed.filter(l => okPoint(l.a) && okPoint(l.b)).map(l => [local(d, l.a), local(d, l.b)]),
    rooms: new Set(mk.rooms),
    points: mk.points.filter(p => okPoint(p.at)).map(p => ({ at: local(d, p.at), kind: p.kind })),
    outdoors: new Set(mk.outdoors),
    bottoms: mk.bottoms.filter(b => okPoint(b.at)).map(b => local(d, b.at)),
  } : null;
  return { spaces, holes, stairs, closings, unfloored, marks };
}

export function localOverlay(d: PlanData, o: OverlayFloor): LocalOverlay {
  return {
    ...roomsFields(d, o),
    // ceilings are not drawn on the plan (R-5.3: never in a view from above); treads and landings are parts as any
    parts: (o.parts ?? []).filter(p => p.kind !== 'ceiling').map(p => ({ kind: p.kind, o: ring(d, p.o), h: (p.h ?? []).map(h => ring(d, h)) })).filter(p => p.o.length >= 6),
    slabs: (o.slabs ?? []).map(s => ({ o: ring(d, s.o), h: (s.h ?? []).map(h => ring(d, h)) })).filter(s => s.o.length >= 6),
    openings: (o.openings ?? []).filter(x => okPoint(x.a) && okPoint(x.b)).map(x => ({
      id: x.id, kind: x.kind, a: local(d, x.a), b: local(d, x.b), flagged: !!x.flagged, fixed: !!x.fixed, label: openingLabel(x.id),
    })),
    furniture: (o.furniture ?? []).filter(f => finite(f.x) && finite(f.y) && finite(f.w) && finite(f.d)).map(f => {
      const r = ((finite(f.rot) ? f.rot : 0) * Math.PI) / 180, c = Math.cos(r), s = Math.sin(r);
      const corners: LRing = [];
      for (const [u, v] of [[-1, -1], [1, -1], [1, 1], [-1, 1]] as const) {
        const x = f.x + (u * f.w / 2) * c - (v * f.d / 2) * s, y = f.y + (u * f.w / 2) * s + (v * f.d / 2) * c;
        corners.push(...d.toLocal(x, y));
      }
      return { id: f.id, kind: f.kind, corners };
    }),
    rooms: (o.rooms ?? []).filter(r => finite(r.x) && finite(r.y)).map(r => ({ name: String(r.name ?? ''), at: d.toLocal(r.x, r.y) })),
    setAside: (o.setAside ?? []).filter((k): k is string => typeof k === 'string'),
  };
}

/** The flags that have a place, of the overlay's floor (or every floor with no overlay; a flag of no floor always). */
export function localFlags(d: PlanData, flags: readonly Flag[] | null | undefined, floor: string | null): LocalFlag[] {
  const out: LocalFlag[] = [];
  for (const f of flags ?? []) {
    if (!okPoint(f.at)) continue;
    if (floor !== null && f.floor !== null && f.floor !== floor) continue;
    let box: QBox | null = null;
    if (Array.isArray(f.bbox) && f.bbox.length === 4 && f.bbox.every(finite)) {
      const [x0, y0] = d.toLocal(f.bbox[0], f.bbox[1]), [x1, y1] = d.toLocal(f.bbox[2], f.bbox[3]);
      box = [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)];
    }
    out.push({ id: f.id, severity: f.severity === 'info' ? 'info' : 'check', at: local(d, f.at), box, title: String(f.title ?? '') });
  }
  return out;
}

export function localDiff(d: PlanData, diff: DiffBody, floor: string | null): LocalDiff {
  const mine = (f: string) => floor === null || f === floor;
  return {
    added: (diff.partsAdded ?? []).filter(p => mine(p.floor)).map(p => ({ kind: p.kind, o: ring(d, p.o) })).filter(p => p.o.length >= 4),
    removed: (diff.partsRemoved ?? []).filter(p => mine(p.floor)).map(p => ({ kind: p.kind, o: ring(d, p.o) })).filter(p => p.o.length >= 4),
    openingsAdded: (diff.openingsAdded ?? []).filter(x => mine(x.floor) && okPoint(x.a) && okPoint(x.b)).map(x => ({ a: local(d, x.a), b: local(d, x.b) })),
    openingsRemoved: (diff.openingsRemoved ?? []).filter(x => mine(x.floor) && okPoint(x.a) && okPoint(x.b)).map(x => ({ a: local(d, x.a), b: local(d, x.b) })),
  };
}

/** The lit box of a floor area (quanta), or null for the whole file. */
export function areaBox(d: PlanData, area: FloorArea | null | undefined): QBox | null {
  if (!area || area.kind !== 'box' || !Array.isArray(area.bbox) || !area.bbox.every(finite)) return null;
  const [x0, y0] = d.toLocal(area.bbox[0], area.bbox[1]), [x1, y1] = d.toLocal(area.bbox[2], area.bbox[3]);
  return [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)];
}

/** A sheet box (m) in quanta, ordered. */
export function localBox(d: PlanData, b: readonly number[]): QBox | null {
  if (!Array.isArray(b) || b.length !== 4 || !b.every(finite)) return null;
  const [x0, y0] = d.toLocal(b[0]!, b[1]!), [x1, y1] = d.toLocal(b[2]!, b[3]!);
  return [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)];
}

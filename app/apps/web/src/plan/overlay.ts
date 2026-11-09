// The build overlay, the flags and the diff in the plan's local frame (docs/upload/DESIGN.md U-12.1: converted once when
// they arrive, never drawn in absolute sheet metres). Owner U7. Pure: no DOM.
// Which records show: the overlay's floor's own (the canvas shows one source's sheet); with no overlay, every flag and
// diff record that has a place (the caller filters by floor then).
import type { Vec2 } from '@walkthrough/viewer';
import type { DiffBody, Flag, FloorArea, OverlayFloor } from '@/upload/contracts';
import type { PlanData, QBox } from './decode';

export type LRing = number[];          // x, y, x, y ... in quanta

export interface LocalOverlay {
  parts: { kind: string; o: LRing; h: LRing[] }[];
  slabs: { o: LRing; h: LRing[] }[];
  openings: { id: string; kind: 'door' | 'window' | 'passage'; a: Vec2; b: Vec2; flagged: boolean; fixed: boolean; label: string }[];
  furniture: { id: string; kind: string; corners: LRing }[];
  rooms: { name: string; at: Vec2 }[];
  setAside: string[];
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

export function localOverlay(d: PlanData, o: OverlayFloor): LocalOverlay {
  return {
    parts: (o.parts ?? []).map(p => ({ kind: p.kind, o: ring(d, p.o), h: (p.h ?? []).map(h => ring(d, h)) })).filter(p => p.o.length >= 6),
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

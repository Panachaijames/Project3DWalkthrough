// upgradeModel: a complete flight of old `step` parts becomes a stair you can climb (rooms/DESIGN.md R-9, amended 16 Nov
// 2026 on the owner's request: in the hotel built from two pictures, holding W at the main stair stopped after a step).
//
// A model WITHOUT `stairways` (BuiltModel v1) walks with the level-based walker, for which `step` parts are colliders. When
// the viewer loads such a model, every flight of `step` parts that is unambiguously complete is re-kinded, IN MEMORY, to
// `tread` parts of one derived `stairways` record; the model then has `stairways`, so the foot-based walker is on (R-9.1)
// and buildScene, the read-outs and the floor naming all see a v2 stair. The saved model, its stamp and the object handed
// in are never changed: the result is a new object that shares everything but `parts` and `stairways`.
//
// The rule is strict. A flight qualifies only when ALL of this holds; otherwise its steps stay steps, exactly as before,
// and a model with no qualifying flight is returned as it is (the very same object: nothing changes for it):
//  1. the steps of one flight: the same floor and the same flight id (the label's text before " step", e.g. "F1-S1";
//     else the id of the one stairOutlines entry of the floor whose bbox holds the step); at least 3 steps; none of them
//     follows the wall height or has a fit;
//  2. each step's outline is a rectangle with no holes; in the order of their tops the rectangles follow one another
//     along one direction (each starts where the one before ends, within 1 cm), with the same sides (within 1 cm), the
//     same width and the same going (within 1 cm);
//  3. the tops (z1, above the floor's level) rise by one constant riser r (each rise within 1 cm of r, none over 0.25 m,
//     the highest step Walk takes), 0.12 m <= r <= 0.25 m, the first top r above the floor;
//  4. the last top plus r is the level of the floor directly above in the same stack (within 1 cm);
//  5. on the flight's centre line, the point 0.5 m past the last step lies on that upper floor's slab (in a slab part's
//     outline and in none of its holes) and the point 0.3 m before the first step lies on the lower floor's slab.
// Owner: builder A (the model); used by viewer.ts right after the model is parsed, and nowhere else at run time.
import type { BuiltFloor, BuiltModel, Part, Presentation, Ring, Stairway, Vec2 } from '../contracts';

/** 1 cm: every "the same" of the rule. */
export const UPGRADE_TOL = 0.01;
export const UPGRADE_MIN_STEPS = 3;
export const UPGRADE_RISER_MIN = 0.12;
/** Also the highest single rise: Walk's STEP_UP (modes/state.ts). */
export const UPGRADE_RISER_MAX = 0.25;
/** The arrival point past the last step and the foot point before the first (m), both checked against the slabs. */
export const UPGRADE_ARRIVAL = 0.5;
export const UPGRADE_FOOT = 0.3;
/** The walking line reaches this far before and past the flight (the schema's 1.0 m) where the slab does too. */
export const UPGRADE_WALK_REACH = 1.0;

/** Why a flight was left as steps (for tests and a diagnosis; never shown). */
export interface FlightRefusal { floor: string; flight: string; why: string }
export interface UpgradeResult {
  /** The model to build: the input itself when nothing qualified, else a copy with treads and `stairways`. */
  model: BuiltModel;
  /** The derived stairways (empty when the model was left as it is). */
  derived: Stairway[];
  refused: FlightRefusal[];
}

const near = (a: number, b: number, tol = UPGRADE_TOL) => Math.abs(a - b) <= tol + 1e-9;

/** Even-odd point in ring. */
export function inRing(ring: Ring, x: number, y: number): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]!, [xj, yj] = ring[j]!;
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Is the plan point on a slab of this floor: in a slab part's outline and in none of its holes? */
export function onSlab(model: BuiltModel, floor: string, x: number, y: number): boolean {
  return model.parts.some(p => p.kind === 'slab' && p.floor === floor && inRing(p.o, x, y) && !p.h.some(h => inRing(h, x, y)));
}

/** The flight a step belongs to: its label's text before " step", else the one stair outline whose bbox holds it. */
function flightOf(model: BuiltModel, p: Part): string | null {
  const m = /^(.*\S)\s+step\b/.exec(p.label ?? '');
  if (m) return m[1]!;
  const holders = (model.stairOutlines[p.floor] ?? []).filter(s => {
    const [x0, y0, x1, y1] = s.bbox, t = UPGRADE_TOL;
    return typeof s.id === 'string' && s.id !== '' && p.o.every(([x, y]) => x >= x0 - t && x <= x1 + t && y >= y0 - t && y <= y1 + t);
  });
  return holders.length === 1 ? holders[0]!.id! : null;
}

/** The floor directly above `f` in its stack, or null. */
function floorAbove(model: BuiltModel, f: BuiltFloor): BuiltFloor | null {
  const stack = f.stack ?? 'main';
  const higher = model.floors.filter(g => (g.stack ?? 'main') === stack && g.level > f.level).sort((a, b) => a.level - b.level);
  return higher[0] ?? null;
}

interface Extent { u0: number; u1: number; v0: number; v1: number }

/** The rectangle's extents along (ux, uy) and across it, or null when it is no rectangle lying along that direction. */
function extent(o: Ring, ux: number, uy: number): Extent | null {
  if (o.length !== 4) return null;
  const us = o.map(([x, y]) => x * ux + y * uy), vs = o.map(([x, y]) => -x * uy + y * ux);
  const u0 = Math.min(...us), u1 = Math.max(...us), v0 = Math.min(...vs), v1 = Math.max(...vs);
  // every corner on a corner of the box, each of the four corners once
  const seen = new Set<string>();
  for (let i = 0; i < 4; i++) {
    const a = near(us[i]!, u0) ? 0 : near(us[i]!, u1) ? 1 : -1, b = near(vs[i]!, v0) ? 0 : near(vs[i]!, v1) ? 1 : -1;
    if (a < 0 || b < 0) return null;
    seen.add(`${a}${b}`);
  }
  if (seen.size !== 4 || !(u1 - u0 > UPGRADE_TOL) || !(v1 - v0 > UPGRADE_TOL)) return null;
  return { u0, u1, v0, v1 };
}

const centre = (o: Ring): Vec2 => [o.reduce((s, p) => s + p[0], 0) / o.length, o.reduce((s, p) => s + p[1], 0) / o.length];
const r3 = (v: number) => Math.round(v * 1000) / 1000;

/** One flight against the rule: its stairway, or the reason it stays steps. */
function derive(model: BuiltModel, from: BuiltFloor, id: string, parts: Part[]): Stairway | string {
  if (parts.length < UPGRADE_MIN_STEPS) return `only ${parts.length} step(s)`;
  if (parts.some(p => p.follow || p.fit !== undefined || p.stair !== undefined)) return 'a step follows the wall height or has a fit';
  if (parts.some(p => p.h.length > 0)) return 'a step has a hole';
  const to = floorAbove(model, from);
  if (!to) return 'no floor above in the stack';

  const steps = [...parts].sort((a, b) => a.z1 - b.z1), n = steps.length;
  const [ax, ay] = centre(steps[0]!.o), [bx, by] = centre(steps[n - 1]!.o), L = Math.hypot(bx - ax, by - ay);
  if (!(L > UPGRADE_TOL)) return 'the steps do not follow one another';
  const ux = (bx - ax) / L, uy = (by - ay) / L;
  const ext: Extent[] = [];
  for (const p of steps) {
    const e = extent(p.o, ux, uy);
    if (!e) return 'a step is not a rectangle along the flight';
    ext.push(e);
  }
  const first = ext[0]!, last = ext[n - 1]!, goings = ext.map(e => e.u1 - e.u0);
  const going = goings.reduce((s, g) => s + g, 0) / n, width = first.v1 - first.v0;
  for (let k = 0; k < n; k++) {
    const e = ext[k]!;
    if (!near(e.v0, first.v0) || !near(e.v1, first.v1)) return 'the steps are not of one width';
    if (!near(goings[k]!, going)) return 'the goings differ';
    if (k > 0 && !near(e.u0, ext[k - 1]!.u1)) return 'two steps do not share an edge (a step is missing, or they overlap)';
  }

  const tops = steps.map(p => p.z1), riser = tops[n - 1]! / n;
  if (!(riser >= UPGRADE_RISER_MIN - 1e-9 && riser <= UPGRADE_RISER_MAX + 1e-9)) return `a riser of ${riser.toFixed(3)} m`;
  for (let k = 0; k < n; k++) {
    const rise = tops[k]! - (k ? tops[k - 1]! : 0);
    if (!near(rise, riser)) return 'the risers are uneven';
    if (rise > UPGRADE_RISER_MAX + 1e-9) return `a rise of ${rise.toFixed(3)} m`;
  }
  const height = to.level - from.level;
  if (!near(tops[n - 1]! + riser, height)) return `the last step's top is not one riser below ${to.key}`;
  if (height - tops[n - 1]! > UPGRADE_RISER_MAX + 1e-9) return `the last rise to ${to.key} is over ${UPGRADE_RISER_MAX} m`;

  // the centre line, from before the first step to past the last
  const vm = (first.v0 + first.v1) / 2;
  const at = (u: number): Vec2 => [u * ux - vm * uy, u * uy + vm * ux];
  const foot = at(first.u0 - UPGRADE_FOOT), arrival = at(last.u1 + UPGRADE_ARRIVAL);
  if (!onSlab(model, from.key, foot[0], foot[1])) return `no ${from.key} slab before the first step`;
  if (!onSlab(model, to.key, arrival[0], arrival[1])) return `the arrival is not on ${to.key}'s slab`;
  // the walking line: the schema's 1.0 m before and past the flight where the slab reaches that far, else the points checked
  const far0 = at(first.u0 - UPGRADE_WALK_REACH), far1 = at(last.u1 + UPGRADE_WALK_REACH);
  const bottom = onSlab(model, from.key, far0[0], far0[1]) ? far0 : foot;
  const top = onSlab(model, to.key, far1[0], far1[1]) ? far1 : arrival;
  const round = (p: Vec2): Vec2 => [r3(p[0]), r3(p[1])];

  return {
    id, from: from.key, to: to.key, kind: 'straight', risers: n + 1, riser: height / (n + 1), going: r3(going), width: r3(width),
    bottom: round(bottom), top: round(top), walk: [round(bottom), round(top)], direction: 'floors', treads: n, landings: 0,
    // evidence (extra properties are allowed): made by the viewer from the model's step parts, not by a builder
    derived: 'steps',
  };
}

/** The whole answer: the model to build, what was derived and what was refused (and why). */
export function upgradeSteps(model: BuiltModel): UpgradeResult {
  if (model.stairways !== undefined) return { model, derived: [], refused: [] };
  const floors = new Map(model.floors.map(f => [f.key, f]));
  const flights = new Map<string, { floor: BuiltFloor; flight: string; parts: Part[] }>();
  for (const p of model.parts) {
    if (p.kind !== 'step') continue;
    const floor = floors.get(p.floor), flight = flightOf(model, p);
    if (!floor || flight === null) continue;
    const key = `${p.floor}\n${flight}`;
    let entry = flights.get(key);
    if (!entry) flights.set(key, (entry = { floor, flight, parts: [] }));
    entry.parts.push(p);
  }
  const derived: Stairway[] = [], refused: FlightRefusal[] = [];
  const stairOf = new Map<Part, string>(), ids = new Set<string>();
  for (const { floor, flight, parts } of flights.values()) {
    const id = ids.has(flight) ? `${floor.key}:${flight}` : flight;
    const made = derive(model, floor, id, parts);
    if (typeof made === 'string') { refused.push({ floor: floor.key, flight, why: made }); continue; }
    ids.add(id);
    derived.push(made);
    for (const p of parts) stairOf.set(p, id);
  }
  if (!derived.length) return { model, derived, refused };
  const parts = model.parts.map(p => {
    const stair = stairOf.get(p);
    return stair === undefined ? p : { ...p, kind: 'tread' as const, fit: 'storey' as const, stair };
  });
  return { model: { ...model, parts, stairways: derived }, derived, refused };
}

/**
 * The model the viewer builds: `model` itself (the same object) when it has `stairways` or no complete flight of steps,
 * else a copy whose complete flights are treads of derived stairways. Never changes `model`.
 */
export const upgradeModel = (model: BuiltModel): BuiltModel => upgradeSteps(model).model;

/**
 * The derived treads look as the steps did: when the presentation styles `step` and not `tread`, the tread takes the
 * step's colours (its mesh name and "walked on, never a collider" stay the tread's). A new object, or `p` itself.
 */
export function upgradePresentation<P extends Presentation>(p: P, upgraded: boolean): P {
  const step = p.partStyles?.step;
  if (!upgraded || !step || p.partStyles?.tread) return p;
  const { mesh: _mesh, collider: _collider, ...look } = step;
  return { ...p, partStyles: { ...p.partStyles, tread: look } };
}

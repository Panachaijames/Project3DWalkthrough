// Shared bits of U7's plan tests (docs/upload/ACCEPTANCE.md 2.3 U7): the fixture plans, a maker of small synthetic plans,
// a recording 2D context and Path2D for happy-dom (which has neither), and brute-force references for the hit tests.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import type { BuildOverlay, BuildSettings, PlanGeometry } from '@/upload/contracts';

export const APP = path.resolve(__dirname, '../../../..');
export const loadPlan = (name: 'bank1' | 'sukhumvit') =>
  JSON.parse(gunzipSync(readFileSync(path.join(APP, 'fixtures/upload/plan', `${name}.plan.json.gz`))).toString('utf8')) as PlanGeometry;
export const loadJson = <T>(rel: string) => JSON.parse(readFileSync(path.join(APP, rel), 'utf8')) as T;
export const bankSettings = () => loadJson<BuildSettings>('fixtures/upload/settings/bank.json');
export const houseSettings = () => loadJson<BuildSettings>('fixtures/upload/settings/house.json');
export const bankOverlay = () => loadJson<BuildOverlay>('fixtures/upload/overlay/bank.overlay.json');

export interface Item {
  key: string;
  layer: string;
  /** 0 open, 1 closed, 2 solid loop, 3 pattern loop, 4 text, 5 insert anchor. */
  type: number;
  /** Sheet metres. */
  pts: [number, number][];
  eid?: string | null;
}

/** A PlanGeometry from items in sheet metres (quantised to 1 cm from `origin`); sig = 'sig-<key>', rsig = 'rsig-<key>'. */
export function makePlan(items: Item[], origin: [number, number] = [0, 0], quantum = 0.01): PlanGeometry {
  const layers: string[] = [], elementIds: string[] = [];
  const out: PlanGeometry['items'] = { key: [], layer: [], type: [], first: [], count: [], sig: [], rsig: [], eid: [] };
  const pts: number[] = [];
  for (const it of items) {
    if (!layers.includes(it.layer)) layers.push(it.layer);
    if (it.eid && !elementIds.includes(it.eid)) elementIds.push(it.eid);
    out.key.push(it.key);
    out.layer.push(layers.indexOf(it.layer));
    out.type.push(it.type);
    out.first.push(pts.length / 2);
    out.count.push(it.pts.length);
    out.sig.push(`sig-${it.key}`);
    out.rsig.push(it.eid ? `rsig-${it.key}` : '');
    out.eid.push(it.eid ? elementIds.indexOf(it.eid) : -1);
    for (const [x, y] of it.pts) pts.push(Math.round((x - origin[0]) / quantum), Math.round((y - origin[1]) / quantum));
  }
  return { format: 'plan-geometry/1', source: 'a'.repeat(40), units: 'mm', origin, quantum, layers, items: out, elementIds, pts };
}

/** A copy of a plan with its origin moved by (dx, dy) metres: the same local quanta, other sheet coordinates. */
export function shifted(json: PlanGeometry, dx: number, dy: number): PlanGeometry {
  return { ...json, origin: [json.origin[0] + dx, json.origin[1] + dy] };
}

// ---------------------------------------------------------------------------------------------- brute-force references
/** Squared distance point - segment. */
export function d2(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
  const t = l2 > 0 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
  return (ax + t * dx - px) ** 2 + (ay + t * dy - py) ** 2;
}

/** The segments of entry i of a PlanGeometry (quanta), the way the canvas closes types 1 - 3. */
export function segmentsOf(json: PlanGeometry, i: number): [number, number, number, number][] {
  const t = json.items.type[i]!, f = json.items.first[i]!, c = json.items.count[i]!;
  const P = (k: number): [number, number] => [json.pts[2 * k]!, json.pts[2 * k + 1]!];
  if (t === 5 || c === 0) return [];
  if (c === 1) { const [x, y] = P(f); return [[x, y, x, y]]; }
  const out: [number, number, number, number][] = [];
  for (let k = f; k < f + c - 1; k++) out.push([...P(k), ...P(k + 1)]);
  if ((t === 1 || t === 2 || t === 3) && c >= 3) out.push([...P(f + c - 1), ...P(f)]);
  return out;
}

/** The smallest distance (quanta) from a local point to any drawn entry, by brute force. */
export function bruteNearest(json: PlanGeometry, qx: number, qy: number): { d: number; entries: number[] } {
  let best = Infinity, entries: number[] = [];
  for (let i = 0; i < json.items.key.length; i++) {
    for (const [ax, ay, bx, by] of segmentsOf(json, i)) {
      const v = Math.sqrt(d2(qx, qy, ax, ay, bx, by));
      if (v < best - 1e-9) { best = v; entries = [i]; } else if (Math.abs(v - best) <= 1e-9 && !entries.includes(i)) entries.push(i);
    }
  }
  return { d: best, entries };
}

/** A seeded random number generator (the walk checks' Park - Miller). */
export function rng(seed: number): () => number {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

// ------------------------------------------------------------------------------------------- a recording canvas for happy-dom
export type Call = [string, ...unknown[]];

/** Records path commands; the canvas's draw helper replays them into the context it is given. */
export class FakePath {
  readonly cmds: Call[] = [];
  moveTo(x: number, y: number) { this.cmds.push(['moveTo', x, y]); }
  lineTo(x: number, y: number) { this.cmds.push(['lineTo', x, y]); }
  closePath() { this.cmds.push(['closePath']); }
  replay(ctx: FakeCtx, op: 'stroke' | 'fill') { ctx.calls.push([op === 'stroke' ? 'strokePath' : 'fillPath', this.cmds.length, ctx.strokeStyle, ctx.lineWidth]); }
}

/** The 2D context calls a frame makes, recorded. */
export class FakeCtx {
  calls: Call[] = [];
  fillStyle: unknown = '#000';
  strokeStyle: unknown = '#000';
  lineWidth = 1;
  lineJoin = 'miter';
  lineCap = 'butt';
  globalAlpha = 1;
  font = '';
  textAlign = 'start';
  textBaseline = 'alphabetic';
  transforms: number[][] = [];
  texts: string[] = [];
  private rec(name: string) { return (...a: unknown[]) => { this.calls.push([name, ...a]); }; }
  save = this.rec('save'); restore = this.rec('restore');
  setTransform = (...a: number[]) => { this.transforms.push(a); this.calls.push(['setTransform', ...a]); };
  fillRect = this.rec('fillRect'); beginPath = this.rec('beginPath'); moveTo = this.rec('moveTo'); lineTo = this.rec('lineTo');
  closePath = this.rec('closePath'); rect = this.rec('rect'); arc = this.rec('arc'); setLineDash = this.rec('setLineDash');
  clip = this.rec('clip');
  stroke = (...a: unknown[]) => { this.calls.push(['stroke', ...a]); };
  fill = (...a: unknown[]) => { this.calls.push(['fill', ...a]); };
  fillText = (t: string, ...a: unknown[]) => { this.texts.push(t); this.calls.push(['fillText', t, ...a]); };
  strokeText = this.rec('strokeText');
  measureText = (t: string) => ({ width: t.length * 6 }) as TextMetrics;
  getImageData = () => ({ data: new Uint8ClampedArray(4) });
  reset() { this.calls = []; this.transforms = []; this.texts = []; }
}

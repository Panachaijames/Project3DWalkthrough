// RR (the rooms milestone's independent review and fix, area "web"; /wt-rr TRIAGE S7, S13): the plan canvas in happy-dom
// with a recording 2D context.
// * S7: with an overlay (the Check step) the first view and Fit (F, the page's button) show that floor's own plate and
//   parts with a margin, not the whole sheet (a DWG may hold every floor and the elevations); another floor of the same
//   sheet fits again, a new overlay of the same floor keeps the view; with no overlay (Files, Layers, Floors) the sheet.
// * S13: the room and the stair open in the Check step's panel are outlined in a strong colour whatever the ticks; the
//   floor plate has a faint tint, so the Floor plate tick shows a change.
import { act, StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { decodePlan, PlanCanvas, type PlanCanvasProps } from '@/plan';
import { PICKED, ROOM_FILL, SLAB_FILL } from '@/plan/colours';
import { controllerOf, HOME_MARGIN_M, type PlanController } from '@/plan/controller';
import { NO_MARKS, withMarks } from '@/plan/marks';
import { fitView } from '@/plan/view';
import type { FloorArea, OverlayFloor, PlanGeometry } from '@/upload/contracts';
import { FakeCtx, FakePath, makePlan, type Item } from '../plan/kit';
import { referenceOverlay, referencePlan } from '../mock-api/rooms';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** A recording context that also keeps the style of every fill and stroke. */
class StyleCtx extends FakeCtx {
  styled: { op: 'fill' | 'stroke'; style: unknown; alpha: number }[] = [];
  override fill = (...a: unknown[]) => { this.styled.push({ op: 'fill', style: this.fillStyle, alpha: this.globalAlpha }); this.calls.push(['fill', ...a]); };
  override stroke = (...a: unknown[]) => { this.styled.push({ op: 'stroke', style: this.strokeStyle, alpha: this.globalAlpha }); this.calls.push(['stroke', ...a]); };
  override reset() { super.reset(); this.styled = []; }
}

let restore: (() => void)[] = [];
let ctxs: StyleCtx[] = [];
let root: Root | null = null;
let host: HTMLDivElement | null = null;

beforeEach(() => {
  ctxs = [];
  const proto = HTMLCanvasElement.prototype as unknown as { getContext: (t: string) => unknown };
  const getContext = proto.getContext;
  proto.getContext = function (t: string) { if (t !== '2d') return null; const c = new StyleCtx(); ctxs.push(c); return c; };
  const g = globalThis as { Path2D?: unknown };
  const hadPath = 'Path2D' in g, oldPath = g.Path2D;
  g.Path2D = FakePath;
  const rect = HTMLElement.prototype.getBoundingClientRect;
  HTMLElement.prototype.getBoundingClientRect = function () {
    const sized = this instanceof HTMLCanvasElement || (this as HTMLElement).dataset?.planCanvas === 'canvas';
    return { x: 0, y: 0, left: 0, top: 0, right: sized ? 1000 : 0, bottom: sized ? 800 : 0, width: sized ? 1000 : 0, height: sized ? 800 : 0, toJSON: () => ({}) } as DOMRect;
  };
  restore.push(() => {
    proto.getContext = getContext;
    if (hadPath) g.Path2D = oldPath; else delete g.Path2D;
    HTMLElement.prototype.getBoundingClientRect = rect;
  });
});
afterEach(async () => {
  if (root) await act(async () => { root!.unmount(); });
  root = null;
  host?.remove();
  host = null;
  for (const f of restore.splice(0)) f();
});

async function mount(json: PlanGeometry, extra: Partial<PlanCanvasProps> = {}) {
  const plan = decodePlan(json);
  const props: PlanCanvasProps = { plan, roleOf: () => 'wall', selected: new Set(), setAside: new Set(), tool: 'select', ...extra };
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
  await act(async () => { root!.render(<StrictMode><PlanCanvas {...props} /></StrictMode>); });
  const canvas = host.querySelector('canvas')!;
  const ctl = controllerOf.get(canvas)!;
  const rerender = async (p: Partial<PlanCanvasProps>) => {
    Object.assign(props, p);
    await act(async () => { root!.render(<StrictMode><PlanCanvas {...props} /></StrictMode>); });
  };
  return { plan, props, canvas, ctl, rerender };
}
const key = (canvas: HTMLCanvasElement, k: string) => canvas.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
const ctxOf = (ctl: PlanController) => ctxs.find(c => c === (ctl as unknown as { ctx: StyleCtx }).ctx) ?? ctxs.at(-1)!;
const redraw = (ctl: PlanController) => { const c = ctxOf(ctl); c.reset(); ctl.drawNow(); return c; };
const styles = (c: StyleCtx, op: 'fill' | 'stroke') => c.styled.filter(s => s.op === op).map(s => s.style);

// ------------------------------------------------------------------------------------------------ S7: fit the floor
/** One sheet holding a 20 x 12 m floor at the origin, a second floor 100 m to the east and the elevations far to the
 *  north-east (as the house's DWG holds both plans and the elevations). */
const SHEET: Item[] = [
  { key: 'W1', layer: 'WALL', type: 0, pts: [[0, 0], [20, 0]] },
  { key: 'W2', layer: 'WALL', type: 0, pts: [[0, 12], [20, 12]] },
  { key: 'U1', layer: 'WALL', type: 0, pts: [[100, 0], [120, 0]] },
  { key: 'U2', layer: 'WALL', type: 0, pts: [[100, 12], [120, 12]] },
  { key: 'E1', layer: 'ELEV', type: 0, pts: [[200, 200], [300, 200]] },
  { key: 'E2', layer: 'ELEV', type: 0, pts: [[200, 260], [300, 260]] },
];
const Q = 0.01;                                                    // makePlan's quantum (m)
function floorOverlay(key: string, x0: number, geometry = true): OverlayFloor {
  return {
    key, source: 'c'.repeat(40), toSheet: [0, 0], area: { kind: 'wholeFile' },
    parts: geometry ? [{ i: 0, kind: 'wall', label: null, o: [[x0, -0.1], [x0 + 20, -0.1], [x0 + 20, 0.1], [x0, 0.1]], h: [] }] : [],
    slabs: geometry ? [{ o: [[x0, 0], [x0 + 20, 0], [x0 + 20, 12], [x0, 12]], h: [] }] : [],
    openings: [], furniture: [], rooms: [], setAside: [],
  };
}
/** The view that fits a sheet box (m) with the floor margin of controller.ts. */
function homeView(box: [number, number, number, number]) {
  const m = Math.max(HOME_MARGIN_M, 0.04 * Math.max(box[2] - box[0], box[3] - box[1]));
  return fitView([(box[0] - m) / Q, (box[1] - m) / Q, (box[2] + m) / Q, (box[3] + m) / Q], { w: 1000, h: 800 });
}

describe('S7: the Check plan opens on its floor, and Fit fits the floor', () => {
  it('with an overlay: the first view and F show the floor\'s plate and parts (with a margin), not the sheet', async () => {
    const { ctl, canvas } = await mount(makePlan(SHEET), { overlay: floorOverlay('L1', 0) });
    const want = homeView([0, -0.1, 20, 12]);
    expect(ctl.view!.cx).toBeCloseTo(want.cx, 6);
    expect(ctl.view!.cy).toBeCloseTo(want.cy, 6);
    expect(ctl.view!.s).toBeCloseTo(want.s, 9);
    key(canvas, '+');
    key(canvas, 'ArrowLeft');
    expect(ctl.view!.s).not.toBeCloseTo(want.s, 9);
    key(canvas, 'f');                                                 // the page's Fit button sends this key
    expect(ctl.view!.cx).toBeCloseTo(want.cx, 6);
    expect(ctl.view!.s).toBeCloseTo(want.s, 9);
  });

  it('with no overlay (the Files, Layers and Floors steps) the sheet is fitted as before, an area or not', async () => {
    const area: FloorArea = { kind: 'box', bbox: [100, 0, 120, 12], pad: 0.5, match: 'all' };
    const { ctl, canvas } = await mount(makePlan(SHEET), { area });
    const sheet = fitView([0, 0, 300 / Q, 260 / Q], { w: 1000, h: 800 });
    expect(ctl.view!.cx).toBeCloseTo(sheet.cx, 6);
    expect(ctl.view!.s).toBeCloseTo(sheet.s, 9);
    key(canvas, '+');
    key(canvas, 'F');
    expect(ctl.view!.s).toBeCloseTo(sheet.s, 9);
  });

  it('another floor of the same sheet fits again; a new overlay of the same floor (a Rebuild, a fix mark) keeps the view', async () => {
    const { ctl, canvas, rerender } = await mount(makePlan(SHEET), { overlay: floorOverlay('L1', 0) });
    await rerender({ overlay: floorOverlay('L2', 100) });
    const want = homeView([100, -0.1, 120, 12]);
    expect(ctl.view!.cx).toBeCloseTo(want.cx, 6);
    expect(ctl.view!.s).toBeCloseTo(want.s, 9);
    key(canvas, '+');
    const zoomed = { ...ctl.view! };
    await rerender({ overlay: withMarks(floorOverlay('L2', 100), { ...NO_MARKS, pickedRoom: 'x' }) });
    expect(ctl.view).toEqual(zoomed);
    // a focus box still wins over the floor (Show on a flag)
    await rerender({ focus: [105, 5, 106, 6] });
    expect(ctl.view!.cx).toBeCloseTo(105.5 / Q, 6);
  });

  it('an overlay with no plate and no parts: its area box with the margin; with no area either: the sheet', async () => {
    const area: FloorArea = { kind: 'box', bbox: [100, 0, 120, 12], pad: 0.5, match: 'all' };
    const { ctl, rerender } = await mount(makePlan(SHEET), { overlay: floorOverlay('L2', 100, false), area });
    const want = homeView([100, 0, 120, 12]);
    expect(ctl.view!.cx).toBeCloseTo(want.cx, 6);
    expect(ctl.view!.s).toBeCloseTo(want.s, 9);
    await rerender({ overlay: floorOverlay('L3', 0, false), area: { kind: 'wholeFile' } });
    const sheet = fitView([0, 0, 300 / Q, 260 / Q], { w: 1000, h: 800 });
    expect(ctl.view!.cx).toBeCloseTo(sheet.cx, 6);
    expect(ctl.view!.s).toBeCloseTo(sheet.s, 9);
  });
});

// ------------------------------------------------------------------------------------- S13: the picked room, the plate
describe('S13: the room or stair open in the panel is outlined; the plate has a faint tint', () => {
  const SHA = 'b'.repeat(40);
  const ref = () => mount(referencePlan(SHA, 0), { overlay: referenceOverlay().floors[0]!, tool: 'rooms' });

  it('the picked room is outlined and tinted in the strong colour, whatever the ticks; nothing when none is picked', async () => {
    const base = referenceOverlay().floors[0]!;
    const { ctl, rerender } = await ref();
    let c = redraw(ctl);
    expect(styles(c, 'stroke')).not.toContain(PICKED.colour);
    await rerender({ overlay: withMarks(base, { ...NO_MARKS, pickedRoom: 'ground-R002' }) });
    c = redraw(ctl);
    expect(styles(c, 'stroke').filter(s => s === PICKED.colour).length).toBe(1);
    expect(styles(c, 'fill')).toContain(PICKED.colour);
    await rerender({ show: { rooms: false, plate: false, furniture: false } });
    c = redraw(ctl);
    expect(styles(c, 'fill')).not.toContain(ROOM_FILL);
    expect(styles(c, 'stroke')).toContain(PICKED.colour);                          // still found with the rooms off
    await rerender({ overlay: withMarks(base, { ...NO_MARKS, pickedRoom: 'no-such-room' }) });
    expect(styles(redraw(ctl), 'stroke')).not.toContain(PICKED.colour);
  });

  it('the picked stair is outlined in the strong colour', async () => {
    const base = referenceOverlay().floors[0]!;
    const { ctl, rerender } = await ref();
    await rerender({ overlay: withMarks(base, { ...NO_MARKS, pickedStair: 'ground-ST2' }) });
    const c = redraw(ctl);
    expect(styles(c, 'stroke').filter(s => s === PICKED.colour).length).toBe(1);
    expect(styles(c, 'fill')).not.toContain(PICKED.colour);
  });

  it('the plate is tinted under its dashed outline; the Floor plate tick takes the tint away', async () => {
    const { ctl, rerender } = await ref();
    let c = redraw(ctl);
    const tint = c.styled.filter(s => s.op === 'fill' && s.style === SLAB_FILL);
    expect(tint.length).toBe(referenceOverlay().floors[0]!.slabs.length);
    expect(tint.every(s => s.alpha > 0 && s.alpha < 0.15)).toBe(true);
    await rerender({ show: { rooms: true, plate: false, furniture: true } });
    c = redraw(ctl);
    expect(styles(c, 'fill')).not.toContain(SLAB_FILL);
  });
});

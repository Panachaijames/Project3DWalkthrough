// R6 (docs/rooms/ACCEPTANCE.md 2.3 R6 "the canvas"; DESIGN.md R-6.2, R-6.4, R-12.6): the plan canvas's rooms milestone in
// happy-dom with a recording 2D context: the tool 'draw-line' (two clicks, each end snapped to a drawn vertex within
// 6 px; Esc and a tool change drop the first end; a drag still pans), the tool 'rooms' (a stair, then one of the app's
// closings, then a room, else the point), the local frame (a plan at y = -3,500 m picks the same), `show` (each tick
// takes its layer away), the rooms' area in the hover text, the fixes waiting for a Rebuild (plan/marks.ts) and the test
// hook window.__plan's answers (testHook()). The plan is the mock's reference-building plan with the frozen overlay.
import type { Vec2 } from '@walkthrough/viewer';
import { act, StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { decodePlan, PlanCanvas, type PlanCanvasProps } from '@/plan';
import { CLOSING_APP, HOLE_HATCH, ROOM_FILL, STAIR_WALK, UNFLOORED_HATCH, WAITING } from '@/plan/colours';
import { controllerOf, roomText, type PlanController } from '@/plan/controller';
import { withMarks } from '@/plan/marks';
import type { OverlayFloor, PlanGeometry } from '@/upload/contracts';
import { pointIn } from '@/build/roomsFixes';
import { FakeCtx, FakePath, shifted } from '../plan/kit';
import { referenceOverlay, referencePlan } from '../mock-api/rooms';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** A recording context that also keeps the style of every fill and stroke. */
class StyleCtx extends FakeCtx {
  styled: { op: 'fill' | 'stroke'; style: unknown; alpha: number; dash: unknown }[] = [];
  private dashNow: unknown = [];
  override setLineDash = (...a: unknown[]) => { this.dashNow = a[0]; this.calls.push(['setLineDash', ...a]); };
  override fill = (...a: unknown[]) => { this.styled.push({ op: 'fill', style: this.fillStyle, alpha: this.globalAlpha, dash: this.dashNow }); this.calls.push(['fill', ...a]); };
  override stroke = (...a: unknown[]) => { this.styled.push({ op: 'stroke', style: this.strokeStyle, alpha: this.globalAlpha, dash: this.dashNow }); this.calls.push(['stroke', ...a]); };
  override reset() { super.reset(); this.styled = []; }
}

let restore: (() => void)[] = [];
let ctxs: StyleCtx[] = [];
let root: Root | null = null;
let host: HTMLDivElement | null = null;

function stubCanvas(): void {
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
}

const SHA = 'b'.repeat(40);
function shiftOverlay(o: OverlayFloor, dy: number): OverlayFloor {
  const p = (v: Vec2): Vec2 => [v[0], v[1] + dy];
  return {
    ...o,
    parts: o.parts.map(x => ({ ...x, o: x.o.map(p), h: x.h.map(r => r.map(p)) })),
    slabs: o.slabs.map(x => ({ o: x.o.map(p), h: x.h.map(r => r.map(p)) })),
    openings: o.openings.map(x => ({ ...x, a: p(x.a), b: p(x.b) })),
    rooms: o.rooms.map(r => ({ ...r, y: r.y + dy })),
    spaces: o.spaces?.map(s => ({ ...s, o: s.o.map(p), h: s.h.map(r => r.map(p)) })),
    holes: o.holes?.map(h => ({ ...h, o: h.o.map(p), h: h.h.map(r => r.map(p)) })),
    stairs: o.stairs?.map(s => ({ ...s, outline: s.outline.map(p), walk: s.walk ? s.walk.map(p) : null, bottom: s.bottom ? p(s.bottom) : null })),
    closings: o.closings?.map(c => ({ ...c, a: p(c.a), b: p(c.b) })),
    unfloored: o.unfloored?.map(u => ({ ...u, o: u.o.map(p), mouth: u.mouth ? [p(u.mouth[0]), p(u.mouth[1])] : null })),
  };
}

async function mount(opts: { floor?: number; dy?: number; extra?: Partial<PlanCanvasProps> } = {}) {
  const floor = opts.floor ?? 0, dy = opts.dy ?? 0;
  let json: PlanGeometry = referencePlan(SHA, floor);
  if (dy) json = shifted(json, 0, dy);
  const plan = decodePlan(json);
  const base = referenceOverlay().floors[floor]!;
  const overlay = dy ? shiftOverlay(base, dy) : base;
  const log: unknown[][] = [];
  const props: PlanCanvasProps = {
    plan, roleOf: i => (({ 'A-WALL': 'wall', 'A-DOOR': 'door', 'A-AREA-IDEN': 'room-name', 'A-FLOR-HRAL': 'railing', 'S-STRS': 'stair' } as const)[plan.layers[i]! as 'A-WALL'] ?? 'other'),
    selected: new Set(), setAside: new Set(), tool: 'rooms', overlay,
    onSelect: (keys, mode) => log.push(['select', keys, mode]), onPick: p => log.push(['pick', p]),
    onLine: (a, b) => log.push(['line', a, b]), onSpace: id => log.push(['space', id]), onStair: id => log.push(['stair', id]),
    onClosing: i => log.push(['closing', i]), onPoint: p => log.push(['point', p]), onFlag: id => log.push(['flag', id]),
    onOpening: id => log.push(['opening', id]),
    ...opts.extra,
  };
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
  return { plan, props, log, canvas, ctl, rerender, overlay, dy };
}

const at = (ctl: PlanController, p: Vec2) => ctl.sheetToScreen(p[0], p[1])!;
function pointer(canvas: HTMLCanvasElement, type: string, [x, y]: [number, number], init: PointerEventInit = {}) {
  canvas.dispatchEvent(new PointerEvent(type, { clientX: x, clientY: y, button: 0, pointerId: 1, bubbles: true, cancelable: true, ...init }));
}
const clickAt = (canvas: HTMLCanvasElement, p: [number, number]) => { pointer(canvas, 'pointerdown', p); pointer(canvas, 'pointerup', p); };
const key = (canvas: HTMLCanvasElement, k: string) => canvas.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
const ctxOf = (ctl: PlanController) => ctxs.find(c => c === (ctl as unknown as { ctx: StyleCtx }).ctx) ?? ctxs.at(-1)!;
const redraw = (ctl: PlanController) => { const c = ctxOf(ctl); c.reset(); ctl.drawNow(); return c; };

beforeEach(() => { ctxs = []; stubCanvas(); });
afterEach(async () => {
  if (root) await act(async () => { root!.unmount(); });
  host?.remove();
  root = null; host = null;
  for (const f of restore.splice(0)) f();
});

describe('the tool Rooms and stairs (R-6.4: a stair, then one of the app\'s closings, then a room, else the point)', () => {
  for (const dy of [0, -3500]) {
    it(`each kind of click reports its record${dy ? ' (a plan at y = -3,500 m picks the same)' : ''}`, async () => {
      const { ctl, canvas, log, overlay } = await mount({ dy });
      const s1 = overlay.stairs![0]!, st2 = overlay.stairs![1]!;
      clickAt(canvas, at(ctl, pointIn(s1.outline)));
      clickAt(canvas, at(ctl, pointIn(st2.outline)));
      const c = overlay.closings![0]!;
      clickAt(canvas, at(ctl, [(c.a[0] + c.b[0]) / 2 + 0.02, (c.a[1] + c.b[1]) / 2]));
      const kitchen = overlay.spaces![1]!;
      clickAt(canvas, at(ctl, pointIn(kitchen.o, kitchen.h)));
      const garage = overlay.unfloored![0]!;
      const g = pointIn(garage.o);
      clickAt(canvas, at(ctl, g));
      expect(log.slice(0, 4)).toEqual([['stair', 'S1'], ['stair', 'ground-ST2'], ['closing', 0], ['space', 'ground-R002']]);
      expect(log[4]![0]).toBe('point');
      const p = log[4]![1] as Vec2;
      expect(Math.abs(p[0] - g[0])).toBeLessThan(0.02);
      expect(Math.abs(p[1] - g[1])).toBeLessThan(0.02);
    });
  }

  it('a staff closing line is never clicked; a click inside a stair goes to the stair, not to the room around it', async () => {
    const base = referenceOverlay().floors[0]!;
    const overlay = { ...base, closings: [{ kind: 'staff' as const, a: [8.9, 8.9] as Vec2, b: [11.8, 8.9] as Vec2, fix: 0 }] };
    const { ctl, canvas, log } = await mount({ extra: { overlay } });
    clickAt(canvas, at(ctl, [10.35, 8.9]));
    expect(log.at(-1)?.[0]).not.toBe('closing');
    const living = overlay.spaces![0]!;
    const s1 = overlay.stairs![0]!;
    // a point of S1's outline that lies in the living room's outline too, if there is one; else S1's own point
    clickAt(canvas, at(ctl, pointIn(s1.outline)));
    expect(log.at(-1)).toEqual(['stair', 'S1']);
    void living;
  });
});

describe('the tool Draw a line (R-6.2: two clicks, each end snapped as pick-point snaps)', () => {
  it('reports the two ends snapped to drawn vertices within 6 px; one click alone reports nothing', async () => {
    const { ctl, canvas, log, overlay, plan } = await mount({ extra: { tool: 'draw-line' } });
    const json = referencePlan(SHA, 0);
    const vertices: Vec2[] = [];
    for (let i = 0; i < json.pts.length; i += 2) vertices.push([json.pts[i]! / 100, json.pts[i + 1]! / 100]);
    const wall = overlay.parts.find(p => p.kind === 'wall')!;
    const [c0, c1] = [wall.o[0]!, wall.o[2]!];
    const s0 = at(ctl, c0), s1 = at(ctl, c1);
    const clicks: [number, number][] = [[s0[0] + 3, s0[1] - 2], [s1[0] - 2, s1[1] + 3]];
    clickAt(canvas, clicks[0]!);
    expect(log.filter(e => e[0] === 'line')).toEqual([]);
    clickAt(canvas, clicks[1]!);
    const lines = log.filter(e => e[0] === 'line');
    expect(lines.length).toBe(1);
    const [, a, b] = lines[0] as [string, Vec2, Vec2];
    [a, b].forEach((end, k) => {
      // a drawn vertex of the plan, within 6 px of the click
      expect(vertices.some(v => Math.abs(v[0] - end[0]) < 1e-6 && Math.abs(v[1] - end[1]) < 1e-6), `${end} is a vertex`).toBe(true);
      const s = at(ctl, end);
      expect(Math.hypot(s[0] - clicks[k]![0], s[1] - clicks[k]![1])).toBeLessThanOrEqual(6);
    });
    // far from any drawn item a click keeps its own point
    clickAt(canvas, [5, 5]);
    clickAt(canvas, [15, 5]);
    const free = log.filter(e => e[0] === 'line')[1] as [string, Vec2, Vec2];
    expect(free[1]).toEqual(ctl.screenToSheet(5, 5));
    void plan;
  });

  it('Esc drops the first end, and so does a tool change; a drag pans; the first end is drawn', async () => {
    const { ctl, canvas, log, rerender } = await mount({ extra: { tool: 'draw-line' } });
    clickAt(canvas, [300, 300]);
    expect(redraw(ctl).styled.length).toBeGreaterThan(0);
    key(canvas, 'Escape');
    clickAt(canvas, [500, 300]);
    clickAt(canvas, [600, 320]);
    expect(log.filter(e => e[0] === 'line').length).toBe(1);
    const first = log.find(e => e[0] === 'line')! as [string, Vec2, Vec2];
    expect(first[1][0]).toBeGreaterThan(ctl.screenToSheet(450, 300)![0]);           // the line started at the 2nd click
    clickAt(canvas, [300, 300]);
    await rerender({ tool: 'rooms' });
    await rerender({ tool: 'draw-line' });
    clickAt(canvas, [700, 300]);
    expect(log.filter(e => e[0] === 'line').length).toBe(1);                      // the first end was dropped
    const v0 = { ...ctl.view! };
    pointer(canvas, 'pointerdown', [100, 100]);
    pointer(canvas, 'pointermove', [160, 140], { buttons: 1 });
    pointer(canvas, 'pointerup', [160, 140]);
    expect(ctl.view!.cx).not.toBe(v0.cx);
  });
});

describe('what is drawn (R-12.6): rooms, holes, stairs, closings, unfloored areas; the ticks; the waiting marks', () => {
  const styles = (c: StyleCtx, op: 'fill' | 'stroke') => c.styled.filter(s => s.op === op).map(s => s.style);

  it('rooms are tinted, holes and unfloored areas hatched, the walking line and the dashed closing drawn; each tick takes its layer away', async () => {
    const up = await mount({ floor: 1 });
    let c = redraw(up.ctl);
    expect(styles(c, 'fill')).toContain(ROOM_FILL);
    expect(styles(c, 'stroke')).toContain(HOLE_HATCH.colour);
    expect(c.calls.filter(x => x[0] === 'clip').length).toBe(2);                  // two holes upstairs
    await up.rerender({ show: { rooms: false, plate: true, furniture: true } });
    c = redraw(up.ctl);
    expect(styles(c, 'fill')).not.toContain(ROOM_FILL);
    await up.rerender({ show: { rooms: true, plate: false, furniture: true } });
    c = redraw(up.ctl);
    expect(c.calls.filter(x => x[0] === 'clip').length).toBe(0);
    expect(styles(c, 'fill')).toContain(ROOM_FILL);
    await act(async () => { root!.unmount(); });
    root = null;

    const g = await mount();
    c = redraw(g.ctl);
    expect(styles(c, 'stroke')).toContain(STAIR_WALK.colour);
    expect(styles(c, 'stroke')).toContain(UNFLOORED_HATCH.colour);
    const closing = c.styled.find(s => s.op === 'stroke' && s.style === CLOSING_APP.colour)!;
    expect(Array.isArray(closing.dash) && (closing.dash as number[]).length).toBe(2);   // dashed
    await g.rerender({ show: { rooms: false, plate: false, furniture: false } });
    c = redraw(g.ctl);
    expect(styles(c, 'stroke')).toContain(STAIR_WALK.colour);                      // stairs and closings: always
    expect(styles(c, 'stroke')).toContain(CLOSING_APP.colour);
    expect(styles(c, 'stroke')).not.toContain(UNFLOORED_HATCH.colour);
    expect(c.calls.filter(x => x[0] === 'clip').length).toBe(0);
  });

  it('a fix waiting for a Rebuild is drawn dashed orange on the plan (plan/marks.ts)', async () => {
    const base = referenceOverlay().floors[0]!;
    const { ctl, rerender } = await mount();
    let c = redraw(ctl);
    expect(styles(c, 'stroke')).not.toContain(WAITING.colour);
    await rerender({ overlay: withMarks(base, { lines: [{ a: [8.9, 8.9], b: [11.8, 8.9] }], removed: [], rooms: ['ground-R001'], points: [], outdoors: [], bottoms: [] }) });
    c = redraw(ctl);
    const waiting = c.styled.filter(s => s.op === 'stroke' && s.style === WAITING.colour);
    expect(waiting.length).toBe(2);                                                 // the line and the room's outline
    expect(waiting.every(s => (s.dash as number[]).length === 2)).toBe(true);
  });

  it('the room under the pointer has its area in the hover text', async () => {
    const { ctl, canvas, overlay } = await mount();
    const kitchen = overlay.spaces![1]!;
    const p = at(ctl, pointIn(kitchen.o, kitchen.h));
    pointer(canvas, 'pointermove', p);
    const tip = host!.querySelector<HTMLElement>('[data-plan-tip]')!;
    await act(async () => { await new Promise(r => setTimeout(r, 40)); });
    expect(tip.textContent).toContain('KITCHEN · 19.7 m²');
    expect(roomText({ name: '', area: 3.04, ceiling: false })).toBe('Room · 3.0 m² · no ceiling');
  });
});

describe('the test hook window.__plan (R-12.6)', () => {
  it('turns a sheet point into page pixels, and lists the rooms and stairs on screen with a point inside each', async () => {
    const { ctl, overlay } = await mount();
    const hook = ctl.testHook();
    expect(hook.spaces().map(s => [s.id, s.name, s.area])).toEqual(overlay.spaces!.map(s => [s.id, s.name, s.area]));
    expect(hook.stairs().map(s => [s.id, s.state])).toEqual([['S1', 'climb'], ['ground-ST2', 'lines']]);
    for (const s of hook.spaces()) {
      const page = hook.toPage(s.at)!;
      expect(page).toEqual(ctl.sheetToScreen(s.at[0], s.at[1]));
    }
    expect(hook.toPage([1e6, 1e6])).toBeNull();
  });
});

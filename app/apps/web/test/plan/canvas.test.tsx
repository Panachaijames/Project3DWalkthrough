// U7: the PlanCanvas component and its controller in happy-dom (docs/upload/DESIGN.md U-12.1), with a recording 2D
// context and Path2D (happy-dom has neither): the tools, the pick modes, the keys, the hover tooltip (text only), the
// props drawn (selection, set-aside, highlight, area, overlay, flags), and the fallback without a canvas.
import { act, StrictMode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { decodePlan, PlanCanvas, type PlanCanvasProps } from '@/plan';
import { controllerOf, type PlanController } from '@/plan/controller';
import { DIM_VEIL, HIGHLIGHT, HIGHLIGHT_VEIL, ROLE_STROKE, SELECTED, SET_ASIDE } from '@/plan/colours';
import type { OverlayFloor, Flag } from '@/upload/contracts';
import { FakeCtx, FakePath, makePlan, type Item } from './kit';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const HOSTILE = '<img src=x onerror=alert(1)>';
const items: Item[] = [
  { key: 'B', layer: 'FURN', type: 5, pts: [[10, 10]] },
  { key: 'B/1', layer: 'FURN', type: 1, pts: [[10, 10], [11, 10], [11, 11], [10, 11]] },
  { key: 'B/2', layer: 'FURN', type: 0, pts: [[10.2, 10.5], [10.8, 10.5]] },
  { key: 'W1', layer: 'WALL', type: 0, pts: [[0, 0], [20, 0]] },
  { key: 'W2', layer: 'WALL', type: 0, pts: [[0, 20], [20, 20]] },
  { key: 'X', layer: HOSTILE, type: 0, pts: [[5, 5], [5, 8]] },
  { key: 'I', layer: 'DROP', type: 0, pts: [[15, 5], [15, 8]] },
];
const roles: Record<string, PlanCanvasProps extends { roleOf: (i: number) => infer R } ? R : never> = {
  FURN: 'furniture', WALL: 'wall', [HOSTILE]: 'other', DROP: 'ignore',
};

let restore: (() => void)[] = [];
let ctxs: FakeCtx[] = [];
let root: Root | null = null;
let host: HTMLDivElement | null = null;

function stubCanvas(): void {
  const proto = HTMLCanvasElement.prototype as unknown as { getContext: (t: string) => unknown };
  const getContext = proto.getContext;
  proto.getContext = function (t: string) { if (t !== '2d') return null; const c = new FakeCtx(); ctxs.push(c); return c; };
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

async function mount(extra: Partial<PlanCanvasProps> = {}, strict = true) {
  const plan = decodePlan(makePlan(items));
  const log: unknown[][] = [];
  const props: PlanCanvasProps = {
    plan, roleOf: i => roles[plan.layers[i]!] ?? 'other', selected: new Set(), setAside: new Set(), tool: 'select',
    onSelect: (keys, mode) => log.push(['select', keys, mode]), onPick: p => log.push(['pick', p]), onBox: b => log.push(['box', b]),
    onOpening: id => log.push(['opening', id]), onFlag: id => log.push(['flag', id]), onHover: info => log.push(['hover', info]),
    ...extra,
  };
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
  await act(async () => { root!.render(strict ? <StrictMode><PlanCanvas {...props} /></StrictMode> : <PlanCanvas {...props} />); });
  const canvas = host.querySelector('canvas')!;
  const ctl = controllerOf.get(canvas)!;
  const rerender = async (p: Partial<PlanCanvasProps>) => {
    Object.assign(props, p);
    await act(async () => { root!.render(strict ? <StrictMode><PlanCanvas {...props} /></StrictMode> : <PlanCanvas {...props} />); });
  };
  return { plan, props, log, canvas, ctl, rerender };
}

/** The screen point (CSS px) of a sheet point. */
const at = (ctl: PlanController, x: number, y: number) => ctl.sheetToScreen(x, y)!;
function pointer(canvas: HTMLCanvasElement, type: string, [x, y]: [number, number], init: PointerEventInit = {}): PointerEvent {
  const e = new PointerEvent(type, { clientX: x, clientY: y, button: 0, pointerId: 1, bubbles: true, cancelable: true, ...init });
  canvas.dispatchEvent(e);
  return e;
}
const clickAt = (canvas: HTMLCanvasElement, p: [number, number], init: PointerEventInit = {}) => {
  pointer(canvas, 'pointerdown', p, init);
  pointer(canvas, 'pointerup', p, init);
};
const drag = (canvas: HTMLCanvasElement, a: [number, number], b: [number, number], init: PointerEventInit = {}) => {
  pointer(canvas, 'pointerdown', a, init);
  pointer(canvas, 'pointermove', [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], { ...init, buttons: 1 });
  pointer(canvas, 'pointermove', b, { ...init, buttons: 1 });
  pointer(canvas, 'pointerup', b, init);
};
const key = (canvas: HTMLCanvasElement, k: string, init: KeyboardEventInit = {}) => {
  const e = new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true, ...init });
  canvas.dispatchEvent(e);
  return e;
};

beforeEach(() => { ctxs = []; });
afterEach(async () => {
  if (root) await act(async () => { root!.unmount(); });
  host?.remove();
  root = null; host = null;
  for (const f of restore.splice(0)) f();
});

describe('without a 2D canvas (happy-dom as it is)', () => {
  it('names the plan as text instead', async () => {
    const plan = decodePlan(makePlan(items));
    host = document.createElement('div');
    document.body.append(host);
    root = createRoot(host);
    await act(async () => { root!.render(<PlanCanvas plan={plan} roleOf={() => 'other'} selected={new Set()} setAside={new Set()} tool="pan" />); });
    expect(host.querySelector('canvas')).toBeNull();
    expect(host.querySelector('[data-plan-canvas="placeholder"]')?.textContent).toMatch(/^Plan of 7 items, 20\.0 x 20\.0 m/);
  });
});

describe('the canvas', () => {
  beforeEach(stubCanvas);

  it('one canvas, focusable, sized to its box at the device pixel ratio; the tooltip starts hidden; it draws once laid out', async () => {
    const { canvas, ctl } = await mount();
    expect(host!.querySelectorAll('canvas').length).toBe(1);
    expect(canvas.tabIndex).toBe(0);
    expect(canvas.getAttribute('aria-label')).toBe('Plan of 7 items, 20.0 x 20.0 m');
    expect([canvas.width, canvas.height]).toEqual([1000 * (window.devicePixelRatio || 1), 800 * (window.devicePixelRatio || 1)]);
    expect((host!.querySelector('[data-plan-tip]') as HTMLElement).hidden).toBe(true);
    expect(ctl.view!.s).toBeGreaterThan(0);
    expect(ctl.drawNow()).toBeGreaterThanOrEqual(0);
    expect(ctl.timing.frames).toBeGreaterThan(0);
  });

  it('StrictMode mounts twice: the first controller is disposed, one stays', async () => {
    const { canvas, ctl } = await mount({}, true);
    expect(controllerOf.get(canvas)).toBe(ctl);
    expect(ctxs.length).toBeGreaterThanOrEqual(1);
  });

  it('draws each layer in its role\'s colour as 1 device-pixel lines: walls dark, `ignore` faint', async () => {
    const { ctl } = await mount();
    const c = ctxs.at(-1)!;
    c.reset();
    const seen: [unknown, number, number][] = [];
    const stroke = c.stroke;
    c.stroke = (...a: unknown[]) => { if (a[0] instanceof FakePath) seen.push([c.strokeStyle, c.globalAlpha, c.lineWidth]); stroke(...a); };
    ctl.drawNow();
    const k = ctl.view!.s * ctl.dpr;                         // device pixels per quantum
    const wall = seen.find(x => x[0] === ROLE_STROKE.wall.colour)!, ign = seen.find(x => x[0] === ROLE_STROKE.ignore.colour)!;
    expect(wall[1]).toBe(1);
    expect(wall[2] * k).toBeCloseTo(1, 9);
    expect(ign[1]).toBe(ROLE_STROKE.ignore.alpha);
    expect(seen.find(x => x[0] === ROLE_STROKE.furniture.colour)).toBeTruthy();
    expect(seen.find(x => x[0] === ROLE_STROKE.other.colour)![1]).toBe(ROLE_STROKE.other.alpha);
  });

  it('select tool: a click picks the nearest item; shift adds, ctrl toggles; empty space clears', async () => {
    const { canvas, ctl, log, rerender } = await mount();
    clickAt(canvas, at(ctl, 10, 0));
    expect(log.at(-1)).toEqual(['select', ['W1'], 'replace']);
    clickAt(canvas, at(ctl, 10, 20), { shiftKey: true });
    expect(log.at(-1)).toEqual(['select', ['W2'], 'add']);
    clickAt(canvas, at(ctl, 5, 6), { ctrlKey: true });
    expect(log.at(-1)).toEqual(['select', ['X'], 'toggle']);
    await rerender({ selected: new Set(['W1']) });
    clickAt(canvas, at(ctl, 12, 13));
    expect(log.at(-1)).toEqual(['select', [], 'replace']);
  });

  it('block mode: a line of a block selects the block\'s anchor', async () => {
    const { canvas, ctl, log } = await mount({ pick: 'block' });
    clickAt(canvas, at(ctl, 10.5, 10.5));
    expect(log.at(-1)).toEqual(['select', ['B'], 'replace']);
  });

  it('a drag box selects the items wholly inside; alt: touched; layer-in-box: the clicked item\'s layer only', async () => {
    const { canvas, ctl, log, rerender } = await mount();
    drag(canvas, at(ctl, 9, 12), at(ctl, 16, 4));
    expect(log.at(-1)).toEqual(['select', ['B/1', 'B/2', 'I'], 'replace']);
    drag(canvas, at(ctl, 9, 12), at(ctl, 16, 6), { altKey: true });
    expect(log.at(-1)).toEqual(['select', ['B/1', 'B/2', 'I'], 'replace']);
    drag(canvas, at(ctl, 9, 12), at(ctl, 16, 6));
    expect(log.at(-1)).toEqual(['select', ['B/1', 'B/2'], 'replace']);
    await rerender({ pick: 'layer-in-box' });
    clickAt(canvas, at(ctl, 15, 6));                       // remembers DROP
    expect(log.at(-1)).toEqual(['select', ['I'], 'replace']);
    drag(canvas, at(ctl, 4, 12), at(ctl, 16, 4));
    expect(log.at(-1)).toEqual(['select', ['I'], 'replace']);
    drag(canvas, at(ctl, 11.05, 11.05), at(ctl, 9.5, 9.5)); // started on a FURN line: that layer now
    expect(log.at(-1)).toEqual(['select', ['B/1', 'B/2'], 'replace']);
  });

  it('draw-box: a drag reports the box in sheet metres, ordered; pick-point: a click reports the point snapped to a vertex', async () => {
    const { canvas, ctl, log, rerender } = await mount({ tool: 'draw-box' });
    drag(canvas, at(ctl, 12, 3), at(ctl, 2, 9));
    const box = log.at(-1)![1] as number[];
    expect(log.at(-1)![0]).toBe('box');
    expect(box[0]).toBeCloseTo(2, 1); expect(box[1]).toBeCloseTo(3, 1); expect(box[2]).toBeCloseTo(12, 1); expect(box[3]).toBeCloseTo(9, 1);
    await rerender({ tool: 'pick-point' });
    const [x, y] = at(ctl, 11, 11);
    clickAt(canvas, [x + 2, y - 2]);
    expect(log.at(-1)).toEqual(['pick', [11, 11]]);
    clickAt(canvas, at(ctl, 13, 13));
    expect((log.at(-1)![1] as number[])[0]).toBeCloseTo(13, 1);
    expect(canvas.style.cursor).toBe('crosshair');
  });

  it('pan tool: a drag pans; the wheel zooms at the pointer; neither selects', async () => {
    const { canvas, ctl, log } = await mount({ tool: 'pan' });
    expect(canvas.style.cursor).toBe('grab');
    const v0 = { ...ctl.view! };
    drag(canvas, [500, 400], [600, 350]);
    expect(ctl.view!.s).toBe(v0.s);
    const [x] = at(ctl, v0.cx * 0.01, v0.cy * 0.01);
    expect(x).toBeCloseTo(600, 6);
    const p = at(ctl, 10, 10);
    const e = new WheelEvent('wheel', { clientX: p[0], clientY: p[1], deltaY: -100, bubbles: true, cancelable: true });
    for (const [k, v] of [['clientX', p[0]], ['clientY', p[1]], ['deltaMode', 0]] as const) {
      if (typeof (e as unknown as Record<string, unknown>)[k] !== 'number') Object.defineProperty(e, k, { value: v });   // happy-dom
    }
    canvas.dispatchEvent(e);
    expect(e.defaultPrevented).toBe(true);
    expect(ctl.view!.s).toBeGreaterThan(v0.s);
    const q = at(ctl, 10, 10);
    expect(q[0]).toBeCloseTo(p[0], 6); expect(q[1]).toBeCloseTo(p[1], 6);
    expect(log.filter(l => l[0] === 'select')).toEqual([]);
  });

  it('keys: arrows pan, + / - zoom, F fits, Esc clears the selection; Delete is left to the page', async () => {
    const { canvas, ctl, log, rerender } = await mount({ selected: new Set(['W1']) });
    const v0 = { ...ctl.view! };
    expect(key(canvas, 'ArrowLeft').defaultPrevented).toBe(true);
    expect(ctl.view!.cx).toBeLessThan(v0.cx);
    key(canvas, '+');
    expect(ctl.view!.s).toBeGreaterThan(v0.s);
    key(canvas, 'f');
    expect(ctl.view).toEqual(v0);
    key(canvas, 'Escape');
    expect(log.at(-1)).toEqual(['select', [], 'replace']);
    let bubbled = false;
    host!.addEventListener('keydown', e => { if (e.key === 'Delete') bubbled = true; });
    const del = key(canvas, 'Delete');
    expect(del.defaultPrevented).toBe(false);
    expect(bubbled).toBe(true);
    await rerender({ selected: new Set() });
    const before = log.length;
    key(canvas, 'Escape');
    expect(log.length).toBe(before);              // nothing selected: nothing to clear
  });

  it('hover: the item under the pointer is reported and named in the tooltip, as text (a hostile layer name stays text)', async () => {
    const { canvas, ctl, log } = await mount();
    pointer(canvas, 'pointermove', at(ctl, 5, 6.5));
    await act(async () => { await new Promise(r => setTimeout(r, 40)); });
    expect(log.filter(l => l[0] === 'hover').at(-1)).toEqual(['hover', { layer: HOSTILE, type: 0, key: 'X' }]);
    const tip = host!.querySelector('[data-plan-tip]') as HTMLElement;
    expect(tip.hidden).toBe(false);
    expect(tip.textContent).toBe(`${HOSTILE}\nline · X`);
    expect(tip.querySelector('img')).toBeNull();
    expect(document.querySelector('img')).toBeNull();
    pointer(canvas, 'pointermove', at(ctl, 12, 13));
    await act(async () => { await new Promise(r => setTimeout(r, 40)); });
    expect(log.filter(l => l[0] === 'hover').at(-1)).toEqual(['hover', null]);
    expect(tip.hidden).toBe(true);
  });

  it('draws the selection, the set-aside items crossed, the highlighted layer over a veil, the area lit', async () => {
    const plan = decodePlan(makePlan(items));
    const { ctl, rerender } = await mount();
    await rerender({ selected: new Set(['B']), setAside: new Set(['W2']), highlightLayer: plan.layers.indexOf('WALL'),
      area: { kind: 'box', bbox: [8, 8, 12, 12], pad: 0.5, match: 'all' } });
    const c = ctxs.at(-1)!;
    c.reset();
    const strokeStyles: unknown[] = [];
    const fills: unknown[] = [];
    const stroke = c.stroke, fill = c.fill, fillRect = c.fillRect;
    c.stroke = (...a: unknown[]) => { strokeStyles.push(c.strokeStyle); stroke(...a); };
    c.fill = (...a: unknown[]) => { fills.push([c.fillStyle, ...a]); fill(...a); };
    c.fillRect = (...a: unknown[]) => { fills.push([c.fillStyle]); fillRect(...a); };
    ctl.drawNow();
    expect(strokeStyles).toContain(SELECTED.colour);
    expect(strokeStyles).toContain(SET_ASIDE.colour);
    expect(strokeStyles).toContain(HIGHLIGHT.colour);
    expect(strokeStyles).toContain(ROLE_STROKE.wall.colour);
    expect(strokeStyles).toContain(ROLE_STROKE.ignore.colour);
    expect(fills).toContainEqual([HIGHLIGHT_VEIL]);
    expect(fills).toContainEqual([DIM_VEIL, 'evenodd']);
  });

  it('the overlay: room names and opening numbers as canvas text; an opening and a flag are clicked before the items', async () => {
    const overlay: OverlayFloor = {
      key: 'L1', source: 'a'.repeat(40), toSheet: [0, 0], area: { kind: 'wholeFile' },
      parts: [{ i: 0, kind: 'wall', label: null, o: [[0, -0.1], [20, -0.1], [20, 0.1], [0, 0.1]], h: [] }],
      slabs: [{ o: [[0, 0], [20, 0], [20, 20], [0, 20]], h: [] }],
      openings: [{ id: 'L1-007', kind: 'door', a: [2, 20], b: [4, 20], flagged: true, fixed: false }],
      furniture: [{ id: 'f1', kind: 'seat', x: 10.5, y: 10.5, w: 1, d: 1, rot: 30 }],
      rooms: [{ name: HOSTILE, x: 6, y: 15 }], setAside: ['I'],
    };
    const flags: Flag[] = [
      { id: 'opening:L1:aaaaaaaaaaaa', kind: 'opening', floor: 'L1', severity: 'check', title: 'L1-007: door to check', detail: '', at: [17, 17], bbox: null, ref: { openingId: 'L1-007' } },
      { id: 'units:x', kind: 'units', floor: 'L2', severity: 'check', title: 'other floor', detail: '', at: [1, 1], bbox: null, ref: {} },
    ];
    const { canvas, ctl, log } = await mount({ overlay, flags });
    const c = ctxs.at(-1)!;
    c.reset();
    ctl.drawNow();
    expect(c.texts).toContain(HOSTILE);
    expect(c.texts).toContain('007');
    clickAt(canvas, at(ctl, 3, 20));
    expect(log.at(-1)).toEqual(['opening', 'L1-007']);
    clickAt(canvas, at(ctl, 17, 17));
    expect(log.at(-1)).toEqual(['flag', 'opening:L1:aaaaaaaaaaaa']);
    clickAt(canvas, at(ctl, 1, 0.05));                  // the other floor's flag (at 1, 1) is not on this sheet: W1 is picked
    expect(log.at(-1)).toEqual(['select', ['W1'], 'replace']);
    expect(document.querySelector('img')).toBeNull();
  });

  it('focus: the view fits the box whenever its value changes', async () => {
    const { ctl, rerender } = await mount();
    await rerender({ focus: [10, 10, 11, 11] });
    const s1 = ctl.view!.s;
    expect(ctl.view!.cx).toBeCloseTo(1050, 6);
    await rerender({ focus: [10, 10, 11, 11] });          // a new array with the same value: no jump
    expect(ctl.view!.s).toBe(s1);
    await rerender({ focus: [0, 0, 20, 20] });
    expect(ctl.view!.s).toBeLessThan(s1);
  });

  it('unmounting removes the controller and its listeners', async () => {
    const { canvas, ctl, log } = await mount();
    await act(async () => { root!.unmount(); });
    root = null;
    expect(controllerOf.get(canvas)).toBeUndefined();
    const n = log.length;
    clickAt(canvas, [500, 400]);
    expect(log.length).toBe(n);
    expect(ctl.drawNow()).toBe(0);
  });
});

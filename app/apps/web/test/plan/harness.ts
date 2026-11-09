// The plan canvas harness (docs/upload/ACCEPTANCE.md 2.4 U7; tests/e2e/plan-canvas.spec.ts). Owner U7. Served by the web
// dev server at /test/plan/harness.html. It mounts the real PlanCanvas over the whole page on a fixture plan
// (fixtures/upload/plan/{bank1,sukhumvit}.plan.json.gz) with the roles of fixtures/upload/settings/{bank,house}.json,
// keeps a selection the way the check screen does (onSelect replace / add / toggle), and exposes window.__planHarness:
//   load(name)              decode and show a fixture plan (tool 'select', pick 'item'); resolves after a frame is drawn
//   set(changes)            new props (tool, pick, highlight (a layer name), area (a floor key of the settings), overlay
//                           (a floor key of fixtures/upload/overlay/bank.overlay.json, with its flags), selected, setAside,
//                           focus, diff); resolves after a frame is drawn
//   info()                  plan, view, size, device pixel ratio, backing store, frames drawn
//   toPage(x, y)            the page pixel (CSS) of a sheet point; toSheet(px, py) the reverse
//   pixels(x, y, r)         the canvas's device pixels round a sheet point ((2r + 1)^2 of [r, g, b, a])
//   timeRedraw(n)           n frames drawn now, each followed by a one-pixel read-back (the work done): ms per frame
//   events, selected()      what the callbacks reported, the selection now
import { createElement, useEffect, useState, type JSX } from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { decodePlan, PlanCanvas, type DecodedPlan, type PickMode, type PlanCanvasProps } from '@/plan';
import { controllerOf } from '@/plan/controller';
import type { Bbox, BuildOverlay, BuildSettings, DiffBody, FloorArea, LayerRole, PlanGeometry } from '@/upload/contracts';
import bankPlanUrl from '../../../../fixtures/upload/plan/bank1.plan.json.gz?url';
import housePlanUrl from '../../../../fixtures/upload/plan/sukhumvit.plan.json.gz?url';
import bankOverlayJson from '../../../../fixtures/upload/overlay/bank.overlay.json';
import bankSettingsJson from '../../../../fixtures/upload/settings/bank.json';
import houseSettingsJson from '../../../../fixtures/upload/settings/house.json';

type Name = 'bank1' | 'sukhumvit';
const PLANS: Record<Name, { url: string; settings: BuildSettings }> = {
  bank1: { url: bankPlanUrl, settings: bankSettingsJson as unknown as BuildSettings },
  sukhumvit: { url: housePlanUrl, settings: houseSettingsJson as unknown as BuildSettings },
};
const OVERLAY = bankOverlayJson as unknown as BuildOverlay;

export interface Changes {
  tool?: PlanCanvasProps['tool'];
  pick?: PickMode;
  highlight?: string | null;
  area?: string | FloorArea | null;
  overlay?: string | null;
  selected?: string[];
  setAside?: string[];
  focus?: Bbox | null;
  diff?: DiffBody | null;
}

interface HarnessEvent { type: string; [k: string]: unknown }

async function fetchPlan(url: string): Promise<PlanGeometry> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  let text: string;
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    text = await new Response(stream).text();
  } else {
    text = new TextDecoder().decode(bytes);
  }
  return JSON.parse(text) as PlanGeometry;
}

const frames = (n = 2) => new Promise<void>(resolve => {
  const step = (k: number) => (k <= 0 ? resolve() : requestAnimationFrame(() => step(k - 1)));
  step(n);
});

let setState: ((p: PlanCanvasProps | null) => void) | null = null;
let current: PlanCanvasProps | null = null;
let settings: BuildSettings | null = null;
const events: HarnessEvent[] = [];

function Harness(): JSX.Element | null {
  const [props, set] = useState<PlanCanvasProps | null>(null);
  setState = set;
  useEffect(() => { harness.ready = true; }, []);
  return props ? createElement(PlanCanvas, props) : null;
}

function canvas(): HTMLCanvasElement {
  const c = document.querySelector<HTMLCanvasElement>('[data-plan-canvas=canvas] canvas');
  if (!c) throw new Error('no plan canvas on the page');
  return c;
}
const controller = () => {
  const c = controllerOf.get(canvas());
  if (!c) throw new Error('no controller for the plan canvas');
  return c;
};

function render(p: PlanCanvasProps): void {
  current = p;
  flushSync(() => setState!(p));
}

function applySelect(keys: string[], mode: 'replace' | 'add' | 'toggle'): void {
  events.push({ type: 'select', keys, mode });
  if (!current) return;
  const next = new Set(mode === 'replace' ? [] : current.selected);
  for (const k of keys) {
    if (mode === 'toggle' && next.has(k)) next.delete(k); else next.add(k);
  }
  render({ ...current, selected: next });
}

function baseProps(plan: DecodedPlan, roles: Record<string, LayerRole>): PlanCanvasProps {
  return {
    plan,
    roleOf: i => roles[plan.layers[i]!] ?? 'other',
    selected: new Set(), setAside: new Set(), tool: 'select', pick: 'item',
    onSelect: (keys, mode) => applySelect(keys, mode),
    onPick: p => { events.push({ type: 'pick', p }); },
    onBox: b => { events.push({ type: 'box', bbox: b }); },
    onOpening: id => { events.push({ type: 'opening', id }); },
    onFlag: id => { events.push({ type: 'flag', id }); },
    onHover: info => { events.push({ type: 'hover', info }); },
  };
}

const harness = {
  ready: false,
  stub: false,
  error: null as string | null,
  events,
  clearEvents() { events.length = 0; },
  async load(name: Name) {
    const spec = PLANS[name];
    if (!spec) throw new Error(`no fixture plan ${String(name)}`);
    const plan = decodePlan(await fetchPlan(spec.url));
    settings = spec.settings;
    events.length = 0;
    render(baseProps(plan, settings.layers));
    await frames(3);
    return harness.info();
  },
  async set(c: Changes) {
    if (!current || !settings) throw new Error('load a plan first');
    const p: PlanCanvasProps = { ...current };
    if (c.tool !== undefined) p.tool = c.tool;
    if (c.pick !== undefined) p.pick = c.pick;
    if (c.highlight !== undefined) {
      const i = c.highlight === null ? -1 : p.plan.layers.indexOf(c.highlight);
      if (c.highlight !== null && i < 0) throw new Error(`no layer ${c.highlight}`);
      p.highlightLayer = i < 0 ? null : i;
    }
    if (c.area !== undefined) {
      p.area = typeof c.area === 'string' ? settings.floors.find(f => f.key === c.area)?.area ?? null : c.area;
    }
    if (c.overlay !== undefined) {
      p.overlay = c.overlay === null ? null : OVERLAY.floors.find(f => f.key === c.overlay) ?? null;
      p.flags = c.overlay === null ? [] : OVERLAY.flags;
    }
    if (c.selected) p.selected = new Set(c.selected);
    if (c.setAside) p.setAside = new Set(c.setAside);
    if (c.focus !== undefined) p.focus = c.focus;
    if (c.diff !== undefined) p.diff = c.diff;
    render(p);
    await frames(2);
    return harness.info();
  },
  selected: () => [...(current?.selected ?? [])],
  info() {
    const ctl = controller(), c = canvas(), r = c.getBoundingClientRect();
    return {
      count: ctl.data.n, layers: ctl.data.layerNames.length, origin: ctl.data.origin, view: ctl.view, size: ctl.size, dpr: ctl.dpr,
      backing: [c.width, c.height], rect: [r.left, r.top, r.width, r.height], frames: ctl.timing.frames, lastMs: ctl.timing.lastMs,
    };
  },
  toPage(x: number, y: number): [number, number] | null {
    const s = controller().sheetToScreen(x, y);
    if (!s) return null;
    const r = canvas().getBoundingClientRect();
    return [r.left + s[0], r.top + s[1]];
  },
  toSheet(px: number, py: number) {
    const r = canvas().getBoundingClientRect();
    return controller().screenToSheet(px - r.left, py - r.top);
  },
  pixels(x: number, y: number, r = 3): number[][] | null {
    const ctl = controller(), s = ctl.sheetToScreen(x, y);
    if (!s) return null;
    const c = canvas(), ctx = c.getContext('2d')!;
    const cx = Math.round(s[0] * ctl.dpr), cy = Math.round(s[1] * ctl.dpr);
    if (cx - r < 0 || cy - r < 0 || cx + r >= c.width || cy + r >= c.height) return null;
    const img = ctx.getImageData(cx - r, cy - r, 2 * r + 1, 2 * r + 1).data;
    const out: number[][] = [];
    for (let i = 0; i < img.length; i += 4) out.push([img[i]!, img[i + 1]!, img[i + 2]!, img[i + 3]!]);
    return out;
  },
  timeRedraw(n = 5): number[] {
    const ctl = controller(), ctx = canvas().getContext('2d')!;
    const out: number[] = [];
    for (let i = 0; i < n; i++) {
      const t0 = performance.now();
      ctl.drawNow();
      ctx.getImageData(0, 0, 1, 1);
      out.push(Math.round((performance.now() - t0) * 100) / 100);
    }
    return out;
  },
  fit() { controller().fit(); return frames(2); },
};

declare global { interface Window { __planHarness: typeof harness } }
window.__planHarness = harness;

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(createElement(Harness));
}
window.addEventListener('error', e => { harness.error = String(e.message); });

// The plan canvas's controller (docs/upload/DESIGN.md U-12.1): one <canvas> (device-pixel-ratio aware), the caches
// (one Path2D per (layer, type), built once; the grid index; the overlay, flags and diff in the local frame), the input
// (pan by drag and arrows, zoom by the wheel at the pointer and +/-, fit, the tools and pick modes, Esc), the hover
// tooltip (text only), and a redraw on requestAnimationFrame only when something changed. Owner U7.
// Delete is not handled here: the key bubbles to the page, whose check step sets the selection aside (PlanCanvasProps
// has no set-aside callback; U7.md).
// The rooms milestone (docs/rooms/DESIGN.md R-6.2, R-6.4, R-12.6; R6): the tools 'draw-line' (two clicks, each end
// snapped as 'pick-point' snaps; Esc or a tool change drops the first end) and 'rooms' (a click goes to a stair, then to
// one of the app's closings, then to a room, else reports the point), `show`, the rooms' area in the hover text, and
// the test hook `window.__plan` (testHook()).
import type { Vec2 } from '@walkthrough/viewer';
import type { Bbox, LayerRole } from '@/upload/contracts';
import { coveredBox, coveredEntries, isAnchor, planData, TYPE_NAMES, type PlanData, type QBox } from './decode';
import { drawFrame, type Ctx, type Scene } from './draw';
import { d2Polyline, polyContains, ringBox, ringContains } from './geom';
import { boxKeys, buildGrid, clickKey, dist2PointSegment, entriesInBox, nearest, type Grid, type Mode } from './hit';
import type { PlanCanvasProps, PlanShow, PlanTestHook } from './index';
import { areaBox, localBox, localDiff, localFlags, localOverlay, type LocalOverlay, type LocalSpace } from './overlay';
import { buildLayerPaths, pathOfEntries, textAnchors, type LayerPath, type PathSink } from './paths';
import { boxFromScreen, clamp, fitView, panBy, sameView, scaleLimits, toLocal, toScreen, wheelFactor, zoomAt, type Size, type View } from './view';
import { FLAG_RADIUS } from './colours';

/** Pick radius in screen pixels (U-12.1: "the nearest item within 6 px"). */
export const PICK_PX = 6;
/** A press that moves less than this is a click. */
export const DRAG_PX = 4;

/** The controller of each live canvas (the harness and the tests reach it through its canvas; nothing else does). */
export const controllerOf = new WeakMap<HTMLCanvasElement, PlanController>();

type P = Path2D | PathSink;

interface Drag {
  id: number;
  kind: 'press' | 'pan' | 'box';
  button: number;
  x0: number; y0: number; x: number; y: number;
  /** The item under the press (layer-in-box takes its layer). */
  pressLayer: number | null;
  shift: boolean; alt: boolean; ctrl: boolean;
  view0: View;
}

export interface Timing { lastMs: number; frames: number }

export class PlanController {
  readonly canvas: HTMLCanvasElement;
  readonly tip: HTMLElement | null;
  private readonly ctx: Ctx | null;
  private readonly makePath: () => P;
  props: PlanCanvasProps;
  data: PlanData;
  view: View | null = null;
  size: Size = { w: 0, h: 0 };
  dpr = 1;
  timing: Timing = { lastMs: 0, frames: 0 };
  private grid: Grid | null | undefined;
  private paths: LayerPath<P>[] | null = null;
  private texts = new Map<number, number[]>();
  private roles: LayerRole[] = [];
  private scene: Omit<Scene<P>, 'data' | 'paths' | 'texts' | 'roles' | 'band' | 'pickMark' | 'lineStart' | 'lineEnd'> = {
    area: null, highlight: null, overlay: null, flags: [], diff: null, selected: null, selectedBoxes: [], setAside: null,
    setAsideBoxes: [], builtAside: null, builtAsideBoxes: [], show: SHOW_ALL,
  };
  private drag: Drag | null = null;
  private band: [number, number, number, number] | null = null;
  private pickMark: [number, number] | null = null;
  /** The tool 'draw-line': its first end (quanta) after the first click, and where the pointer is. */
  private lineStart: [number, number] | null = null;
  private lineEnd: [number, number] | null = null;
  private lastLayer: number | null = null;
  private hoverAt: [number, number] | null = null;
  private hoverKey = '';
  private raf = 0;
  private hoverRaf = 0;
  private focusSig = '';
  /** RR (S7): the box the first view and Fit show when the canvas has an overlay: that floor's own plate and parts (or
   *  its area) with a margin, not the whole sheet (a DWG may hold every floor and the elevations); null: the sheet. */
  private home: QBox | null = null;
  /** The overlay floor the view was last fitted for: another floor of the same sheet fits again. */
  private homeKey: string | null = null;
  private wantFit = true;
  private disposed = false;
  private readonly off: (() => void)[] = [];

  constructor(canvas: HTMLCanvasElement, tip: HTMLElement | null, props: PlanCanvasProps, ctx: Ctx | null, makePath?: () => P) {
    this.canvas = canvas;
    this.tip = tip;
    this.ctx = ctx;
    this.makePath = makePath ?? (() => new Path2D());
    this.props = props;
    this.data = planData(props.plan);
    controllerOf.set(canvas, this);
    this.listen();
    this.update(props, null);
  }

  // ------------------------------------------------------------------------------------------------------ props
  /** New props from React: rebuilds what changed, then one redraw. */
  setProps(next: PlanCanvasProps): void {
    const prev = this.props;
    this.props = next;
    this.update(next, prev);
  }

  private update(p: PlanCanvasProps, prev: PlanCanvasProps | null): void {
    const planChanged = !prev || prev.plan !== p.plan;
    if (planChanged) {
      this.data = planData(p.plan);
      this.grid = undefined;
      this.paths = null;
      this.texts = textAnchors(this.data);
      this.lastLayer = null;
      this.pickMark = null;
      this.wantFit = true;
      this.focusSig = '';
    }
    const d = this.data;
    const roles = d.layerNames.map((_, i) => p.roleOf(i));
    const rolesChanged = roles.length !== this.roles.length || roles.some((r, i) => r !== this.roles[i]);
    this.roles = roles;
    let dirty = planChanged || rolesChanged;
    const sc = this.scene;
    if (planChanged || prev!.area !== p.area) { sc.area = areaBox(d, p.area); dirty = true; }
    const hl = p.highlightLayer ?? null;
    const remembered = p.pick === 'layer-in-box' && hl === null ? this.lastLayer : null;
    if ((hl ?? remembered) !== sc.highlight) { sc.highlight = hl ?? remembered; dirty = true; }
    if (planChanged || prev!.overlay !== p.overlay) {
      sc.overlay = p.overlay ? localOverlay(d, p.overlay) : null;
      const [path, boxes] = this.asidePath(sc.overlay?.setAside ?? []);
      sc.builtAside = path; sc.builtAsideBoxes = boxes;
      dirty = true;
    }
    if (planChanged || prev!.overlay !== p.overlay || prev!.area !== p.area) {
      this.home = sc.overlay ? homeBoxOf(d, sc.overlay, sc.area) : null;
      // the first overlay, or another floor of the same sheet: fit again (a new overlay of the same floor, after a
      // Rebuild or a fix mark, keeps the view)
      const hk = p.overlay?.key ?? null;
      if (hk !== this.homeKey) { this.homeKey = hk; if (hk !== null && !p.focus) this.wantFit = true; }
    }
    if (planChanged || prev!.overlay !== p.overlay || prev!.flags !== p.flags) { sc.flags = localFlags(d, p.flags, p.overlay?.key ?? null); dirty = true; }
    if (planChanged || prev!.overlay !== p.overlay || prev!.diff !== p.diff) { sc.diff = p.diff ? localDiff(d, p.diff, p.overlay?.key ?? null) : null; dirty = true; }
    if (planChanged || prev!.selected !== p.selected) {
      const entries: number[] = [], boxes: QBox[] = [];
      for (const k of p.selected) {
        for (const e of coveredEntries(d, k)) entries.push(e);
        if (isAnchor(d, k)) { const b = coveredBox(d, k); if (b) boxes.push(b); }
      }
      sc.selected = entries.length ? pathOfEntries(d, entries, this.makePath) : null;
      sc.selectedBoxes = boxes;
      dirty = true;
    }
    if (planChanged || prev!.setAside !== p.setAside) {
      const [path, boxes] = this.asidePath([...p.setAside]);
      sc.setAside = path; sc.setAsideBoxes = boxes;
      dirty = true;
    }
    const show = showOf(p.show);
    if (!sameShow(show, sc.show)) { sc.show = show; dirty = true; }
    if (!prev || prev.tool !== p.tool) {
      this.canvas.style.cursor = cursorOf(p.tool);
      this.cancelDrag();
      if (this.lineStart) { this.lineStart = this.lineEnd = null; dirty = true; }
    }
    const fsig = p.focus ? p.focus.join(',') : '';
    if (fsig !== this.focusSig) { this.focusSig = fsig; if (p.focus) this.wantFit = true; }
    if (this.wantFit) dirty = this.fitNow() || dirty;
    if (dirty) this.requestDraw();
  }

  private asidePath(keys: readonly string[]): [P | null, QBox[]] {
    const d = this.data, entries: number[] = [], boxes: QBox[] = [];
    for (const k of keys) {
      const es = coveredEntries(d, k);
      for (const e of es) entries.push(e);
      const b = coveredBox(d, k);
      if (b) boxes.push(b);
    }
    return [entries.length ? pathOfEntries(d, entries, this.makePath) : null, boxes];
  }

  // ------------------------------------------------------------------------------------------------------ view
  /** Fits the view to the focus box, else the plan; true when it could (the canvas has a size). */
  private fitNow(): boolean {
    if (this.size.w <= 0 || this.size.h <= 0) return false;
    const focus = this.props.focus ? localBox(this.data, this.props.focus) : null;
    const box = focus ?? this.home ?? this.data.fitBox;
    this.view = box ? fitView(box, this.size) : { cx: 0, cy: 0, s: 0.5 };
    this.wantFit = false;
    return true;
  }

  /** F, 0, Home and the page's Fit button: the overlay's floor when there is one (RR, S7), else the sheet. */
  fit(): void {
    const box = this.home ?? this.data.fitBox;
    this.view = box ? fitView(box, this.size) : this.view;
    this.requestDraw();
  }

  /** The canvas's CSS size and the device pixel ratio; resizes the backing store. Keeps the view's middle and scale. */
  resize(w: number, h: number, dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1): void {
    w = Math.max(0, Math.round(w)); h = Math.max(0, Math.round(h));
    if (w === this.size.w && h === this.size.h && dpr === this.dpr) return;
    this.size = { w, h };
    this.dpr = dpr;
    this.canvas.width = Math.max(1, Math.round(w * dpr));
    this.canvas.height = Math.max(1, Math.round(h * dpr));
    if (this.wantFit || !this.view) this.fitNow();
    this.requestDraw();
  }

  setView(v: View): void {
    const lim = scaleLimits(this.data.bounds, this.size);
    const nv = { cx: v.cx, cy: v.cy, s: clamp(v.s, lim.min, lim.max) };
    if (this.view && sameView(this.view, nv)) return;
    this.view = nv;
    this.requestDraw();
  }

  /** Screen pixels (CSS, from the canvas's corner) of a sheet point. */
  sheetToScreen(x: number, y: number): [number, number] | null {
    if (!this.view) return null;
    const [qx, qy] = this.data.toLocal(x, y);
    return toScreen(this.view, this.size, qx, qy);
  }

  screenToSheet(px: number, py: number): Vec2 | null {
    if (!this.view) return null;
    const [qx, qy] = toLocal(this.view, this.size, px, py);
    return this.data.toSheet(qx, qy);
  }

  // ------------------------------------------------------------------------------------------------------ drawing
  requestDraw(): void {
    if (this.raf || this.disposed || !this.ctx) return;
    if (typeof requestAnimationFrame !== 'function') { this.drawNow(); return; }
    this.raf = requestAnimationFrame(() => { this.raf = 0; this.drawNow(); });
  }

  /** Draws one frame now; returns its time in ms (the U-12.1 budget is measured on this). */
  drawNow(): number {
    if (!this.ctx || !this.view || this.disposed) return 0;
    const t0 = performance.now();
    if (!this.paths) this.paths = buildLayerPaths(this.data, this.makePath);
    const sc: Scene<P> = {
      ...this.scene, data: this.data, paths: this.paths, texts: this.texts, roles: this.roles, band: this.band, pickMark: this.pickMark,
      lineStart: this.lineStart, lineEnd: this.lineEnd,
    };
    drawFrame(this.ctx, sc, this.view, this.size, this.dpr, DRAW);
    const ms = performance.now() - t0;
    this.timing = { lastMs: ms, frames: this.timing.frames + 1 };
    return ms;
  }

  // ------------------------------------------------------------------------------------------------------ picking
  private gridNow(): Grid | null {
    if (this.grid === undefined) this.grid = buildGrid(this.data);
    return this.grid;
  }

  /** The drawn entry within PICK_PX of a screen point, or -1. */
  entryAt(px: number, py: number): number {
    if (!this.view) return -1;
    const [qx, qy] = toLocal(this.view, this.size, px, py);
    return nearest(this.data, this.gridNow(), qx, qy, PICK_PX / this.view.s)?.entry ?? -1;
  }

  private flagAt(px: number, py: number): string | null {
    if (!this.view) return null;
    let best: string | null = null, bestD = FLAG_RADIUS + 4;
    for (const f of this.scene.flags) {
      const [x, y] = toScreen(this.view, this.size, f.at[0], f.at[1]);
      const dd = Math.hypot(x - px, y - py);
      if (dd <= bestD) { best = f.id; bestD = dd; }
    }
    return best;
  }

  private openingAt(px: number, py: number): string | null {
    const ov = this.scene.overlay;
    if (!ov || !this.view) return null;
    const [qx, qy] = toLocal(this.view, this.size, px, py);
    const r = PICK_PX / this.view.s;
    let best: string | null = null, bestD = r * r;
    for (const o of ov.openings) {
      const dd = dist2PointSegment(qx, qy, o.a[0], o.a[1], o.b[0], o.b[1]);
      if (dd <= bestD) { best = o.id; bestD = dd; }
    }
    return best;
  }

  /** The nearest drawn vertex within PICK_PX (pick-point snaps to it), else the point itself; quanta. */
  private snap(px: number, py: number): [number, number] {
    const v = this.view!;
    const [qx, qy] = toLocal(v, this.size, px, py);
    const r = PICK_PX / v.s;
    const hit = nearest(this.data, this.gridNow(), qx, qy, r);
    if (!hit) return [qx, qy];
    const d = this.data, f = d.first[hit.entry]!, c = d.count[hit.entry]!;
    let best: [number, number] = [qx, qy], bestD = r * r;
    for (let k = f; k < f + c; k++) {
      const x = d.pts[2 * k]!, y = d.pts[2 * k + 1]!, dd = (x - qx) ** 2 + (y - qy) ** 2;
      if (dd <= bestD) { best = [x, y]; bestD = dd; }
    }
    return best;
  }

  // ------------------------------------------------------------------------------------------- rooms milestone picks
  /** The stair under a local point: its outline holds it, or its outline or walking line is within PICK_PX. */
  stairAt(qx: number, qy: number): string | null {
    const ov = this.scene.overlay;
    if (!ov || !this.view) return null;
    const r2 = (PICK_PX / this.view.s) ** 2;
    let best: string | null = null, bestD = Infinity;
    for (const st of ov.stairs) {
      if (ringContains(st.outline, qx, qy)) return st.id;
      const ring = [...st.outline, st.outline[0]!, st.outline[1]!];
      const d = Math.min(d2Polyline(ring, qx, qy), st.walk ? d2Polyline(st.walk, qx, qy) : Infinity);
      if (d <= r2 && d < bestD) { best = st.id; bestD = d; }
    }
    return best;
  }

  /** The index (in overlay.closings) of the app's closing (a bridge or a doorway closing, not a staff line) within
   *  PICK_PX of a local point. */
  closingAt(qx: number, qy: number): number | null {
    const ov = this.scene.overlay;
    if (!ov || !this.view) return null;
    const r2 = (PICK_PX / this.view.s) ** 2;
    let best: number | null = null, bestD = r2;
    for (const c of ov.closings) {
      if (c.kind === 'staff') continue;
      const d = dist2PointSegment(qx, qy, c.a[0], c.a[1], c.b[0], c.b[1]);
      if (d <= bestD) { best = c.index; bestD = d; }
    }
    return best;
  }

  /** The room (overlay space) that holds a local point. */
  spaceAt(qx: number, qy: number): LocalSpace | null {
    const ov = this.scene.overlay;
    if (!ov) return null;
    for (const r of ov.spaces) {
      if (qx < r.box[0] || qx > r.box[2] || qy < r.box[1] || qy > r.box[3]) continue;
      if (polyContains(r.o, r.h, qx, qy)) return r;
    }
    return null;
  }

  /** The nearest drawn vertex of ANY item within PICK_PX (the draw-line tool: a wall corner is often nearer to another
   *  item's edge than to its own), else the point itself; quanta. */
  snapVertex(px: number, py: number): [number, number] {
    const v = this.view!;
    const [qx, qy] = toLocal(v, this.size, px, py);
    const r = PICK_PX / v.s;
    const d = this.data;
    let best: [number, number] = [qx, qy], bestD = r * r;
    for (const e of entriesInBox(d, this.gridNow(), [qx - r, qy - r, qx + r, qy + r], 'touch')) {
      const f = d.first[e]!, c = d.count[e]!;
      for (let k = f; k < f + c; k++) {
        const x = d.pts[2 * k]!, y = d.pts[2 * k + 1]!, dd = (x - qx) ** 2 + (y - qy) ** 2;
        if (dd <= bestD) { best = [x, y]; bestD = dd; }
      }
    }
    return best;
  }

  /** A click at a screen point with the props' tool and pick mode (what a pointer up without a drag does). */
  click(px: number, py: number, mods: { shift?: boolean; ctrl?: boolean; alt?: boolean } = {}): void {
    const p = this.props;
    if (!this.view) return;
    if (p.tool === 'pick-point') {
      const q = this.snap(px, py);
      this.pickMark = q;
      this.requestDraw();
      p.onPick?.(this.data.toSheet(q[0], q[1]));
      return;
    }
    if (p.tool === 'draw-box') return;
    if (p.tool === 'draw-line') {
      const q = this.snapVertex(px, py);
      const a = this.lineStart;
      if (!a) { this.lineStart = q; this.lineEnd = null; this.requestDraw(); return; }
      this.lineStart = this.lineEnd = null;
      this.requestDraw();
      if (a[0] === q[0] && a[1] === q[1]) return;                       // a line of no length
      p.onLine?.(this.data.toSheet(a[0], a[1]), this.data.toSheet(q[0], q[1]));
      return;
    }
    if (p.tool === 'rooms') {
      const [qx, qy] = toLocal(this.view, this.size, px, py);
      const stair = this.stairAt(qx, qy);
      if (stair !== null && p.onStair) { p.onStair(stair); return; }
      const closing = this.closingAt(qx, qy);
      if (closing !== null && p.onClosing) { p.onClosing(closing); return; }
      const space = this.spaceAt(qx, qy);
      if (space && p.onSpace) { p.onSpace(space.id); return; }
      p.onPoint?.(this.data.toSheet(qx, qy));
      return;
    }
    const flag = this.flagAt(px, py);
    if (flag !== null && p.onFlag) { p.onFlag(flag); return; }
    const opening = this.openingAt(px, py);
    if (opening !== null && p.onOpening) { p.onOpening(opening); return; }
    if (p.tool !== 'select') return;
    const mode: Mode = mods.shift ? 'add' : mods.ctrl ? 'toggle' : 'replace';
    const e = this.entryAt(px, py);
    if (e < 0) { if (mode === 'replace' && p.selected.size) p.onSelect?.([], 'replace'); return; }
    const pick = p.pick ?? 'item';
    if (pick === 'layer-in-box') this.rememberLayer(this.data.layer[e]!);
    p.onSelect?.([clickKey(this.data, e, pick, p.selected, mode)], mode);
  }

  /** A box between two screen points (what a drag does with the select or draw-box tool). */
  boxAt(ax: number, ay: number, bx: number, by: number, mods: { shift?: boolean; ctrl?: boolean; alt?: boolean } = {},
    pressLayer: number | null = null): void {
    const p = this.props;
    if (!this.view) return;
    const b = boxFromScreen(this.view, this.size, ax, ay, bx, by);
    if (p.tool === 'draw-box') {
      const [x0, y0] = this.data.toSheet(b[0], b[1]), [x1, y1] = this.data.toSheet(b[2], b[3]);
      p.onBox?.([x0, y0, x1, y1] as Bbox);
      return;
    }
    if (p.tool !== 'select') return;
    const pick = p.pick ?? 'item';
    if (pick === 'layer-in-box' && pressLayer !== null) this.rememberLayer(pressLayer);
    const layer = pick === 'layer-in-box' ? pressLayer ?? this.lastLayer : null;
    const keys = boxKeys(this.data, this.gridNow(), b, mods.alt ? 'touch' : 'inside', pick, layer);
    const mode: Mode = mods.shift ? 'add' : mods.ctrl ? 'toggle' : 'replace';
    if (keys.length || mode === 'replace') p.onSelect?.(keys, mode);
  }

  private rememberLayer(layer: number): void {
    if (this.lastLayer === layer) return;
    this.lastLayer = layer;
    if (this.props.highlightLayer == null) { this.scene.highlight = layer; this.requestDraw(); }
  }

  // ------------------------------------------------------------------------------------------------------ input
  private listen(): void {
    const c = this.canvas;
    const on = <K extends keyof HTMLElementEventMap>(type: K, fn: (e: HTMLElementEventMap[K]) => void, opts?: AddEventListenerOptions) => {
      c.addEventListener(type, fn as EventListener, opts);
      this.off.push(() => c.removeEventListener(type, fn as EventListener, opts));
    };
    on('pointerdown', e => this.onDown(e));
    on('pointermove', e => this.onMove(e));
    on('pointerup', e => this.onUp(e));
    on('pointercancel', () => this.cancelDrag());
    on('pointerleave', () => { if (!this.drag) this.hover(null); });
    on('wheel', e => this.onWheel(e), { passive: false });
    on('keydown', e => this.onKey(e));
    on('contextmenu', e => { if (this.drag) e.preventDefault(); });
  }

  private local(e: { clientX: number; clientY: number }): [number, number] {
    const r = this.canvas.getBoundingClientRect();
    if (!Number.isFinite(e.clientX) || !Number.isFinite(e.clientY)) return [this.size.w / 2, this.size.h / 2];
    return [e.clientX - r.left, e.clientY - r.top];
  }

  private onDown(e: PointerEvent): void {
    if (!this.view || this.drag) return;
    if (e.button !== 0 && e.button !== 1) return;
    try { this.canvas.focus({ preventScroll: true }); } catch { /* not focusable in this environment */ }
    const [x, y] = this.local(e);
    const tool = this.props.tool;
    const pan = e.button === 1 || tool === 'pan';
    let pressLayer: number | null = null;
    if (!pan && tool === 'select' && (this.props.pick ?? 'item') === 'layer-in-box') {
      const hit = this.entryAt(x, y);
      pressLayer = hit >= 0 ? this.data.layer[hit]! : null;
    }
    this.drag = {
      id: e.pointerId, kind: pan ? 'pan' : 'press', button: e.button, x0: x, y0: y, x, y, pressLayer,
      shift: e.shiftKey, alt: e.altKey, ctrl: e.ctrlKey || e.metaKey, view0: this.view,
    };
    try { this.canvas.setPointerCapture(e.pointerId); } catch { /* a synthetic pointer */ }
    if (e.button === 1) e.preventDefault();
    this.hover(null);
  }

  private onMove(e: PointerEvent): void {
    const [x, y] = this.local(e);
    const g = this.drag;
    if (!g) {
      this.hoverAt = [x, y];
      this.scheduleHover();
      if (this.lineStart && this.view) { this.lineEnd = toLocal(this.view, this.size, x, y); this.requestDraw(); }
      return;
    }
    if (g.id !== e.pointerId) return;
    g.x = x; g.y = y;
    const moved = Math.hypot(x - g.x0, y - g.y0) >= DRAG_PX;
    if (g.kind === 'press' && moved) {
      const tool = this.props.tool;
      g.kind = tool === 'select' || tool === 'draw-box' ? 'box' : 'pan';
    }
    if (g.kind === 'pan' && (moved || g.view0 !== this.view)) this.setView(panBy(g.view0, x - g.x0, y - g.y0));
    if (g.kind === 'box') { this.band = [g.x0, g.y0, x, y]; this.requestDraw(); }
  }

  private onUp(e: PointerEvent): void {
    const g = this.drag;
    if (!g || g.id !== e.pointerId) return;
    this.drag = null;
    try { this.canvas.releasePointerCapture(e.pointerId); } catch { /* already released */ }
    const [x, y] = this.local(e);
    const mods = { shift: g.shift, alt: g.alt, ctrl: g.ctrl };
    if (g.kind === 'box') {
      this.band = null;
      this.requestDraw();
      this.boxAt(g.x0, g.y0, x, y, mods, g.pressLayer);
    } else if (g.kind === 'press' || (g.kind === 'pan' && Math.hypot(x - g.x0, y - g.y0) < DRAG_PX && g.button === 0)) {
      this.click(x, y, mods);
    }
  }

  private cancelDrag(): void {
    if (this.drag) {
      try { this.canvas.releasePointerCapture(this.drag.id); } catch { /* already released */ }
      this.drag = null;
    }
    if (this.band) { this.band = null; this.requestDraw(); }
  }

  private onWheel(e: WheelEvent): void {
    if (!this.view) return;
    e.preventDefault();
    const [x, y] = this.local(e);
    this.setView(zoomAt(this.view, this.size, x, y, wheelFactor(e.deltaY, e.deltaMode, this.size.h), scaleLimits(this.data.bounds, this.size)));
    if (this.drag?.kind === 'pan') { this.drag.view0 = this.view; this.drag.x0 = x; this.drag.y0 = y; }
  }

  private onKey(e: KeyboardEvent): void {
    if (!this.view || e.altKey || e.ctrlKey || e.metaKey) return;
    const step = (e.shiftKey ? 0.5 : 0.1) * Math.min(this.size.w, this.size.h);
    const lim = scaleLimits(this.data.bounds, this.size);
    const mid: [number, number] = [this.size.w / 2, this.size.h / 2];
    switch (e.key) {
      case 'ArrowLeft': this.setView(panBy(this.view, step, 0)); break;
      case 'ArrowRight': this.setView(panBy(this.view, -step, 0)); break;
      case 'ArrowUp': this.setView(panBy(this.view, 0, step)); break;
      case 'ArrowDown': this.setView(panBy(this.view, 0, -step)); break;
      case '+': case '=': this.setView(zoomAt(this.view, this.size, mid[0], mid[1], 1.25, lim)); break;
      case '-': case '_': this.setView(zoomAt(this.view, this.size, mid[0], mid[1], 0.8, lim)); break;
      case 'f': case 'F': case '0': case 'Home': this.fit(); break;
      case 'Escape':
        if (this.drag) this.cancelDrag();
        else if (this.lineStart) { this.lineStart = this.lineEnd = null; this.requestDraw(); }
        else if (this.props.selected.size) this.props.onSelect?.([], 'replace');
        break;
      default: return;
    }
    e.preventDefault();
  }

  // ------------------------------------------------------------------------------------------------------ hover
  private scheduleHover(): void {
    if (this.hoverRaf || typeof requestAnimationFrame !== 'function') { if (!this.hoverRaf) this.hoverNow(); return; }
    this.hoverRaf = requestAnimationFrame(() => { this.hoverRaf = 0; this.hoverNow(); });
  }

  private hoverNow(): void {
    if (!this.hoverAt || this.drag) return;
    const [x, y] = this.hoverAt;
    const flag = this.flagAt(x, y);
    if (flag !== null) {
      const f = this.scene.flags.find(g => g.id === flag)!;
      this.tipShow(x, y, [f.title || f.id]);
      this.report(null);
      return;
    }
    const opening = this.openingAt(x, y);
    if (opening !== null) {
      const o = this.scene.overlay!.openings.find(g => g.id === opening)!;
      this.tipShow(x, y, [`${o.id} (${o.kind})`]);
      this.report(null);
      return;
    }
    // rooms milestone: the room under the pointer with its area (R-12.6), when the rooms are shown
    const [qx, qy] = this.view ? toLocal(this.view, this.size, x, y) : [0, 0];
    const room = this.scene.show.rooms && this.view ? this.spaceAt(qx, qy) : null;
    const roomLine = room ? roomText(room) : null;
    const e = this.entryAt(x, y);
    if (e < 0) {
      if (roomLine) { this.tipShow(x, y, [roomLine]); this.report(null); return; }
      this.hover(null);
      return;
    }
    const d = this.data, layer = d.layerNames[d.layer[e]!]!, type = d.type[e]!, key = d.keys[e]!;
    this.tipShow(x, y, roomLine ? [layer, `${TYPE_NAMES[type] ?? type} · ${key}`, roomLine] : [layer, `${TYPE_NAMES[type] ?? type} · ${key}`]);
    this.report({ layer, type, key });
  }

  // ------------------------------------------------------------------------------------------------------ test hook
  /** window.__plan (rooms R-12.6): sheet points to page pixels, and the rooms and stairs of the overlay on screen. */
  testHook(): PlanTestHook {
    return {
      toPage: (pt: Vec2) => {
        if (this.disposed || !this.view || !Array.isArray(pt)) return null;
        const s = this.sheetToScreen(pt[0], pt[1]);
        if (!s || s[0] < 0 || s[1] < 0 || s[0] > this.size.w || s[1] > this.size.h) return null;
        const r = this.canvas.getBoundingClientRect();
        return [r.left + s[0], r.top + s[1]];
      },
      spaces: () => (this.scene.overlay?.spaces ?? []).map(r => ({ id: r.id, name: r.name, area: r.area, at: r.sheetAt })),
      stairs: () => (this.scene.overlay?.stairs ?? []).map(s => ({ id: s.id, state: s.state, at: s.sheetAt })),
    };
  }

  private hover(info: null): void {
    this.hoverAt = info;
    this.tipHide();
    this.report(null);
  }

  private report(info: { layer: string; type: number; key: string } | null): void {
    const k = info ? `${info.layer}\u0000${info.type}\u0000${info.key}` : '';
    if (k === this.hoverKey) return;
    this.hoverKey = k;
    this.props.onHover?.(info);
  }

  private tipShow(x: number, y: number, lines: string[]): void {
    const t = this.tip;
    if (!t) return;
    t.textContent = lines.join('\n');          // drawing text: text only, never HTML
    t.hidden = false;
    const left = x + 14 + 260 > this.size.w ? Math.max(0, x - 14 - 260) : x + 14;
    const top = y + 16 + 40 > this.size.h ? Math.max(0, y - 16 - 40) : y + 16;
    t.style.left = `${Math.round(left)}px`;
    t.style.top = `${Math.round(top)}px`;
  }

  private tipHide(): void {
    if (this.tip && !this.tip.hidden) this.tip.hidden = true;
  }

  // ------------------------------------------------------------------------------------------------------ teardown
  dispose(): void {
    this.disposed = true;
    if (this.raf && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(this.raf);
    if (this.hoverRaf && typeof cancelAnimationFrame === 'function') cancelAnimationFrame(this.hoverRaf);
    this.raf = this.hoverRaf = 0;
    for (const f of this.off.splice(0)) f();
    controllerOf.delete(this.canvas);
  }
}

/** Stroke and fill of a cached path (a Path2D in the browser; a recorder in the unit tests replays its own). */
const DRAW = {
  stroke(ctx: Ctx, p: P): void {
    if (typeof Path2D !== 'undefined' && p instanceof Path2D) (ctx as CanvasRenderingContext2D).stroke(p);
    else (p as unknown as { replay?(ctx: Ctx, op: 'stroke' | 'fill'): void }).replay?.(ctx, 'stroke');
  },
  fill(ctx: Ctx, p: P): void {
    if (typeof Path2D !== 'undefined' && p instanceof Path2D) (ctx as CanvasRenderingContext2D).fill(p);
    else (p as unknown as { replay?(ctx: Ctx, op: 'stroke' | 'fill'): void }).replay?.(ctx, 'fill');
  },
};

export function cursorOf(tool: PlanCanvasProps['tool']): string {
  return tool === 'pan' ? 'grab' : tool === 'select' ? 'default' : 'crosshair';
}

/** `show` missing: everything (index.ts). */
export const SHOW_ALL: PlanShow = { rooms: true, plate: true, furniture: true };
const showOf = (s: PlanShow | undefined): PlanShow => (s ? { rooms: s.rooms !== false, plate: s.plate !== false, furniture: s.furniture !== false } : SHOW_ALL);
const sameShow = (a: PlanShow, b: PlanShow) => a.rooms === b.rooms && a.plate === b.plate && a.furniture === b.furniture;

/** A room's hover line: its name (or "Room"), its area, "no ceiling" when it has none (R-6.4). Drawing text: text only. */
export function roomText(r: Pick<LocalSpace, 'name' | 'area' | 'ceiling'>): string {
  const area = `${(Math.round(r.area * 10) / 10).toFixed(1)} m²`;
  return `${r.name || 'Room'} · ${area}${r.ceiling ? '' : ' · no ceiling'}`;
}

/** RR (S7): the margin round a floor's own box, in metres: this share of its longer side, at least HOME_MARGIN_M. */
export const HOME_MARGIN_SHARE = 0.04;
export const HOME_MARGIN_M = 0.5;

/** The box (quanta) of an overlay floor's own geometry: its plate (slabs), parts and stairs; else its area box; with a
 *  margin. null when the overlay has none of them (the caller then fits the sheet). */
export function homeBoxOf(d: PlanData, ov: LocalOverlay, area: QBox | null): QBox | null {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const take = (r: ArrayLike<number>) => {
    const b = ringBox(r);
    if (!b || !b.every(Number.isFinite)) return;
    if (b[0] < x0) x0 = b[0]; if (b[1] < y0) y0 = b[1]; if (b[2] > x1) x1 = b[2]; if (b[3] > y1) y1 = b[3];
  };
  for (const s of ov.slabs) take(s.o);
  for (const p of ov.parts) take(p.o);
  for (const st of ov.stairs) take(st.outline);
  const box: QBox | null = Number.isFinite(x0) ? [x0, y0, x1, y1] : area;
  if (!box) return null;
  const m = Math.max(HOME_MARGIN_M / d.quantum, HOME_MARGIN_SHARE * Math.max(box[2] - box[0], box[3] - box[1]));
  return [box[0] - m, box[1] - m, box[2] + m, box[3] + m];
}

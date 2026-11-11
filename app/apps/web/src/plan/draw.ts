// One frame of the plan canvas (docs/upload/DESIGN.md U-12.1). Owner U7.
// Order: the cached layer paths in their roles' colours (faint roles first, walls last), the floor's area lit and the
// rest dimmed, the highlighted layer, the overlay (slabs outlined, parts filled by kind, furniture rectangles, openings
// as thick segments by kind), the diff (added green, removed red), the set-aside items crossed, the selection; then, in
// screen pixels, the flags as rings, the room names and opening numbers (fillText: drawing text is never HTML), the
// rubber band. Every width is in screen pixels: divided by the scale while the transform is the plan's.
import {
  AREA_EDGE, BACKGROUND, BUILT_ASIDE, CLOSING_APP, CLOSING_STAFF, DIFF_ADDED, DIFF_REMOVED, DIM_VEIL, FILL_ALPHA, FLAG_COLOUR,
  FLAG_RADIUS, FURNITURE, FURNITURE_FILL, HATCH_PX, HIGHLIGHT, HIGHLIGHT_VEIL, HOLE_HATCH, LABEL, LINE_DRAFT, MOUTH, OPENING_COLOUR,
  OPENING_WIDTH, OUTDOORS_HATCH, PART_ALPHA, PART_FILL, PATTERN_ALPHA, PICK_MARK, ROOM_ALPHA, ROOM_EDGE, ROOM_FILL, RUBBER_BAND,
  SELECTED, SET_ASIDE, SLAB_EDGE, STAIR_OUTLINE, STAIR_WALK, STRUCK, UNFLOORED_HATCH, WAITING, roleStroke, type Stroke,
} from './colours';
import { T_CLOSED, T_OPEN, T_PATTERN, T_SOLID, type PlanData, type QBox } from './decode';
import { ringBox } from './geom';
import type { LocalDiff, LocalFlag, LocalOverlay, LRing } from './overlay';
import type { LayerPath } from './paths';
import { canvasTransform, toScreen, visibleBox, type Size, type View } from './view';
import type { LayerRole } from '@/upload/contracts';
import type { PartKind } from '@walkthrough/viewer';

/** The 2D context calls a frame makes (CanvasRenderingContext2D has them all; the unit tests record them). */
export type Ctx = Pick<CanvasRenderingContext2D,
  'save' | 'restore' | 'setTransform' | 'fillRect' | 'beginPath' | 'moveTo' | 'lineTo' | 'closePath' | 'rect' | 'arc'
  | 'stroke' | 'fill' | 'setLineDash' | 'fillText' | 'strokeText' | 'measureText' | 'clip'> & {
  fillStyle: string | CanvasGradient | CanvasPattern;
  strokeStyle: string | CanvasGradient | CanvasPattern;
  lineWidth: number;
  lineJoin: CanvasLineJoin;
  lineCap: CanvasLineCap;
  globalAlpha: number;
  font: string;
  textAlign: CanvasTextAlign;
  textBaseline: CanvasTextBaseline;
};

/** What a frame draws (the controller keeps it; every array is in the plan's local quanta). */
export interface Scene<P> {
  data: PlanData;
  paths: LayerPath<P>[];
  texts: Map<number, number[]>;
  roles: LayerRole[];
  area: QBox | null;
  highlight: number | null;
  overlay: LocalOverlay | null;
  flags: LocalFlag[];
  diff: LocalDiff | null;
  /** Paths of the selected / set-aside / built-aside items, and the boxes to cross (set-asides) or outline (blocks). */
  selected: P | null;
  selectedBoxes: QBox[];
  setAside: P | null;
  setAsideBoxes: QBox[];
  builtAside: P | null;
  builtAsideBoxes: QBox[];
  /** The rubber band (screen px) while a box is dragged, the last picked point (quanta). */
  band: [number, number, number, number] | null;
  pickMark: [number, number] | null;
  /** Rooms milestone (R-12.6): what is drawn of the overlay (the Check step's three ticks). */
  show: { rooms: boolean; plate: boolean; furniture: boolean };
  /** The tool 'draw-line': its first end and the pointer (quanta), until the second click. */
  lineStart: [number, number] | null;
  lineEnd: [number, number] | null;
}

/** Draw order of the roles: faint ones first, so the built ones are on top. */
const ROLE_ORDER: Record<string, number> = { ignore: 0, other: 1, grid: 2, level: 3, light: 3, 'room-name': 4, 'room-outline': 4 };
const roleRank = (r: LayerRole) => ROLE_ORDER[r] ?? (r === 'wall' || r === 'column' ? 9 : 6);

export function drawFrame<P>(ctx: Ctx, sc: Scene<P>, view: View, size: Size, dpr: number,
  draw: { stroke(ctx: Ctx, p: P): void; fill(ctx: Ctx, p: P): void }): void {
  const s = view.s;
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.fillStyle = BACKGROUND;
  ctx.fillRect(0, 0, Math.round(size.w * dpr), Math.round(size.h * dpr));
  ctx.setTransform(...canvasTransform(view, size, dpr));
  ctx.lineJoin = 'miter';
  ctx.lineCap = 'butt';
  const vis = visibleBox(view, size);

  // ---- the drawing, by role
  const order = sc.paths.map((lp, i) => [roleRank(sc.roles[lp.layer] ?? 'other'), lp.type === T_SOLID ? 0 : 1, i] as const)
    .sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
  for (const [, , i] of order) {
    const lp = sc.paths[i]!;
    if (lp.box[2] < vis[0] || lp.box[0] > vis[2] || lp.box[3] < vis[1] || lp.box[1] > vis[3]) continue;
    strokePath(ctx, lp, roleStroke(sc.roles[lp.layer] ?? 'other'), s * dpr, draw);
  }
  for (const [layer, xy] of sc.texts) dots(ctx, xy, roleStroke(sc.roles[layer] ?? 'other'), s, vis);   // 1.5 CSS px squares

  // ---- the floor's area lit, the rest dimmed
  if (sc.area) {
    ctx.globalAlpha = 1;
    ctx.fillStyle = DIM_VEIL;
    ctx.beginPath();
    ctx.rect(vis[0], vis[1], vis[2] - vis[0], vis[3] - vis[1]);
    const a = sc.area;
    // the area as a hole (even-odd)
    ctx.moveTo(a[0], a[1]); ctx.lineTo(a[0], a[3]); ctx.lineTo(a[2], a[3]); ctx.lineTo(a[2], a[1]); ctx.closePath();
    ctx.fill('evenodd');
    edge(ctx, AREA_EDGE, s, [6, 4]);
    ctx.beginPath(); ctx.rect(a[0], a[1], a[2] - a[0], a[3] - a[1]); ctx.stroke();
    ctx.setLineDash([]);
  }

  // ---- the highlighted layer
  if (sc.highlight !== null) {
    ctx.globalAlpha = 1;
    ctx.fillStyle = HIGHLIGHT_VEIL;
    ctx.fillRect(vis[0], vis[1], vis[2] - vis[0], vis[3] - vis[1]);
    for (const lp of sc.paths) {
      if (lp.layer !== sc.highlight) continue;
      if (lp.type === T_SOLID) { ctx.globalAlpha = 0.35; ctx.fillStyle = HIGHLIGHT.colour; draw.fill(ctx, lp.path); }
      edge(ctx, HIGHLIGHT, s);
      draw.stroke(ctx, lp.path);
    }
    const xy = sc.texts.get(sc.highlight);
    if (xy) dots(ctx, xy, HIGHLIGHT, s, vis, 2.5);
  }

  // ---- the build's overlay
  const ov = sc.overlay;
  const show = sc.show;
  if (ov) {
    if (show.plate) {
      for (const sl of ov.slabs) { polygon(ctx, sl.o, sl.h); edge(ctx, SLAB_EDGE, s, [4, 3]); ctx.stroke(); ctx.setLineDash([]); }
      // rooms milestone: the plate's holes hatched, the unfloored areas hatched orange with their mouth dashed
      for (const h of ov.holes) { hatch(ctx, h.o, h.h, HOLE_HATCH, s, vis, 1); polygon(ctx, h.o, h.h); edge(ctx, HOLE_HATCH, s); ctx.stroke(); }
      for (const u of ov.unfloored) {
        const st = u.answered || ov.marks?.outdoors.has(u.index) ? OUTDOORS_HATCH : UNFLOORED_HATCH;
        hatch(ctx, u.o, [], st, s, vis, u.answered ? -1 : 1);
        polygon(ctx, u.o, []); edge(ctx, st, s); ctx.stroke();
        if (u.mouth && !u.answered) { edge(ctx, MOUTH, s, [6, 4]); segment(ctx, u.mouth[0], u.mouth[1]); ctx.setLineDash([]); }
      }
    }
    if (show.rooms) {
      for (const r of ov.spaces) {
        polygon(ctx, r.o, r.h);
        ctx.globalAlpha = ROOM_ALPHA; ctx.fillStyle = ROOM_FILL; ctx.fill('evenodd');
        edge(ctx, ROOM_EDGE, s); ctx.stroke();
      }
    }
    for (const p of ov.parts) {
      polygon(ctx, p.o, p.h);
      ctx.globalAlpha = PART_ALPHA;
      ctx.fillStyle = PART_FILL[p.kind as PartKind] ?? PART_FILL.wall;
      ctx.fill('evenodd');
      edge(ctx, { colour: PART_FILL[p.kind as PartKind] ?? PART_FILL.wall, alpha: 0.9, width: 0.8 }, s);
      ctx.stroke();
    }
    if (show.furniture) {
      for (const f of ov.furniture) {
        polygon(ctx, f.corners, []);
        ctx.globalAlpha = 1; ctx.fillStyle = FURNITURE_FILL; ctx.fill();
        edge(ctx, FURNITURE, s); ctx.stroke();
      }
    }
    for (const o of ov.openings) {
      // a fixed opening (staff changed it) is dashed
      edge(ctx, { colour: OPENING_COLOUR[o.kind] ?? OPENING_COLOUR.door, alpha: o.fixed ? 0.65 : 1, width: OPENING_WIDTH }, s, o.fixed ? [3, 2] : undefined);
      ctx.beginPath(); ctx.moveTo(o.a[0], o.a[1]); ctx.lineTo(o.b[0], o.b[1]); ctx.stroke();
      ctx.setLineDash([]);
    }
    // rooms milestone, always drawn: the stairs (outline; a climbable one with its walking line and an arrow at the
    // bottom), the app's closings dashed and staff closing lines solid
    for (const st of ov.stairs) {
      polygon(ctx, st.outline, []);
      edge(ctx, STAIR_OUTLINE, s, st.state === 'climb' ? undefined : [5, 3]); ctx.stroke(); ctx.setLineDash([]);
      if (st.walk) {
        polyline(ctx, st.walk); edge(ctx, STAIR_WALK, s); ctx.stroke();
        arrowHead(ctx, [st.walk[0]!, st.walk[1]!], [st.walk[2]!, st.walk[3]!], STAIR_WALK, s);
      }
    }
    for (const c of ov.closings) {
      edge(ctx, c.kind === 'staff' ? CLOSING_STAFF : CLOSING_APP, s, c.kind === 'staff' ? undefined : [5, 4]);
      segment(ctx, c.a, c.b); ctx.setLineDash([]);
    }
    // the fixes waiting for a Rebuild (R-6.4 "Shown before Rebuild")
    const mk = ov.marks;
    if (mk) {
      for (const id of mk.rooms) {
        const r = ov.spaces.find(x => x.id === id);
        if (r) { polygon(ctx, r.o, r.h); edge(ctx, WAITING, s, [6, 4]); ctx.stroke(); ctx.setLineDash([]); }
      }
      for (const [a, b] of mk.lines) { edge(ctx, WAITING, s, [6, 4]); segment(ctx, a, b); ctx.setLineDash([]); }
      for (const [a, b] of mk.removed) {
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, g = 7 / s;
        edge(ctx, STRUCK, s);
        ctx.beginPath(); ctx.moveTo(mx - g, my - g); ctx.lineTo(mx + g, my + g); ctx.moveTo(mx - g, my + g); ctx.lineTo(mx + g, my - g); ctx.stroke();
      }
      for (const p of mk.points) {
        const g = 6 / s;
        edge(ctx, WAITING, s);
        ctx.beginPath();
        if (p.kind === 'floor') { ctx.rect(p.at[0] - g, p.at[1] - g, 2 * g, 2 * g); }
        else { ctx.moveTo(p.at[0] - g, p.at[1]); ctx.lineTo(p.at[0], p.at[1] + g); ctx.lineTo(p.at[0] + g, p.at[1]); ctx.lineTo(p.at[0], p.at[1] - g); ctx.closePath(); }
        ctx.stroke();
      }
      for (const b of mk.bottoms) {
        const st = ov.stairs.find(x => x.box[0] <= b[0] && b[0] <= x.box[2] && x.box[1] <= b[1] && b[1] <= x.box[3]);
        const toward: [number, number] = st ? [st.at[0], st.at[1]] : [b[0], b[1] + 1];
        arrowHead(ctx, b, toward, WAITING, s, 12);
      }
    }
  }
  if (sc.lineStart) {
    const [x, y] = sc.lineStart, g = 5 / s;
    edge(ctx, LINE_DRAFT, s);
    ctx.beginPath(); ctx.moveTo(x - g, y); ctx.lineTo(x + g, y); ctx.moveTo(x, y - g); ctx.lineTo(x, y + g); ctx.stroke();
    if (sc.lineEnd) { edge(ctx, LINE_DRAFT, s, [4, 3]); segment(ctx, sc.lineStart, sc.lineEnd); ctx.setLineDash([]); }
  }

  // ---- the diff
  const df = sc.diff;
  if (df) {
    for (const p of df.added) {
      polygon(ctx, p.o, []);
      ctx.globalAlpha = 0.25; ctx.fillStyle = DIFF_ADDED; ctx.fill();
      edge(ctx, { colour: DIFF_ADDED, alpha: 1, width: 2 }, s); ctx.stroke();
    }
    for (const p of df.removed) { polygon(ctx, p.o, []); edge(ctx, { colour: DIFF_REMOVED, alpha: 1, width: 2 }, s, [5, 3]); ctx.stroke(); ctx.setLineDash([]); }
    for (const [list, colour] of [[df.openingsAdded, DIFF_ADDED], [df.openingsRemoved, DIFF_REMOVED]] as const) {
      edge(ctx, { colour, alpha: 1, width: 3.5 }, s);
      for (const o of list) { ctx.beginPath(); ctx.moveTo(o.a[0], o.a[1]); ctx.lineTo(o.b[0], o.b[1]); ctx.stroke(); }
    }
  }

  // ---- set aside (crossed), then the selection
  for (const [p, boxes, st] of [[sc.builtAside, sc.builtAsideBoxes, BUILT_ASIDE], [sc.setAside, sc.setAsideBoxes, SET_ASIDE]] as const) {
    if (p) { edge(ctx, st, s, [4, 3]); draw.stroke(ctx, p); ctx.setLineDash([]); }
    if (boxes.length) {
      edge(ctx, st, s);
      ctx.beginPath();
      for (const b of boxes) {
        const g = 3 / s;
        ctx.moveTo(b[0] - g, b[1] - g); ctx.lineTo(b[2] + g, b[3] + g);
        ctx.moveTo(b[0] - g, b[3] + g); ctx.lineTo(b[2] + g, b[1] - g);
      }
      ctx.stroke();
    }
  }
  if (sc.selected) { edge(ctx, SELECTED, s); draw.stroke(ctx, sc.selected); }
  if (sc.selectedBoxes.length) {
    edge(ctx, { ...SELECTED, width: 1.2 }, s, [5, 3]);
    ctx.beginPath();
    const g = 4 / s;
    for (const b of sc.selectedBoxes) ctx.rect(b[0] - g, b[1] - g, b[2] - b[0] + 2 * g, b[3] - b[1] + 2 * g);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // ---- screen space: flags, labels, the rubber band, the picked point
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.globalAlpha = 1;
  ctx.setLineDash([]);
  for (const f of sc.flags) {
    const [x, y] = toScreen(view, size, f.at[0], f.at[1]);
    if (x < -20 || y < -20 || x > size.w + 20 || y > size.h + 20) continue;
    ctx.beginPath(); ctx.arc(x, y, FLAG_RADIUS, 0, Math.PI * 2);
    ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.stroke();
    ctx.lineWidth = 2; ctx.strokeStyle = FLAG_COLOUR[f.severity]; ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fillStyle = FLAG_COLOUR[f.severity]; ctx.fill();
  }
  if (ov) {
    ctx.font = LABEL.font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 3;
    ctx.strokeStyle = LABEL.halo;
    for (const r of ov.rooms) {
      const [x, y] = toScreen(view, size, r.at[0], r.at[1]);
      if (x < -100 || y < -20 || x > size.w + 100 || y > size.h + 20 || !r.name) continue;
      ctx.strokeText(r.name, x, y);
      ctx.fillStyle = LABEL.colour;
      ctx.fillText(r.name, x, y);
    }
    for (const o of ov.openings) {
      const [ax, ay] = toScreen(view, size, o.a[0], o.a[1]), [bx, by] = toScreen(view, size, o.b[0], o.b[1]);
      if (Math.hypot(bx - ax, by - ay) < 12) continue;
      const x = (ax + bx) / 2, y = (ay + by) / 2;
      if (x < -20 || y < -20 || x > size.w + 20 || y > size.h + 20) continue;
      ctx.strokeText(o.label, x, y - 9);
      ctx.fillStyle = OPENING_COLOUR[o.kind] ?? LABEL.colour;
      ctx.fillText(o.label, x, y - 9);
    }
  }
  if (sc.pickMark) {
    const [x, y] = toScreen(view, size, sc.pickMark[0], sc.pickMark[1]);
    ctx.lineWidth = 2; ctx.strokeStyle = PICK_MARK;
    ctx.beginPath(); ctx.moveTo(x - 7, y); ctx.lineTo(x + 7, y); ctx.moveTo(x, y - 7); ctx.lineTo(x, y + 7); ctx.stroke();
  }
  if (sc.band) {
    const [x0, y0, x1, y1] = sc.band;
    ctx.fillStyle = RUBBER_BAND.fill;
    ctx.fillRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0));
    ctx.lineWidth = 1; ctx.strokeStyle = RUBBER_BAND.stroke; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.rect(Math.min(x0, x1) + 0.5, Math.min(y0, y1) + 0.5, Math.abs(x1 - x0), Math.abs(y1 - y0)); ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.restore();
}

/** The drawing's own lines: widths in DEVICE pixels (s = device pixels per quantum), so they stay 1 px hairlines at any
 *  device pixel ratio (Chromium's fast path; U-12.1's budget). */
function strokePath<P>(ctx: Ctx, lp: LayerPath<P>, st: Stroke, s: number, draw: { stroke(ctx: Ctx, p: P): void; fill(ctx: Ctx, p: P): void }): void {
  if (lp.type === T_SOLID) {
    ctx.globalAlpha = st.alpha * FILL_ALPHA;
    ctx.fillStyle = st.colour;
    draw.fill(ctx, lp.path);
    edge(ctx, st, s);
    draw.stroke(ctx, lp.path);
  } else if (lp.type === T_PATTERN) {
    edge(ctx, { ...st, alpha: st.alpha * PATTERN_ALPHA, width: st.width * 0.8 }, s);
    draw.stroke(ctx, lp.path);
  } else if (lp.type === T_OPEN || lp.type === T_CLOSED) {
    edge(ctx, st, s);
    draw.stroke(ctx, lp.path);
  }
}

/** Sets the stroke: colour, alpha, a width in screen pixels, an optional dash in screen pixels. */
function edge(ctx: Ctx, st: Stroke, s: number, dash?: number[]): void {
  ctx.globalAlpha = st.alpha;
  ctx.strokeStyle = st.colour;
  ctx.lineWidth = st.width / s;
  ctx.setLineDash(dash ? dash.map(v => v / s) : []);
}

/** Text anchors as small squares (radius in screen pixels), only those in view. */
function dots(ctx: Ctx, xy: number[], st: Stroke, s: number, vis: QBox, r = 1.5): void {
  ctx.globalAlpha = Math.min(1, st.alpha + 0.2);
  ctx.fillStyle = st.colour;
  const q = r / s;
  for (let i = 0; i < xy.length; i += 2) {
    const x = xy[i]!, y = xy[i + 1]!;
    if (x < vis[0] - q || x > vis[2] + q || y < vis[1] - q || y > vis[3] + q) continue;
    ctx.fillRect(x - q, y - q, 2 * q, 2 * q);
  }
}

function segment(ctx: Ctx, a: readonly number[], b: readonly number[]): void {
  ctx.beginPath(); ctx.moveTo(a[0]!, a[1]!); ctx.lineTo(b[0]!, b[1]!); ctx.stroke();
}

function polyline(ctx: Ctx, r: LRing): void {
  ctx.beginPath();
  ctx.moveTo(r[0]!, r[1]!);
  for (let i = 2; i + 1 < r.length; i += 2) ctx.lineTo(r[i]!, r[i + 1]!);
}

/** A filled arrowhead at `at` pointing toward `to` (size in screen pixels). */
function arrowHead(ctx: Ctx, at: readonly number[], to: readonly number[], st: Stroke, s: number, px = 11): void {
  const dx = to[0]! - at[0]!, dy = to[1]! - at[1]!, l = Math.hypot(dx, dy);
  if (!(l > 0)) return;
  const ux = dx / l, uy = dy / l, L = px / s, W = (px * 0.55) / s;
  ctx.globalAlpha = st.alpha;
  ctx.fillStyle = st.colour;
  ctx.beginPath();
  ctx.moveTo(at[0]! + ux * L, at[1]! + uy * L);
  ctx.lineTo(at[0]! - uy * W, at[1]! + ux * W);
  ctx.lineTo(at[0]! + uy * W, at[1]! - ux * W);
  ctx.closePath();
  ctx.fill();
}

/** Diagonal hatch lines HATCH_PX screen pixels apart, clipped to the polygon (and to the view). dir 1: "/", -1: "\". */
function hatch(ctx: Ctx, o: LRing, holes: LRing[], st: Stroke, s: number, vis: QBox, dir: 1 | -1): void {
  const b = ringBox(o);
  if (!b) return;
  const x0 = Math.max(b[0], vis[0]), y0 = Math.max(b[1], vis[1]), x1 = Math.min(b[2], vis[2]), y1 = Math.min(b[3], vis[3]);
  if (x0 >= x1 || y0 >= y1) return;
  const sp = HATCH_PX / s;
  ctx.save();
  polygon(ctx, o, holes);
  ctx.clip('evenodd');
  edge(ctx, st, s);
  ctx.beginPath();
  // lines x - dir * y = c across the box
  const c0 = dir === 1 ? x0 - y1 : x0 + y0, c1 = dir === 1 ? x1 - y0 : x1 + y1;
  for (let c = Math.floor(c0 / sp) * sp; c <= c1; c += sp) {
    ctx.moveTo(c + dir * y0, y0);
    ctx.lineTo(c + dir * y1, y1);
  }
  ctx.stroke();
  ctx.restore();
}

function polygon(ctx: Ctx, o: LRing, holes: LRing[]): void {
  ctx.beginPath();
  for (const ring of [o, ...holes]) {
    if (ring.length < 4) continue;
    ctx.moveTo(ring[0]!, ring[1]!);
    for (let i = 2; i < ring.length; i += 2) ctx.lineTo(ring[i]!, ring[i + 1]!);
    ctx.closePath();
  }
}


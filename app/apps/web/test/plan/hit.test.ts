// U7: hit.ts (docs/upload/DESIGN.md U-12.1; ACCEPTANCE 2.3 U7 "hit.ts (nearest item, box inside / touching, the block mode
// climbing levels, layer-in-box, at several zooms)"). The grid index is checked against brute force on the bank plan.
import { describe, expect, it } from 'vitest';
import { decodePlan } from '@/plan';
import { blockChain, planData } from '@/plan/decode';
import { boxKeys, buildGrid, cellsOfSegment, clickKey, entriesInBox, nearest, segmentTouchesBox } from '@/plan/hit';
import type { PlanGeometry } from '@/upload/contracts';
import { bruteNearest, d2, loadPlan, makePlan, rng, segmentsOf, type Item } from './kit';

const L = (k: string, layer: string, ...pts: [number, number][]): Item => ({ key: k, layer, type: 0, pts });

describe('the grid walk', () => {
  it('every point of a segment lies in a cell the walk visits (random segments, any direction)', () => {
    const r = rng(11);
    for (let n = 0; n < 300; n++) {
      const cs = 200, cols = 40, rows = 30;
      const ax = r() * 8000, ay = r() * 6000, bx = r() * 8000, by = r() * 6000;
      const seen = new Set<number>();
      cellsOfSegment(ax, ay, bx, by, cs, cols, rows, c => seen.add(c));
      for (let k = 0; k < 200; k++) {
        const t = r(), x = ax + (bx - ax) * t, y = ay + (by - ay) * t;
        expect(seen.has(Math.floor(y / cs) * cols + Math.floor(x / cs))).toBe(true);
      }
      expect(seen.size).toBeLessThanOrEqual(Math.abs(Math.floor(bx / cs) - Math.floor(ax / cs)) + Math.abs(Math.floor(by / cs) - Math.floor(ay / cs)) + 1);
    }
  });

  it('segmentTouchesBox: crossing, inside, touching an edge, missing', () => {
    const b: [number, number, number, number] = [0, 0, 10, 10];
    expect(segmentTouchesBox(-5, 5, 15, 5, b)).toBe(true);
    expect(segmentTouchesBox(2, 2, 3, 3, b)).toBe(true);
    expect(segmentTouchesBox(10, -5, 10, 15, b)).toBe(true);
    expect(segmentTouchesBox(-5, -5, -1, 20, b)).toBe(false);
    expect(segmentTouchesBox(-5, 2, 4, 14, b)).toBe(true);
    expect(segmentTouchesBox(-5, 4, 4, 16, b)).toBe(false);
    expect(segmentTouchesBox(-5, 8, 2, 16, b)).toBe(false);
    expect(segmentTouchesBox(5, 5, 5, 5, b)).toBe(true);
  });
});

describe('nearest and boxes on the bank plan, against brute force', () => {
  const json = loadPlan('bank1');
  const d = planData(decodePlan(json));
  const g = buildGrid(d)!;
  const n = json.items.key.length;
  const r = rng(7);
  const segs: [number, number, number, number, number][] = [];
  for (let i = 0; i < n; i++) for (const s of segmentsOf(json, i)) segs.push([i, ...s]);

  for (const s of [0.3, 1, 5]) {              // CSS px per quantum: the sheet whole, 1 px per cm, close up
    it(`nearest within 6 px at ${s} px per centimetre finds the nearest drawn item (or none beyond 6 px)`, () => {
      const rad = 6 / s;
      for (let k = 0; k < 120; k++) {
        const [, ax, ay, bx, by] = segs[Math.floor(r() * segs.length)]!;
        const t = r(), off = (r() - 0.5) * 3 * rad;
        const qx = ax + (bx - ax) * t + off, qy = ay + (by - ay) * t - off;
        const want = bruteNearest(json, qx, qy);
        const got = nearest(d, g, qx, qy, rad);
        if (want.d > rad + 1e-9) { expect(got).toBeNull(); continue; }
        expect(got, `at ${qx}, ${qy}`).not.toBeNull();
        expect(got!.d).toBeCloseTo(want.d, 6);
        expect(want.entries).toContain(got!.entry);
        expect(json.items.type[got!.entry]).not.toBe(5);
      }
    });
  }

  const touches = (sx: number, sy: number, ex: number, ey: number, b: number[]) => {
    const inside = (x: number, y: number) => x >= b[0]! && x <= b[2]! && y >= b[1]! && y <= b[3]!;
    if (inside(sx, sy) || inside(ex, ey)) return true;
    const side = (ax: number, ay: number, bx: number, by: number, cx: number, cy: number) => Math.sign((bx - ax) * (cy - ay) - (by - ay) * (cx - ax));
    const cross = (cx: number, cy: number, dx: number, dy: number) =>
      side(sx, sy, ex, ey, cx, cy) * side(sx, sy, ex, ey, dx, dy) <= 0 && side(cx, cy, dx, dy, sx, sy) * side(cx, cy, dx, dy, ex, ey) <= 0;
    return cross(b[0]!, b[1]!, b[2]!, b[1]!) || cross(b[2]!, b[1]!, b[2]!, b[3]!) || cross(b[2]!, b[3]!, b[0]!, b[3]!) || cross(b[0]!, b[3]!, b[0]!, b[1]!);
  };

  it('a box selects the drawn entries wholly inside, or touched: equal to brute force on 60 random boxes', () => {
    const [x0, y0, x1, y1] = d.bounds!;
    for (let k = 0; k < 60; k++) {
      const w = 50 + r() * 600, h = 50 + r() * 600, bx = x0 + r() * (x1 - x0), by = y0 + r() * (y1 - y0);
      const b: [number, number, number, number] = [bx, by, bx + w, by + h];
      const inside: number[] = [], touch: number[] = [];
      for (let i = 0; i < n; i++) {
        const ss = segmentsOf(json, i);
        if (!ss.length) continue;
        if (ss.every(([a, b2, c, e]) => a >= b[0] && c >= b[0] && a <= b[2] && c <= b[2] && b2 >= b[1] && e >= b[1] && b2 <= b[3] && e <= b[3])) inside.push(i);
        if (ss.some(([a, b2, c, e]) => touches(a, b2, c, e, b))) touch.push(i);
      }
      expect(entriesInBox(d, g, b, 'inside')).toEqual(inside);
      expect(entriesInBox(d, g, b, 'touch')).toEqual(touch);
    }
  });

  it('a click in block mode on a line of a block selects that block\'s anchor; again, one level up', () => {
    const anchors = new Set(json.items.key.filter((_, i) => json.items.type[i] === 5));
    const deep = json.items.key.findIndex((k, i) => json.items.type[i] === 0 && k.split('/').length >= 3 && anchors.has(k.split('/').slice(0, 2).join('/')));
    expect(deep).toBeGreaterThanOrEqual(0);
    const key = json.items.key[deep]!;
    const chain = blockChain(d, key);
    expect(chain[0]).toBe(key.split('/').slice(0, -1).join('/'));
    expect(clickKey(d, deep, 'block', new Set(), 'replace')).toBe(chain[0]);
    if (chain.length > 1) expect(clickKey(d, deep, 'block', new Set([chain[0]!]), 'replace')).toBe(chain[1]);
    expect(clickKey(d, deep, 'item', new Set(), 'replace')).toBe(key);
  });
});

describe('the pick modes on a small nested plan', () => {
  // A: a block holding block A/B (two lines) and a line A/D; E a loose line; H a hatch of two loops; T a text on layer T
  const items: Item[] = [
    { key: 'A', layer: 'F', type: 5, pts: [[0, 0]] },
    { key: 'A/B', layer: 'F', type: 5, pts: [[1, 1]] },
    L('A/B/C1', 'F', [1, 1], [2, 1]),
    L('A/B/C2', 'F', [1, 1.5], [2, 1.5]),
    L('A/D', 'F', [5, 5], [6, 5]),
    L('E', 'W', [10, 0], [10, 3]),
    { key: 'H', layer: 'W', type: 2, pts: [[20, 0], [21, 0], [21, 1]] },
    { key: 'H', layer: 'W', type: 2, pts: [[30, 0], [31, 0], [31, 1]] },
    { key: 'T', layer: 'T', type: 4, pts: [[1.5, 1.2]] },
  ];
  const json: PlanGeometry = makePlan(items);
  const d = planData(decodePlan(json));
  const g = buildGrid(d);
  const idx = (k: string) => json.items.key.indexOf(k);

  it('block: the innermost block, then one level per click while it is selected; at the top it stays; add mode never climbs', () => {
    const e = idx('A/B/C1');
    expect(clickKey(d, e, 'block', new Set(), 'replace')).toBe('A/B');
    expect(clickKey(d, e, 'block', new Set(['A/B']), 'replace')).toBe('A');
    expect(clickKey(d, e, 'block', new Set(['A']), 'replace')).toBe('A');
    expect(clickKey(d, e, 'block', new Set(['A/B']), 'add')).toBe('A/B');
    expect(clickKey(d, idx('A/D'), 'block', new Set(), 'replace')).toBe('A');
    expect(clickKey(d, idx('E'), 'block', new Set(), 'replace')).toBe('E');      // in no block: the item itself
    expect(clickKey(d, idx('A/D'), 'item', new Set(), 'replace')).toBe('A/D');
  });

  it('nearest: within the radius only; a text is a point; an anchor is never picked', () => {
    expect(nearest(d, g, 150, 105, 10)?.entry).toBe(idx('A/B/C1'));
    expect(nearest(d, g, 150, 121, 3)?.entry).toBe(idx('T'));
    expect(nearest(d, g, 0, 0, 5)).toBeNull();                 // only the anchor A is there
    expect(nearest(d, g, 1000, 400, 50)).toBeNull();
    expect(nearest(d, g, 1000, 400, 101)?.entry).toBe(idx('E'));
  });

  it('box, item mode: whole items inside; a hatch only with all its loops; touched with alt', () => {
    expect(boxKeys(d, g, [90, 90, 210, 160], 'inside', 'item', null)).toEqual(['A/B/C1', 'A/B/C2', 'T']);
    expect(boxKeys(d, g, [90, 90, 210, 130], 'inside', 'item', null)).toEqual(['A/B/C1', 'T']);
    expect(boxKeys(d, g, [1990, -10, 2110, 110], 'inside', 'item', null)).toEqual([]);
    expect(boxKeys(d, g, [1990, -10, 2110, 110], 'touch', 'item', null)).toEqual(['H']);
    expect(boxKeys(d, g, [1990, -10, 3110, 110], 'inside', 'item', null)).toEqual(['H']);
  });

  it('box, block mode: a block once its whole subtree is inside (touching: any of it); loose items as themselves', () => {
    expect(boxKeys(d, g, [90, 90, 210, 160], 'inside', 'block', null)).toEqual(['A/B', 'T']);
    expect(boxKeys(d, g, [90, 90, 210, 130], 'inside', 'block', null)).toEqual(['T']);
    expect(boxKeys(d, g, [90, 90, 210, 130], 'touch', 'block', null)).toEqual(['A/B', 'T']);
    expect(boxKeys(d, g, [-10, -10, 700, 700], 'inside', 'block', null)).toEqual(['A/B', 'A', 'T']);
    expect(boxKeys(d, g, [990, -10, 1010, 400], 'inside', 'block', null)).toEqual(['E']);
  });

  it('box, layer-in-box: only the items of the given layer; no layer, nothing', () => {
    const F = json.layers.indexOf('F'), T = json.layers.indexOf('T');
    expect(boxKeys(d, g, [90, 90, 210, 160], 'inside', 'layer-in-box', F)).toEqual(['A/B/C1', 'A/B/C2']);
    expect(boxKeys(d, g, [90, 90, 210, 160], 'inside', 'layer-in-box', T)).toEqual(['T']);
    expect(boxKeys(d, g, [90, 90, 210, 160], 'inside', 'layer-in-box', null)).toEqual([]);
  });

  it('a view or xref block holding a quarter of the sheet or more is never a block pick', () => {
    const many: Item[] = [{ key: 'V', layer: 'W', type: 5, pts: [[0, 0]] }, { key: 'V/K', layer: 'F', type: 5, pts: [[0, 0]] }];
    for (let i = 0; i < 30; i++) many.push(L(`V/L${i}`, 'W', [i, 0], [i, 1]));
    many.push(L('V/K/1', 'F', [0, 5], [1, 5]));
    for (let i = 0; i < 30; i++) many.push(L(`X${i}`, 'W', [i, 10], [i, 11]));
    const dd = planData(decodePlan(makePlan(many)));
    expect([...dd.bigAnchors]).toEqual(['V']);
    expect(blockChain(dd, 'V/K/1')).toEqual(['V/K']);
    expect(clickKey(dd, makePlan(many).items.key.indexOf('V/L3'), 'block', new Set(), 'replace')).toBe('V/L3');
  });

  it('squared distances as the brute force has them', () => {
    expect(d2(0, 1, -1, 0, 1, 0)).toBe(1);
    expect(d2(3, 0, -1, 0, 1, 0)).toBe(4);
  });
});

// U7: near.ts (docs/upload/DESIGN.md U-8.1, U-14.3: the "close to walls" chip; ACCEPTANCE 2.3 U7 "near.ts").
import { describe, expect, it } from 'vitest';
import { decodePlan, nearLayers } from '@/plan';
import { dist2SegmentSegment } from '@/plan/near';
import { bankSettings, loadPlan, makePlan, segmentsOf, type Item } from './kit';

describe('dist2SegmentSegment', () => {
  it('0 when crossing or touching; else the nearest end against the other segment', () => {
    expect(dist2SegmentSegment(0, 0, 10, 10, 0, 10, 10, 0)).toBe(0);
    expect(dist2SegmentSegment(0, 0, 10, 0, 10, 0, 20, 5)).toBe(0);
    expect(dist2SegmentSegment(0, 0, 10, 0, 0, 3, 10, 3)).toBe(9);
    expect(dist2SegmentSegment(0, 0, 10, 0, 13, 4, 20, 4)).toBe(25);
    expect(dist2SegmentSegment(0, 0, 10, 0, 5, 2, 5, 2)).toBe(4);
    expect(dist2SegmentSegment(0, 0, 10, 0, 2, 0, 8, 0)).toBe(0);      // collinear, overlapping
  });
});

describe('nearLayers on a small plan', () => {
  const items: Item[] = [
    { key: 'W', layer: 'WALL', type: 0, pts: [[0, 0], [10, 0]] },
    { key: 'a', layer: 'NEAR', type: 0, pts: [[2, 0.5], [3, 0.5]] },                    // 0.5 m
    { key: 'b', layer: 'NEAR', type: 1, pts: [[5, 0.99], [6, 0.99], [6, 3], [5, 3]] },  // 0.99 m
    { key: 'c', layer: 'FAR', type: 0, pts: [[2, 1.5], [3, 1.5]] },                     // 1.5 m
    { key: 'h', layer: 'HATCH', type: 2, pts: [[0, -0.4], [1, -0.4], [1, -0.8]] },     // two loops, both near: one item
    { key: 'h', layer: 'HATCH', type: 2, pts: [[4, -0.4], [5, -0.4], [5, -0.8]] },
    { key: 't', layer: 'TAGS', type: 4, pts: [[7, 0.3]] },                               // a text near the wall
    { key: 'i', layer: 'BLOCKS', type: 5, pts: [[8, 0.1]] },                             // an insert anchor: not drawn
    { key: 'x', layer: 'CROSS', type: 0, pts: [[9, -5], [9, 5]] },                       // crosses the wall
    { key: 'e', layer: 'END', type: 0, pts: [[11, 0], [12, 0]] },                        // 1 m beyond its end
  ];
  const plan = decodePlan(makePlan(items));
  const L = (n: string) => plan.layers.indexOf(n);
  const named = (m: Map<number, number>) => Object.fromEntries([...m].map(([l, n]) => [plan.layers[l], n]));

  it('counts, per layer that is not a wall layer, the items with some part within the distance; one per key', () => {
    expect(named(nearLayers(plan, new Set([L('WALL')]), 1.0))).toEqual({ NEAR: 2, HATCH: 1, TAGS: 1, CROSS: 1, END: 1 });
    expect(named(nearLayers(plan, new Set([L('WALL')]), 0.5))).toEqual({ NEAR: 1, HATCH: 1, TAGS: 1, CROSS: 1 });
    expect(named(nearLayers(plan, new Set([L('WALL')]), 2))).toEqual({ NEAR: 2, FAR: 1, HATCH: 1, TAGS: 1, CROSS: 1, END: 1 });
  });

  it('wall layers are never counted; no wall layer, or one with nothing drawn, gives an empty map', () => {
    expect(named(nearLayers(plan, new Set([L('WALL'), L('NEAR')]), 1.0))).toEqual({ HATCH: 1, TAGS: 1, CROSS: 1, END: 1, FAR: 1 });
    expect(nearLayers(plan, new Set(), 1).size).toBe(0);
    expect(nearLayers(plan, new Set([L('BLOCKS')]), 1).size).toBe(0);
  });
});

describe('nearLayers on the bank plan with its wall layers, against brute force', () => {
  it('the same counts as testing every item against every wall segment', () => {
    const json = loadPlan('bank1');
    const plan = decodePlan(json);
    const roles = bankSettings().layers;
    const walls = new Set(plan.layers.map((l, i) => (roles[l] === 'wall' ? i : -1)).filter(i => i >= 0));
    expect(walls.size).toBe(2);
    const wallSegs = json.items.key.flatMap((_, i) => (walls.has(json.items.layer[i]!) ? segmentsOf(json, i) : []));
    const r2 = 100 * 100;
    const want = new Map<number, number>();
    const counted = new Set<string>();
    json.items.key.forEach((k, i) => {
      const l = json.items.layer[i]!;
      if (walls.has(l) || json.items.type[i] === 5 || counted.has(k)) return;
      const near = segmentsOf(json, i).some(([ax, ay, bx, by]) => wallSegs.some(([cx, cy, dx, dy]) => {
        if (Math.min(ax, bx) - 100 > Math.max(cx, dx) || Math.max(ax, bx) + 100 < Math.min(cx, dx)) return false;
        if (Math.min(ay, by) - 100 > Math.max(cy, dy) || Math.max(ay, by) + 100 < Math.min(cy, dy)) return false;
        return dist2SegmentSegment(ax, ay, bx, by, cx, cy, dx, dy) <= r2;
      }));
      if (near) { counted.add(k); want.set(l, (want.get(l) ?? 0) + 1); }
    });
    const got = nearLayers(plan, walls, 1.0);
    expect(Object.fromEntries([...got].sort((a, b) => a[0] - b[0]))).toEqual(Object.fromEntries([...want].sort((a, b) => a[0] - b[0])));
    // the bank's A-FLOR (the detector's kerb context) is close to walls: an `ignore` there would get the chip
    expect(got.get(plan.layers.indexOf('A-FLOR'))).toBeGreaterThan(0);
  });
});

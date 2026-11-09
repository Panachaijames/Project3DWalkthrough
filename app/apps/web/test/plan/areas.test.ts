// U7: areas.ts (docs/upload/DESIGN.md U-7.3, U-14.3: the reader's area clustering with a layer filter, in the browser).
import { describe, expect, it } from 'vitest';
import { decodePlan, proposeAreas } from '@/plan';
import type { DrawingRead } from '@/upload/contracts';
import { houseSettings, loadJson, loadPlan, makePlan, type Item } from './kit';

describe('proposeAreas: the reader\'s rule on the plan geometry', () => {
  for (const [name, drawing] of [['bank1', 'bank1'], ['sukhumvit', 'sukhumvit']] as const) {
    it(`${name}: on every layer, the same boxes in the same order as the reader's drawing.json areas`, () => {
      const plan = decodePlan(loadPlan(name));
      const read = loadJson<DrawingRead>(`fixtures/upload/drawing/${drawing}.drawing.json`);
      expect(proposeAreas(plan, new Set(plan.layers.map((_, i) => i)))).toEqual(read.areas.map(a => a.bbox));
    });
  }

  it('the house on its wall-role layers only: fewer, tighter boxes, each inside one of the two plans\' floor areas', () => {
    const plan = decodePlan(loadPlan('sukhumvit'));
    const s = houseSettings();
    const walls = new Set(plan.layers.map((l, i) => (s.layers[l] === 'wall' ? i : -1)).filter(i => i >= 0));
    const boxes = proposeAreas(plan, walls);
    expect(boxes.length).toBeGreaterThan(0);
    const areas = s.floors.map(f => (f.area.kind === 'box' ? f.area.bbox : null)).filter((b): b is [number, number, number, number] => !!b);
    expect(areas.length).toBe(2);
    for (const b of boxes) {
      const inside = areas.some(a => b[0] >= Math.floor(a[0]) - 2 && b[1] >= Math.floor(a[1]) - 2 && b[2] <= Math.ceil(a[2]) + 2 && b[3] <= Math.ceil(a[3]) + 2);
      // the wall layers also run through the elevations: a box there is allowed, but not one spanning both plans
      expect(b[2] - b[0] < 60, JSON.stringify(b)).toBe(true);
      if (!inside) expect(b[1] >= 26 || b[3] <= 6, JSON.stringify(b)).toBe(true);
    }
  });

  // the rule reads points (every n // 20-th of an item), not lines: the squares here carry a point every 0.5 m
  const sq = (k: string, x: number, y: number, w: number, h: number, layer = 'W'): Item => {
    const pts: [number, number][] = [];
    for (let t = 0; t < w; t += 0.5) pts.push([x + t, y]);
    for (let t = 0; t < h; t += 0.5) pts.push([x + w, y + t]);
    for (let t = 0; t < w; t += 0.5) pts.push([x + w - t, y + h]);
    for (let t = 0; t < h; t += 0.5) pts.push([x, y + h - t]);
    return { key: k, layer, type: 1, pts };
  };

  it('cells of 1 m, joined across gaps of up to 2 cells, boxes over 25 m2 only, top edge first then left', () => {
    const items: Item[] = [
      sq('a', 0, 0, 6, 6),                  // cells 0..6 -> box [0, 0, 7, 7]
      sq('b', 8, 0, 2, 2),                  // cells 8..10: two from a's last (6): joined -> [0, 0, 11, 7]
      sq('f', 13, 0, 2, 2),                 // cells 13..15: three from b's last: alone, 9 m2: dropped
      sq('c', 30, 20, 6, 6),                // alone, higher: first
      sq('d', 60, 0, 3, 3),                 // 4 x 4 = 16 m2: dropped
      sq('e', 0, 40, 10, 10, 'OTHER'),      // another layer
      { key: 't', layer: 'W', type: 4, pts: [[100, 100]] },
      { key: 'i', layer: 'W', type: 5, pts: [[200, 200]] },
    ];
    const plan = decodePlan(makePlan(items, [0, 0]));
    const W = new Set([plan.layers.indexOf('W')]);
    expect(proposeAreas(plan, W)).toEqual([[30, 20, 37, 27], [0, 0, 11, 7]]);
    expect(proposeAreas(plan, new Set([0, 1]))).toEqual([[0, 40, 11, 51], [30, 20, 37, 27], [0, 0, 11, 7]]);
    expect(proposeAreas(plan, new Set())).toEqual([]);
  });

  it('a plan whose origin is not a whole metre still finds metre cells of the sheet', () => {
    const plan = decodePlan(makePlan([sq('a', -3.5, -3.5, 7, 7)], [-3.5, -3.5]));
    expect(proposeAreas(plan, new Set([0]))).toEqual([[-4, -4, 4, 4]]);
    const two = decodePlan(makePlan([{ key: 'b', layer: 'W', type: 0, pts: [[-3.5, -3.5], [3.5, 3.5]] }], [-3.5, -3.5]));
    expect(proposeAreas(two, new Set([0]))).toEqual([]);           // two points, two lone cells
  });
});

// U7: decode.ts (docs/upload/DESIGN.md U-7.5, U-12.1; ACCEPTANCE 2.3 U7 "decode.ts (the fixture plans)").
import { describe, expect, it } from 'vitest';
import { decodePlan } from '@/plan';
import { blockChain, coveredBox, coveredEntries, entriesOfKey, planData, subtreeKeys } from '@/plan/decode';
import type { PlanGeometry } from '@/upload/contracts';
import { loadPlan, makePlan } from './kit';

for (const name of ['bank1', 'sukhumvit'] as const) {
  describe(`decodePlan: the ${name} fixture plan`, () => {
    const json = loadPlan(name);
    const plan = decodePlan(json);
    const d = planData(plan);
    const n = json.items.key.length;

    it('keeps every entry: key, layer, type, points, as the file has them', () => {
      expect(plan.count).toBe(n);
      expect(plan.layers).toEqual(json.layers);
      expect(plan.source).toBe(json.source);
      expect(plan.units).toBe(json.units);
      expect(plan.origin).toEqual(json.origin);
      expect(plan.quantum).toBe(json.quantum);
      for (let i = 0; i < n; i++) {
        if (plan.keyAt(i) !== json.items.key[i] || plan.layerAt(i) !== json.items.layer[i] || plan.typeAt(i) !== json.items.type[i]) {
          throw new Error(`entry ${i} differs`);
        }
      }
      expect(Array.from(d.pts)).toEqual(json.pts);
      expect(Array.from(d.first)).toEqual(json.items.first);
      expect(Array.from(d.count)).toEqual(json.items.count);
    });

    it('extents = the box of every point in sheet metres; each entry has its own box', () => {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (let i = 0; i < json.pts.length; i += 2) {
        x0 = Math.min(x0, json.pts[i]!); x1 = Math.max(x1, json.pts[i]!);
        y0 = Math.min(y0, json.pts[i + 1]!); y1 = Math.max(y1, json.pts[i + 1]!);
      }
      const [ox, oy] = json.origin, q = json.quantum;
      plan.extents.forEach((v, k) => expect(v).toBeCloseTo([ox + x0 * q, oy + y0 * q, ox + x1 * q, oy + y1 * q][k]!, 9));
      expect(d.bounds).toEqual([x0, y0, x1, y1]);
      for (let i = 0; i < n; i += 97) {
        const f = json.items.first[i]!, c = json.items.count[i]!;
        const xs = Array.from({ length: c }, (_, k) => json.pts[2 * (f + k)]!), ys = Array.from({ length: c }, (_, k) => json.pts[2 * (f + k) + 1]!);
        expect(Array.from(d.box.subarray(4 * i, 4 * i + 4))).toEqual([Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]);
      }
    });

    it('refOf gives each key its own entry\'s sig, rsig, element id and layer (a hatch\'s loops share them); unknown keys null', () => {
      const firstOf = new Map<string, number>();
      json.items.key.forEach((k, i) => { if (!firstOf.has(k)) firstOf.set(k, i); });
      for (const [k, i] of firstOf) {
        const e = json.items.eid[i]!;
        expect(plan.refOf(k)).toEqual({
          sig: json.items.sig[i], rsig: json.items.rsig[i], elementId: e >= 0 ? json.elementIds[e] : null, layer: json.layers[json.items.layer[i]!],
        });
      }
      expect(plan.refOf('no such key')).toBeNull();
      expect(plan.refOf('')).toBeNull();
    });

    it('a key repeats only for a hatch\'s loops (types 2 / 3, one layer); entriesOfKey lists them all', () => {
      const groups = new Map<string, number[]>();
      json.items.key.forEach((k, i) => groups.set(k, [...(groups.get(k) ?? []), i]));
      for (const [k, list] of groups) {
        expect(entriesOfKey(d, k)).toEqual(list);
        if (list.length > 1) {
          expect(list.every(i => json.items.type[i] === 2 || json.items.type[i] === 3), k).toBe(true);
          expect(new Set(list.map(i => json.items.layer[i])).size).toBe(1);
        }
      }
      expect(d.sortedKeys.length).toBe(groups.size);
    });

    it('the subtree of an INSERT anchor is the anchor and every key starting with key + "/", nothing else', () => {
      const anchors = json.items.key.filter((_, i) => json.items.type[i] === 5);
      expect(anchors.length).toBeGreaterThan(10);
      const keys = [...new Set(json.items.key)];
      for (const a of anchors.slice(0, 40)) {
        expect(subtreeKeys(d, a).sort()).toEqual(keys.filter(k => k === a || k.startsWith(a + '/')).sort());
        const want = json.items.key.map((k, i) => (k === a || k.startsWith(a + '/') ? i : -1)).filter(i => i >= 0);
        expect(coveredEntries(d, a).sort((x, y) => x - y)).toEqual(want);
      }
    });

    it('blockChain: the anchors that hold an item, innermost first, by key prefix', () => {
      const anchors = new Set(json.items.key.filter((_, i) => json.items.type[i] === 5));
      const nested = json.items.key.filter((k, i) => json.items.type[i] !== 5 && k.split('/').length >= 3).slice(0, 50);
      expect(nested.length).toBeGreaterThan(0);
      for (const k of nested) {
        const parts = k.split('@')[0]!.split('/');
        const want: string[] = [];
        for (let j = parts.length - 1; j >= 1; j--) { const p = parts.slice(0, j).join('/'); if (anchors.has(p) && !d.bigAnchors.has(p)) want.push(p); }
        expect(blockChain(d, k)).toEqual(want);
      }
    });

    it('fits the view to every point, or to the 1 - 99 % box when stray points make the sheet four times larger', () => {
      expect(d.fitBox).not.toBeNull();
      const [bx0, by0, bx1, by1] = d.bounds!, [fx0, fy0, fx1, fy1] = d.fitBox!;
      expect(fx0).toBeGreaterThanOrEqual(bx0); expect(fy0).toBeGreaterThanOrEqual(by0);
      expect(fx1).toBeLessThanOrEqual(bx1); expect(fy1).toBeLessThanOrEqual(by1);
      if (name === 'bank1') expect(d.fitBox).toEqual(d.bounds);
      else expect((fx1 - fx0) * (fy1 - fy0)).toBeLessThan((bx1 - bx0) * (by1 - by0) / 4);   // the house sheet: stray items far out
    });
  });
}

describe('decodePlan: the frame and the checks', () => {
  const items = [
    { key: 'A', layer: 'W', type: 5, pts: [[1, 1]] as [number, number][] },
    { key: 'A/1', layer: 'W', type: 0, pts: [[0, 0], [2, 0]] as [number, number][], eid: '123456' },
    { key: 'A/2@9', layer: 'T', type: 4, pts: [[1, 2]] as [number, number][] },
    { key: 'H', layer: 'W', type: 2, pts: [[0, 0], [1, 0], [1, 1]] as [number, number][] },
    { key: 'H', layer: 'W', type: 2, pts: [[3, 3], [4, 3], [4, 4]] as [number, number][] },
  ];

  it('works in local quanta from the origin: a plan at y = -3,500 m holds the same quanta as one at 0', () => {
    const a = planData(decodePlan(makePlan(items, [0, 0])));
    const b = planData(decodePlan(makePlan(items.map(it => ({ ...it, pts: it.pts.map(([x, y]) => [x, y - 3500] as [number, number]) })), [0, -3500])));
    expect(Array.from(b.pts)).toEqual(Array.from(a.pts));
    expect(b.toSheet(100, 200)).toEqual([1, -3498]);
    expect(b.toLocal(1, -3498)).toEqual([100, 200]);
    expect(b.plan.extents).toEqual([0, -3500, 4, -3496]);
  });

  it('the carried data survives a spread copy of the plan (the screens may copy it)', () => {
    const plan = decodePlan(makePlan(items));
    expect(planData({ ...plan })).toBe(planData(plan));
    expect(() => planData({ ...plan, ...{} } as never)).not.toThrow();
    expect(() => planData({ source: '', units: 'mm', origin: [0, 0], quantum: 0.01, layers: [], extents: [0, 0, 0, 0], count: 0,
      keyAt: () => '', layerAt: () => 0, typeAt: () => 0, refOf: () => null })).toThrow(/decodePlan/);
  });

  it('refOf: element id from the file, rsig empty without one', () => {
    const plan = decodePlan(makePlan(items));
    expect(plan.refOf('A/1')).toEqual({ sig: 'sig-A/1', rsig: 'rsig-A/1', elementId: '123456', layer: 'W' });
    expect(plan.refOf('H')).toEqual({ sig: 'sig-H', rsig: '', elementId: null, layer: 'W' });
    const d = planData(plan);
    expect(entriesOfKey(d, 'H')).toEqual([3, 4]);
    expect(coveredEntries(d, 'A')).toEqual([0, 1, 2]);
    expect(blockChain(d, 'A/2@9')).toEqual(['A']);
    expect(coveredBox(d, 'A')).toEqual([0, 0, 200, 200]);          // the anchor's point is not drawn: the lines' and text's box
  });

  const bad: [string, (j: PlanGeometry) => PlanGeometry, RegExp][] = [
    ['parallel arrays of other lengths', j => ({ ...j, items: { ...j.items, sig: j.items.sig.slice(1) } }), /items.sig/],
    ['an odd number of point values', j => ({ ...j, pts: [...j.pts, 1] }), /odd/],
    ['a point that is not whole', j => ({ ...j, pts: j.pts.map((v, i) => (i === 3 ? v + 0.5 : v)) }), /whole number/],
    ['points outside pts', j => ({ ...j, items: { ...j.items, count: j.items.count.map((c, i) => (i === 4 ? c + 1 : c)) } }), /outside pts/],
    ['a layer out of range', j => ({ ...j, items: { ...j.items, layer: j.items.layer.map((l, i) => (i === 1 ? 9 : l)) } }), /layer 9/],
    ['a type out of range', j => ({ ...j, items: { ...j.items, type: j.items.type.map((t, i) => (i === 1 ? 7 : t)) } }), /type 7/],
    ['an element id index out of range', j => ({ ...j, items: { ...j.items, eid: j.items.eid.map((e, i) => (i === 1 ? 5 : e)) } }), /element id/],
    ['no quantum', j => ({ ...j, quantum: 0 }), /quantum/],
  ];
  for (const [what, mutate, msg] of bad) {
    it(`refuses ${what}`, () => {
      expect(() => decodePlan(mutate(makePlan(items)))).toThrow(msg);
    });
  }

  it('an empty plan decodes (no points: the extents are the origin)', () => {
    const p = decodePlan(makePlan([], [5, 6]));
    expect(p.count).toBe(0);
    expect(p.extents).toEqual([5, 6, 5, 6]);
    expect(planData(p).fitBox).toBeNull();
  });
});

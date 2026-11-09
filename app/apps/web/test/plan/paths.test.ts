// U7: paths.ts (docs/upload/DESIGN.md U-12.1; ACCEPTANCE 2.3 U7 "paths.ts (one path per layer and type, built in local
// quanta from origin: a plan at y = -3,500 m picks the same keys as one at 0)").
import { describe, expect, it } from 'vitest';
import { decodePlan, type PlanCanvasProps } from '@/plan';
import { PlanController } from '@/plan/controller';
import { planData } from '@/plan/decode';
import { buildLayerPaths, pathOfEntries, textAnchors } from '@/plan/paths';
import type { PlanGeometry } from '@/upload/contracts';
import { FakeCtx, FakePath, loadPlan, rng, shifted } from './kit';

for (const name of ['bank1', 'sukhumvit'] as const) {
  describe(`paths of the ${name} plan`, () => {
    const json = loadPlan(name);
    const d = planData(decodePlan(json));
    const paths = buildLayerPaths(d, () => new FakePath());

    it('one path per (layer, type) that has lines or fills; texts and insert anchors are no path', () => {
      const want = new Set<string>();
      json.items.type.forEach((t, i) => { if (t <= 3 && json.items.count[i]! >= 2) want.add(`${json.items.layer[i]}:${t}`); });
      expect(paths.map(p => `${p.layer}:${p.type}`).sort()).toEqual([...want].sort());
      expect(new Set(paths.map(p => `${p.layer}:${p.type}`)).size).toBe(paths.length);
      const entries = json.items.type.filter((t, i) => t <= 3 && json.items.count[i]! >= 2).length;
      expect(paths.reduce((a, p) => a + p.entries, 0)).toBe(entries);
    });

    it('built in the file\'s own integer quanta: every point as stored, a subpath per entry, closed for types 1 - 3', () => {
      let moves = 0, closes = 0, points = 0;
      for (const p of paths) {
        for (const c of p.path.cmds) {
          if (c[0] === 'moveTo') moves++;
          if (c[0] === 'closePath') closes++;
          if (c[0] === 'moveTo' || c[0] === 'lineTo') {
            points++;
            expect(Number.isInteger(c[1]) && Number.isInteger(c[2])).toBe(true);
          }
        }
      }
      const drawn = json.items.type.map((t, i) => (t <= 3 && json.items.count[i]! >= 2 ? i : -1)).filter(i => i >= 0);
      expect(moves).toBe(drawn.length);
      expect(closes).toBe(drawn.filter(i => json.items.type[i] !== 0).length);
      expect(points).toBe(drawn.reduce((a, i) => a + json.items.count[i]!, 0));
      const lim = json.pts.reduce((a, v) => Math.max(a, Math.abs(v)), 0);
      expect(lim).toBeLessThan(2 ** 24);                    // exact in float32
    });

    it('each path\'s box holds its entries', () => {
      for (const p of paths) {
        expect(p.box[0]).toBeLessThanOrEqual(p.box[2]);
        expect(p.box[1]).toBeLessThanOrEqual(p.box[3]);
      }
      const all = paths.reduce<[number, number, number, number]>((b, p) => [Math.min(b[0], p.box[0]), Math.min(b[1], p.box[1]),
        Math.max(b[2], p.box[2]), Math.max(b[3], p.box[3])], [Infinity, Infinity, -Infinity, -Infinity]);
      expect(all[0]).toBeGreaterThanOrEqual(d.bounds![0]);
      expect(all[2]).toBeLessThanOrEqual(d.bounds![2]);
    });

    it('text anchors per layer as points (drawn as dots, never as their text)', () => {
      const texts = textAnchors(d);
      const want = json.items.type.filter(t => t === 4).length;
      expect([...texts.values()].reduce((a, xy) => a + xy.length / 2, 0)).toBe(want);
    });
  });
}

describe('the local frame: a plan at y = -3,500 m (the suite\'s sheet) draws and picks like one at 0', () => {
  const at0 = loadPlan('bank1');
  const far: PlanGeometry = shifted(at0, 0, -3500);

  it('the same path commands, whatever the origin', () => {
    const a = buildLayerPaths(planData(decodePlan(at0)), () => new FakePath());
    const b = buildLayerPaths(planData(decodePlan(far)), () => new FakePath());
    expect(b.map(p => p.path.cmds)).toEqual(a.map(p => p.path.cmds));
  });

  const mount = (json: PlanGeometry) => {
    const plan = decodePlan(json);
    const picked: string[][] = [];
    const ctx = new FakeCtx();
    const props: PlanCanvasProps = {
      plan, roleOf: () => 'wall', selected: new Set(), setAside: new Set(), tool: 'select', pick: 'item',
      onSelect: keys => { picked.push(keys); },
    };
    const c = new PlanController(document.createElement('canvas'), null, props, ctx as never, () => new FakePath());
    c.resize(1400, 880, 1);
    c.drawNow();
    return { c, ctx, picked, plan };
  };

  it('the same view, small transforms, the same keys picked at the same sheet points (300 clicks, item and block modes)', () => {
    const A = mount(at0), B = mount(far);
    expect(B.c.view).toEqual(A.c.view);
    const ta = A.ctx.transforms.find(t => t[0] !== 1)!, tb = B.ctx.transforms.find(t => t[0] !== 1)!;
    expect(tb).toEqual(ta);
    expect(Math.abs(ta[4]!) + Math.abs(ta[5]!)).toBeLessThan(5000);       // device pixels, never millions
    const r = rng(3);
    for (const pick of ['item', 'block'] as const) {
      for (const m of [A, B]) m.c.setProps({ ...m.c.props, pick });
      for (let k = 0; k < 150; k++) {
        const px = 100 + r() * 1200, py = 50 + r() * 780;
        const sa = A.c.screenToSheet(px, py)!, sb = B.c.screenToSheet(px, py)!;
        expect(sb[0]).toBeCloseTo(sa[0], 6);
        expect(sb[1]).toBeCloseTo(sa[1] - 3500, 6);
        A.c.click(px, py); B.c.click(px, py);
      }
      expect(B.picked).toEqual(A.picked);
      expect(A.picked.filter(k => k.length).length).toBeGreaterThan(10);
      A.picked.length = 0; B.picked.length = 0;
    }
    A.c.dispose(); B.c.dispose();
  });

  it('pathOfEntries draws exactly the given entries', () => {
    const d = planData(decodePlan(at0));
    const i = at0.items.type.findIndex((t, k) => t === 1 && at0.items.count[k]! >= 3);
    const p = pathOfEntries(d, [i], () => new FakePath());
    expect(p.cmds[0]).toEqual(['moveTo', at0.pts[2 * at0.items.first[i]!], at0.pts[2 * at0.items.first[i]! + 1]]);
    expect(p.cmds.at(-1)).toEqual(['closePath']);
    expect(p.cmds.length).toBe(at0.items.count[i]! + 1);
  });
});

// Builder D: the replay's geometry and colours (build_replay.js segGeometry, quadGeometries, ringGeometries, bounds,
// make / unmake): vertex layouts, the plan -> three.js frame (x, z = -y), what the framing reads, the defaults of
// DESIGN.md 7.2, and that unmake takes everything out again and frees it.
import { Color, Group, LineBasicMaterial, LineSegments, Mesh, MeshBasicMaterial, Plane, Scene, Vector3 } from 'three';
import { describe, expect, it, vi } from 'vitest';
import type { FloorRecord } from '../../../src/contracts';
import { DEFAULT_REPLAY_TEXTS } from '../../../src/model/presentation';
import {
  lineBounds, makeReplayObjects, partBounds, quadGeometries, replayColors, ringGeometries, segGeometry, unmakeReplayObjects,
  type ReplayFloorRt,
} from '../../../src/replay/objects';
import { stages } from './helpers';

const pos = (g: { getAttribute(n: string): { array: ArrayLike<number> } }) => Array.from(g.getAttribute('position').array);

describe('replay geometry', () => {
  it('segGeometry: flat x1, y1, x2, y2 -> segments at height y, plan y -> -z; a trailing partial segment is dropped', () => {
    expect(pos(segGeometry([1, 2, 3, 4, 5, 6, 7, 8, 9, 9], 0.03))).toEqual([1, 0.03, -2, 3, 0.03, -4, 5, 0.03, -6, 7, 0.03, -8].map(Math.fround));
  });

  it('quadGeometries: two triangles and four edges per quad', () => {
    const [tri, edge] = quadGeometries([0, 0, 2, 0, 2, 1, 0, 1, /* second */ 5, 5, 6, 5, 6, 6, 5, 6], 0.01);
    expect(tri.getAttribute('position').count).toBe(12);
    expect(edge.getAttribute('position').count).toBe(16);
    expect(pos(tri).slice(0, 18)).toEqual([0, 0.01, -0, 2, 0.01, -0, 2, 0.01, -1, 0, 0.01, -0, 2, 0.01, -1, 0, 0.01, -1].map(Math.fround));
    expect(pos(edge).slice(0, 6)).toEqual([0, 0.01, -0, 2, 0.01, -0].map(Math.fround));
  });

  it('ringGeometries: a flat fill with its hole at height y, and every loop outlined', () => {
    const o: [number, number][] = [[0, 0], [4, 0], [4, 4], [0, 4]], h: [number, number][][] = [[[1, 1], [3, 1], [3, 3], [1, 3]]];
    const [fill, line] = ringGeometries([{ o, h }], 0.015);
    const p = pos(fill);
    for (let i = 1; i < p.length; i += 3) expect(p[i]).toBeCloseTo(0.015, 6);
    fill.computeBoundingBox();
    expect(fill.boundingBox!.min.toArray().map(v => Math.round(v * 1000) / 1000)).toEqual([0, 0.015, -4]);
    expect(fill.boundingBox!.max.toArray().map(v => Math.round(v * 1000) / 1000)).toEqual([4, 0.015, 0]);
    expect(fill.index!.count / 3).toBe(8);                    // a square ring: 8 triangles
    expect(line.getAttribute('position').count).toBe(16);     // 4 + 4 segments
  });

  it('frames a floor by its kept lines (noise left out), or by its parts when it has none', () => {
    expect(lineBounds({ wall: [0, 1, 4, 5], door: [-2, 3, 1, 1], noise: [900, 900, -900, -900] })).toEqual({ x0: -2, x1: 4, y0: 1, y1: 5 });
    expect(lineBounds({ noise: [1, 1, 2, 2] }).x0).toBe(Infinity);
    const parts = [{ floor: 'a', o: [[1, 2], [3, 2], [3, 6]] as [number, number][] }, { floor: 'b', o: [[50, 50], [51, 50], [51, 51]] as [number, number][] }];
    expect(partBounds(parts, 'a')).toEqual({ x0: 1, x1: 3, y0: 2, y1: 6 });
    expect(partBounds(parts, 'zz')).toEqual({ x0: 0, x1: 0, y0: 0, y1: 0 });
  });
});

describe('replayColors (DESIGN.md 7.2)', () => {
  it('uses the bank page values when the stages file has none', () => {
    expect(replayColors({})).toEqual(DEFAULT_REPLAY_TEXTS.colors);
    expect(replayColors({})).toEqual({
      wall: '#7a6650', glass: '#2f86a8', door: '#c0702a', stair: '#2e8b47', railing: '#9b3fa0',
      ink: '#3b4148', faint: '#a4acb4', piece: '#cfc2b0', pieceEdge: '#8a7a66', run: '#e3ddd3', runEdge: '#6f675d',
    });
  });

  it('with colours given: exactly those over the replay\'s own (a category the page did not colour stays ink)', () => {
    const c = replayColors({ colors: { wall: '#7a6650', glass: '#3f8fb0', door: '#c0702a', railing: '#9b3fa0' } });
    expect(c.glass).toBe('#3f8fb0');
    expect(c.stair).toBeUndefined();
    expect([c.ink, c.faint, c.piece, c.pieceEdge, c.run, c.runEdge]).toEqual(['#3b4148', '#a4acb4', '#cfc2b0', '#8a7a66', '#e3ddd3', '#6f675d']);
    expect(replayColors({ colors: { ink: '#000000' } }).ink).toBe('#000000');
  });
});

describe('makeReplayObjects / unmakeReplayObjects', () => {
  const data = stages('bank-v2');
  const floor = (key: string, level: number): ReplayFloorRt => {
    const group = new Group();
    const rec = { key, name: key, level, modelLevel: level, wallHeight: 3.7, stack: 'main', group, colliders: [], walkables: [], surfaces: [], late: [], rise: [] } as FloorRecord;
    const sf = data.floors[key]!;
    return {
      rec, key, name: key, level, height: 3.7, sheet: sf.sheet, lines: sf.lines, pieces: sf.pieces, rings: sf.rings,
      b: lineBounds(sf.lines), u: { uRise: { value: 1 }, uBase: { value: level } },
    };
  };

  it('puts a "build replay" group into each floor group and the scan bar into the scene; unmake takes all out and frees it', () => {
    const scene = new Scene(), floors = [floor('L1', 0), floor('L2', 3.7)];
    for (const f of floors) scene.add(f.rec.group);
    const scanPlane = new Plane(new Vector3(-1, 0, 0), 0), sweepPlane = new Plane(new Vector3(-1, 0, 0), 0);
    const made = makeReplayObjects({ scene, floors, colors: replayColors(data), accent: '#2f6f8f', scanPlane, sweepPlane });
    expect(made.scan.parent).toBe(scene);
    expect(made.scan.visible).toBe(false);
    expect(made.scan.renderOrder).toBe(7);
    expect((made.scan.material as MeshBasicMaterial).color.getHexString()).toBe(new Color('#2f6f8f').getHexString());
    made.floors.forEach((F, i) => {
      expect(F.g.parent).toBe(floors[i]!.rec.group);
      expect(F.g.name).toBe('build replay');
      expect(Object.keys(F.lines)).toEqual(Object.keys(data.floors[F.f.key]!.lines).filter(c => data.floors[F.f.key]!.lines[c]!.length));
      for (const [cat, L] of Object.entries(F.lines)) {
        expect(L.faint.geometry).toBe(L.ink.geometry);
        expect([L.faint.renderOrder, L.ink.renderOrder]).toEqual([1, 2]);
        expect((L.ink.material as LineBasicMaterial).clippingPlanes).toEqual([scanPlane]);
        expect((L.faint.material as LineBasicMaterial).opacity).toBe(cat === 'noise' ? 0.35 : 0.5);
        const want = cat === 'noise' ? DEFAULT_REPLAY_TEXTS.colors.faint : DEFAULT_REPLAY_TEXTS.colors[cat] ?? DEFAULT_REPLAY_TEXTS.colors.ink;
        expect(L.color.getHexString()).toBe(new Color(want).getHexString());
        // y = the floor's model level + 0.03
        expect(L.ink.geometry.getAttribute('position').getY(0)).toBeCloseTo(F.f.level + 0.03, 5);
      }
      for (const p of F.pieces) {
        expect([p.m.renderOrder, p.e.renderOrder]).toEqual([3, 4]);
        expect((p.m.material as MeshBasicMaterial).clippingPlanes).toEqual([sweepPlane]);
        expect((p.m.material as MeshBasicMaterial).opacity).toBe(0);
      }
      for (const r of F.runs) expect([r.m.renderOrder, r.e.renderOrder]).toEqual([5, 6]);
      expect(F.pieces.length).toBe(Object.values(data.floors[F.f.key]!.pieces).filter(q => q.length).length);
      expect(F.runs.length).toBe(Object.values(data.floors[F.f.key]!.rings).filter(q => q.length).length);
    });
    const disposed = vi.fn();
    const things: { dispose(): void; addEventListener(t: string, f: () => void): void }[] = [made.scan.geometry, made.scan.material as MeshBasicMaterial];
    for (const F of made.floors) F.g.traverse(n => { const m = n as Mesh | LineSegments; if (m.geometry) things.push(m.geometry, m.material as MeshBasicMaterial); });
    for (const t of new Set(things)) t.addEventListener('dispose', disposed);
    unmakeReplayObjects(made, scene);
    expect(made.scan.parent).toBeNull();
    for (const f of floors) expect(f.rec.group.children.length).toBe(0);
    expect(disposed.mock.calls.length).toBeGreaterThanOrEqual(new Set(things).size);
  });
});

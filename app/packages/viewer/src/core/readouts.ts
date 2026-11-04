// upHit, downHit, rayHit (the bank and hotel pages) and cast (the house page): read-outs of what Walk would meet, for tests
// and the hover label (DESIGN.md 11.7). Owner: builder A. Plan (x, y) is three.js (x, z = -y); heights above the floor's
// level are measured from the level Walk uses now (FloorRecord.level, which Build settings change). Only the floor's
// visible colliders count (mesh.visible: the ticks and the furniture's show tick switch them), first hit only.
import { Raycaster, Vector3, type Mesh } from 'three';
import type { CreateReadouts, ReadoutsApi } from '../contracts';

export const createReadouts: CreateReadouts = ctx => {
  const ray = new Raycaster();
  ray.firstHitOnly = true;
  const origin = new Vector3(), dir = new Vector3();
  const visible = (key: string): Mesh[] => (ctx.floorByKey.get(key)?.colliders ?? []).filter(m => m.visible);
  const first = (key: string, far: number) => {
    const cols = visible(key);
    if (!cols.length) return null;
    // the world matrices as they are now (a Build settings change or a typed height moves meshes between two frames)
    for (const m of cols) m.updateWorldMatrix(true, false);
    ray.set(origin, dir);
    ray.near = 0;
    ray.far = far;
    return ray.intersectObjects(cols, false)[0] ?? null;
  };
  const levelOf = (key: string) => ctx.floorByKey.get(key)?.level;

  const api: ReadoutsApi = {
    upHit(key, x, y, h0 = 1.0) {
      const level = levelOf(key);
      if (level === undefined) return null;
      origin.set(x, level + h0, -y); dir.set(0, 1, 0);
      const hit = first(key, 20);
      return hit ? hit.distance + h0 : null;
    },
    downHit(key, x, y, h0 = 3.0) {
      const level = levelOf(key);
      if (level === undefined) return null;
      origin.set(x, level + h0, -y); dir.set(0, -1, 0);
      const hit = first(key, 8);
      return hit ? h0 - hit.distance : null;
    },
    rayHit(key, x, y, h, dx, dy, far = 3) {
      const level = levelOf(key);
      if (level === undefined) return null;
      const n = Math.hypot(dx, dy) || 1;
      origin.set(x, level + h, -y); dir.set(dx / n, 0, -dy / n);
      const hit = first(key, far);
      return hit ? { d: hit.distance, name: hit.object.name } : null;
    },
    cast(key, p, d, far) {
      if (!ctx.floorByKey.has(key)) return null;
      origin.set(p[0], p[1], p[2]); dir.set(d[0], d[1], d[2]).normalize();
      const hit = first(key, far);
      return hit ? { d: hit.distance, name: hit.object.name } : null;
    },
  };
  return api;
};

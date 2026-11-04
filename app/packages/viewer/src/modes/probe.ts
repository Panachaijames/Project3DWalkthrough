// Probe read-outs for tests and debugging (DESIGN.md 12 "Probe read-outs"): window.__viewer.probe with testHook, exactly
// the prototype's (viewer_modes.js `probe`). Owner: builder B.
import { Vector3 } from 'three';
import type { ModesProbe, ModesState, ViewerContext } from '../contracts';
import { D2R, OPEN_HEIGHT, PROBE_OPEN_FAR, PROBE_STEP } from './state';
import type { Walker } from './walk';

export function createProbe(ctx: Pick<ViewerContext, 'camera' | 'floors'>, s: ModesState, walk: Walker, applyCamera: () => void): ModesProbe {
  const camera = ctx.camera;
  return {
    open: deg => walk.openAhead(deg === undefined ? s.yaw : deg * D2R, PROBE_OPEN_FAR),
    clearance: () => walk.clearance(s.pos, s.floor),
    onFloor: () => walk.onFloor(s.pos, s.floor),
    crosses: (x0, z0, x1, z1) => {            // is there a wall between two points (chest height, current floor)?
      const f = s.floor, cols = walk.visibleColliders(f), d = new Vector3(x1 - x0, 0, z1 - z0), len = d.length();
      if (!cols.length || len < 1e-6) return false;
      walk.ray.set(new Vector3(x0, f.level + OPEN_HEIGHT, z0), d.divideScalar(len));
      walk.ray.far = len;
      return walk.ray.intersectObjects(cols, false).length > 0;
    },
    walk: (deg, metres) => {                  // walk straight (as W would, 5 cm steps) and return how far you got
      const yaw = deg * D2R, d = new Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)).multiplyScalar(PROBE_STEP), start = s.pos.clone();
      for (let t = 0; t < metres; t += PROBE_STEP) walk.walkMove(d.clone());
      applyCamera();
      return s.pos.distanceTo(start);
    },
    visible: () => ctx.floors.filter(f => f.group.visible).map(f => f.key),
    camera: () => ({
      x: camera.position.x, y: camera.position.y, z: camera.position.z, fov: camera.fov, rx: camera.rotation.x,
      offsetY: camera.view && camera.view.enabled ? camera.view.offsetY : null,
      dir: camera.getWorldDirection(new Vector3()).toArray(),
    }),
  };
}

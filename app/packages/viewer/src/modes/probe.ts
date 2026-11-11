// Probe read-outs for tests and debugging (DESIGN.md 12 "Probe read-outs"): window.__viewer.probe with testHook, exactly
// the prototype's (viewer_modes.js `probe`). Owner: builder B.
//
// With climbing on (a model with `stairways`; rooms/DESIGN.md R-9.8; rooms step R4): every read-out is measured from the
// foot (walk.base(), walk.bodies()); a probe call starts from where the test put the walker (walk.restart(): when
// s.pos.x / z or s.floor are not where the walker last put them, the foot goes back to the current floor's level, a
// teleport); `walk` returns the horizontal distance and never eases the eye; `foot` and `ground` are the walker's own.
// On a model without stairways nothing differs from before: base() is the floor's level, bodies() its visible colliders,
// restart() does nothing.
import { Vector3 } from 'three';
import type { ModesProbe, ModesState, ViewerContext } from '../contracts';
import { D2R, OPEN_HEIGHT, PROBE_OPEN_FAR, PROBE_STEP } from './state';
import type { Walker } from './walk';

export function createProbe(ctx: Pick<ViewerContext, 'camera' | 'floors'>, s: ModesState, walk: Walker, applyCamera: () => void): ModesProbe {
  const camera = ctx.camera;
  return {
    open: deg => { walk.restart(); return walk.openAhead(deg === undefined ? s.yaw : deg * D2R, PROBE_OPEN_FAR); },
    clearance: () => { walk.restart(); return walk.clearance(s.pos, s.floor); },
    onFloor: () => { walk.restart(); return walk.onFloor(s.pos, s.floor); },
    crosses: (x0, z0, x1, z1) => {            // is there a wall between two points (chest height, where the walker stands)?
      walk.restart();
      const cols = walk.bodies(), d = new Vector3(x1 - x0, 0, z1 - z0), len = d.length();
      if (!cols.length || len < 1e-6) return false;
      walk.ray.set(new Vector3(x0, walk.base() + OPEN_HEIGHT, z0), d.divideScalar(len));
      walk.ray.far = len;
      return walk.ray.intersectObjects(cols, false).length > 0;
    },
    walk: (deg, metres) => {                  // walk straight (as W would, 5 cm steps) and return how far you got
      walk.restart();
      const yaw = deg * D2R, d = new Vector3(-Math.sin(yaw), 0, -Math.cos(yaw)).multiplyScalar(PROBE_STEP), start = s.pos.clone();
      for (let t = 0; t < metres; t += PROBE_STEP) walk.walkMove(d.clone());
      if (walk.climbing) s.pos.y = s.foot + s.eye;      // a probe call never eases the eye
      applyCamera();
      return walk.climbing ? Math.hypot(s.pos.x - start.x, s.pos.z - start.z) : s.pos.distanceTo(start);
    },
    foot: () => { walk.restart(); return s.foot; },
    ground: () => { walk.restart(); return walk.ground(s.pos); },
    visible: () => ctx.floors.filter(f => f.group.visible).map(f => f.key),
    camera: () => ({
      x: camera.position.x, y: camera.position.y, z: camera.position.z, fov: camera.fov, rx: camera.rotation.x,
      offsetY: camera.view && camera.view.enabled ? camera.view.offsetY : null,
      dir: camera.getWorldDirection(new Vector3()).toArray(),
    }),
  };
}

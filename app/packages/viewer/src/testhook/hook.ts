// window.__viewer / __host / __build / __walkthrough (DESIGN.md 11.7, 18.18): the prototypes' read-outs, kept by name so
// the ported browser checks change little. Owner: builder A. Only with ViewerOptions.testHook (?test=1 in the offline file,
// VITE_WTV_TEST_HOOK=1 in the staff app). Everything reads the live objects (the modes' state, the floor records' arrays),
// never copies; dispose() deletes each property that is still this viewer's.
//   __viewer      the modes: mode, state, probe, setMode, goToFloor, takePhoto, lock
//   __host        FL (MODEL levels, the prototypes' records), floors (the FloorRecords: WALK levels), model, openings,
//                 probes, labels, the read-outs, furniture, camera, controls, pictures, rise, plinths, groups, fitted
//   __build       the replay (or null)
//   __walkthrough a three.js subset (the bundle has no import map), the Viewer, the version, live(), created(), gpu()
import { Box3, Color, Euler, MathUtils, Matrix4, Plane, Quaternion, Raycaster, Vector2, Vector3, type Group, type Mesh } from 'three';
import type {
  InstallTestHook, RiseItem, TestHookBuild, TestHookFloor, TestHookHost, TestHookThree, TestHookViewer, TestHookWalkthrough,
} from '../contracts';
import { counters } from '../core/live';
import { VIEWER_VERSION } from '../version';

export const TEST_THREE: TestHookThree = { Vector2, Vector3, Raycaster, Box3, Plane, Matrix4, Quaternion, Euler, MathUtils, Color };

export const installTestHook: InstallTestHook = (ctx, viewer) => {
  if (typeof window === 'undefined') return;
  const modes = () => ctx.modes;
  const hookViewer: TestHookViewer = {
    get mode() { return modes().mode; },
    get state() { return modes().state; },
    get probe() { return modes().probe; },
    setMode: (mode, opt) => modes().setMode(mode, opt),
    goToFloor: key => modes().goToFloor(key),
    takePhoto: () => modes().takePhoto(),
    lock: on => modes().lock(on),
  };

  const FL: Record<string, TestHookFloor> = {};
  const rise: Record<string, RiseItem[]> = {};
  const groups: Record<string, Group> = {};
  for (const f of ctx.floors) {
    FL[f.key] = {
      key: f.key, name: f.name, level: f.modelLevel, group: f.group,
      colliders: f.colliders, walkables: f.walkables, late: f.late, rise: f.rise,
      surfaces: f.surfaces,                               // v2: what the foot-based walker stands on ([] on an old model)
    };
    rise[f.key] = f.rise;
    groups[f.key] = f.group;
  }
  const pictures = ctx.pictures;
  const host: TestHookHost = {
    FL,
    floors: ctx.floors,
    model: ctx.model,
    openings: ctx.model.openings,
    probes: ctx.model.probes,
    get labels() { return ctx.labels.labels; },
    upHit: (...a) => ctx.readouts.upHit(...a),
    downHit: (...a) => ctx.readouts.downHit(...a),
    rayHit: (...a) => ctx.readouts.rayHit(...a),
    cast: (...a) => ctx.readouts.cast(...a),
    get furniture() { return ctx.furniture; },
    camera: ctx.camera,
    controls: ctx.controls,
    pictures: pictures ? { objs: pictures.sheets as Mesh[], ready: pictures.ready, src: pictures.src, show: () => pictures.sync() } : null,
    rise,
    plinths: ctx.built.plinths,
    groups,
    fitted: ctx.built.fitted,
  };

  const replay = () => ctx.replay;
  const build: TestHookBuild | null = ctx.replay ? {
    get phase() { return replay()!.phase; },
    get state() { return replay()!.state; },
    get steps() { return replay()!.steps; },
    generate: () => replay()!.generate(),
    skip: () => replay()!.skip(),
    openSettings: () => replay()!.openSettings(),
    seek: T => replay()!.seek(T),
  } : null;

  const walkthrough: TestHookWalkthrough = {
    THREE: TEST_THREE,
    viewer,
    version: VIEWER_VERSION,
    live: () => counters.live,
    created: () => counters.created,
    gpu: () => {
      const info = ctx.renderer.info;
      return { geometries: info.memory.geometries, textures: info.memory.textures, programs: info.programs?.length ?? 0 };
    },
  };

  window.__viewer = hookViewer;
  window.__host = host;
  window.__build = build;
  window.__walkthrough = walkthrough;
  ctx.disposer.add(() => {
    const mine = window.__walkthrough === walkthrough;            // __build may be null: whose null it is, __walkthrough says
    if (window.__viewer === hookViewer) delete window.__viewer;
    if (window.__host === host) delete window.__host;
    if ((build !== null && window.__build === build) || (build === null && mine && window.__build === null)) delete window.__build;
    if (mine) delete window.__walkthrough;
  });
};

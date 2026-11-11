// The climbing tests' DOM kit (rooms step R4; not a test file; happy-dom): the real parseBuiltModel, resolvePresentation,
// buildScene, createVisibility, createHeights, createReadouts and installModes on a context without WebGL (the renderer
// is a stub, the furniture and the replay are not installed), as test/tools/record-walk-parity.ts mounts the old models.
import { PerspectiveCamera, Scene, Vector2, Vector3, type WebGLRenderer } from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type {
  BuiltModel, FloorRecord, InternalEvents, ModesApi, ModesState, PanelSlot, ViewerContext, ViewerEvents,
} from '../../../src/contracts';
import { buildScene } from '../../../src/core/build';
import { createDisposer } from '../../../src/core/disposer';
import { createEventBus } from '../../../src/core/events';
import { createHeights } from '../../../src/core/heights';
import { createReadouts } from '../../../src/core/readouts';
import { createVisibility } from '../../../src/core/visibility';
import { parsePresentation, resolvePresentation } from '../../../src/model/presentation';
import { installModes } from '../../../src/modes/index';
import { bridgeEvents } from '../../../src/viewer';
import { PLAIN } from './climb-kit';

export const SIZE = { width: 1400, height: 880 };

export interface ModesRig {
  ctx: ViewerContext; model: BuiltModel; modes: ModesApi; s: ModesState; canvas: HTMLCanvasElement; root: HTMLDivElement;
  floor(key: string): FloorRecord;
  /** World matrices as a rendered frame would leave them (after a Build settings change). */
  refresh(): void;
  /** Walk on `key` at the plan point (x, y), the foot on the floor's level, by writing the position as the e2e helpers do. */
  put(key: string, x: number, y: number): void;
  /** probe.walk toward a plan point; returns the horizontal distance made. */
  to(x: number, y: number): number;
  /** One frame with a made-up clock (ms). */
  frame(ms: number): void;
  dispose(): void;
}

export function modesRig(model: BuiltModel, presentationJson: unknown = PLAIN): ModesRig {
  const presentation = resolvePresentation(parsePresentation(presentationJson), model);
  const built = buildScene(model, presentation);
  const scene = new Scene();
  for (const f of built.floors) scene.add(f.group);
  const disposer = createDisposer();

  const container = document.createElement('div');
  document.body.append(container);
  const root = document.createElement('div');
  root.className = 'wtv';
  const div = (wt: string) => { const e = document.createElement('div'); e.setAttribute('data-wt', wt); return e; };
  const hint = div('hint'), errorBox = div('error'), panelEl = div('panel');
  const style = document.createElement('style');
  const canvas = document.createElement('canvas');
  canvas.getBoundingClientRect = () => ({ left: 0, top: 0, right: SIZE.width, bottom: SIZE.height, width: SIZE.width, height: SIZE.height, x: 0, y: 0, toJSON: () => ({}) });
  root.append(canvas, style, hint, errorBox, panelEl);
  container.append(root);
  const slots = new Map<PanelSlot, HTMLDivElement>();
  for (const slot of ['title', 'intro', 'floors', 'modes', 'shows', 'legend', 'build', 'furniture'] as PanelSlot[]) {
    const e = div(`slot-${slot}`);
    slots.set(slot, e);
    panelEl.append(e);
  }

  const camera = new PerspectiveCamera(40, SIZE.width / SIZE.height, 0.1, presentation.camera.far);
  const controls = new OrbitControls(camera, canvas);
  camera.position.set(24, 27, 29);
  controls.target.set(0, 2.5, 0);
  camera.lookAt(controls.target);
  controls.update();
  camera.updateMatrixWorld();

  const renderer = {
    domElement: canvas, getPixelRatio: () => 1, setPixelRatio: () => {}, setSize: () => {}, getSize: (t: Vector2) => t.set(SIZE.width, SIZE.height),
    getDrawingBufferSize: (t: Vector2) => t.set(SIZE.width, SIZE.height), render: () => {}, setRenderTarget: () => {}, getRenderTarget: () => null,
    capabilities: { getMaxAnisotropy: () => 1 }, dispose: () => {},
  } as unknown as WebGLRenderer;
  const ctx = {
    id: 'climb', container, renderer, canvas, scene, camera, controls, model, presentation, stages: null,
    project: { model, presentation, stages: null, pictures: {}, heights: null, stamp: 'climbclimb00' },
    options: {
      address: {}, build: 'skip', furnitureHeights: 'local', storageKey: 'climb', testHook: false, pixelRatioCap: 2,
      download: () => {}, noDownload: true, testFailAt: null,
    },
    floors: built.floors, floorByKey: new Map<string, FloorRecord>(built.floors.map(f => [f.key, f])), built,
    disposer, events: createEventBus<ViewerEvents>(), bus: createEventBus<InternalEvents>(),
    ui: {
      root, hint, errorBox,
      addStyle: (css: string) => { style.textContent += `\n${css}`; },
      setFlag: (flag: string, on: boolean) => { if (on) root.setAttribute(`data-${flag}`, ''); else root.removeAttribute(`data-${flag}`); },
    },
    size: () => ({ ...SIZE }),
    rectOf: (e: Element) => { const r = e.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height }; },
    reportError: (err: unknown) => { throw err; },
    panel: { el: panelEl, slot: (slot: PanelSlot) => slots.get(slot)!, markFloors: () => {} },
    pictures: null, furniture: null, replay: null, labels: { labels: [], place: () => {} }, loop: null,
  } as unknown as ViewerContext;
  const w = ctx as unknown as Record<string, unknown>;
  bridgeEvents(ctx.bus, ctx.events);
  w.visibility = createVisibility(ctx);
  w.heights = createHeights(ctx);
  w.readouts = createReadouts(ctx);
  ctx.visibility.applyFloor();
  ctx.visibility.applyToggles();
  const modes = installModes(ctx);
  w.modes = modes;
  const s = modes.state;
  const refresh = () => scene.updateMatrixWorld(true);
  refresh();
  const floor = (key: string) => ctx.floorByKey.get(key)!;
  const rig: ModesRig = {
    ctx, model, modes, s, canvas, root, floor, refresh,
    put(key, x, y) {
      if (s.mode !== 'walk') modes.setMode('walk', { floor: floor(key), point: { x, z: -y } });
      if (s.floor.key !== key) modes.goToFloor(key);
      s.pos.x = x; s.pos.z = -y;
    },
    to(x, y) {
      const dx = x - s.pos.x, dy = y + s.pos.z, len = Math.hypot(dx, dy);
      if (len < 1e-9) return 0;
      // probe.walk's heading: (-sin yaw, -cos yaw) in three.js (x, z); plan y = -z
      const deg = Math.atan2(-dx, dy) * 180 / Math.PI;
      return modes.probe.walk(deg, len - 1e-9);
    },
    frame(ms) { modes.tick(ms); },
    dispose() { disposer.dispose(); controls.dispose(); container.remove(); },
  };
  return rig;
}

/** Client coordinates of a world point as the camera sees it now. */
export function clientOf(ctx: ViewerContext, p: Vector3): { clientX: number; clientY: number } {
  ctx.camera.updateMatrixWorld();
  const v = p.clone().project(ctx.camera);
  return { clientX: (v.x + 1) / 2 * SIZE.width, clientY: (1 - v.y) / 2 * SIZE.height };
}

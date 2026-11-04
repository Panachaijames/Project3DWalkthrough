// Renderer, scene, lights, camera, controls, root, resize (DESIGN.md 11.4 step 2; the four pages' script tops). Owner: A.
//
// The context is made here and filled in by viewer.ts in the init order of 11.4 (floors, visibility, heights, readouts,
// panel, modes, furniture, replay, labels): those fields start as placeholders that throw when used too early.
//
// Two disposers. ctx.disposer is the modules' (every listener, timer, tracked object and undo step of B, C, D and A's own
// modules); `core` is this file's own (the root, the renderer, the controls, the resize watchers). teardown() runs, in the
// order of DESIGN.md 11.8: stop the loop, exit pointer lock, the resize watchers off, ctx.disposer (listeners and timers off,
// tracked geometry / materials / textures disposed, object URLs revoked, image loads aborted, window hooks removed), then
// the core: OrbitControls.dispose(), every geometry, material, texture and BVH of the scene graph, the self-check
// (renderer.info.memory geometries and textures 0, else console.warn('[viewer] dispose left ...')), renderer.dispose(),
// renderer.forceContextLoss(), and last the adopted stylesheet and the root (createRoot's own disposer step).
import {
  Box3, Color, DirectionalLight, HemisphereLight, PerspectiveCamera, Scene, Vector3, WebGLRenderer,
  type BufferGeometry, type Material, type Mesh, type Object3D, type Texture,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type {
  BuiltScene, CreateContext, Disposer, FloorRecord, HeightsApi, InternalEvents, LabelsApi, ModesApi, PanelApi, ReadoutsApi,
  ResolvedOptions, ViewerContext, ViewerEvents, ViewerOptions, ViewerProject, VisibilityApi,
} from '../contracts';
import { resolvePresentation } from '../model/presentation';
import { createRoot } from '../ui/root';
import { el } from '../ui/dom';
import { usePrototypeZoom } from './controls';
import { createDisposer } from './disposer';
import { createEventBus } from './events';
import { createLoop, type CoreLoop } from './loop';
import { usePrototypeTransparentSort } from './sort';

export const STORAGE_KEY_PREFIX = 'walkthrough-furniture-heights:';
export const BACKGROUND = 0xeef0f2;

/** ViewerContext with its fields writable (viewer.ts fills them in init order) and the core's own parts. */
export type CoreContext = { -readonly [K in keyof ViewerContext]: ViewerContext[K] } & {
  loop: CoreLoop;
  /** The core's own disposer (root, renderer, controls, resize); undone after ctx.disposer. */
  readonly core: Disposer;
  /** Everything undone, in the order of DESIGN.md 11.8. Idempotent. */
  teardown(): void;
};

let nextId = 1;

/** A stand-in for a field filled later in init order: any use before then is a clear error, not a silent undefined. */
function notYet<T extends object>(name: string): T {
  return new Proxy({} as T, {
    get(_, prop) {
      if (typeof prop === 'symbol' || prop === 'then' || prop === 'toJSON') return undefined;
      throw new Error(`[viewer] ctx.${name}.${String(prop)} used before ${name} was installed (DESIGN.md 11.4 init order)`);
    },
  });
}

/**
 * Textures the renderer gave the materials under `root` itself, not in the scene graph: three 0.186's DFG lookup table for
 * physically based materials (a module-wide DataTexture, `uniforms.dfgLUT`, uploaded once per renderer that draws a
 * MeshStandardMaterial). Disposing it frees it in every renderer that uploaded it; a renderer still drawing uploads it
 * again at its next frame. Without this the self-check would always find 1 texture left.
 */
export function rendererTextures(renderer: WebGLRenderer, root: Object3D): Set<Texture> {
  const out = new Set<Texture>();
  const props = (renderer as unknown as { properties?: { get(o: object): { uniforms?: Record<string, { value?: unknown } | undefined> } } }).properties;
  if (!props || typeof props.get !== 'function') return out;
  root.traverse(o => {
    const m = o as Mesh;
    const mats = m.material ? (Array.isArray(m.material) ? m.material : [m.material]) : [];
    for (const mat of mats) {
      let value: unknown;
      try { value = props.get(mat).uniforms?.dfgLUT?.value; } catch { value = undefined; }
      if (value && typeof value === 'object' && (value as Texture).isTexture) out.add(value as Texture);
    }
  });
  return out;
}

/** Disposes every geometry (and its BVH), material and material texture under `root`. */
export function disposeTree(root: Object3D): void {
  const geometries = new Set<BufferGeometry>(), materials = new Set<Material>(), textures = new Set<Texture>();
  root.traverse(o => {
    const m = o as Mesh;
    if (m.geometry) geometries.add(m.geometry);
    const mats = m.material ? (Array.isArray(m.material) ? m.material : [m.material]) : [];
    for (const mat of mats) {
      materials.add(mat);
      for (const v of Object.values(mat)) if (v && typeof v === 'object' && (v as Texture).isTexture) textures.add(v as Texture);
    }
  });
  for (const g of geometries) { g.boundsTree = undefined; g.dispose(); }
  for (const mat of materials) mat.dispose();
  for (const t of textures) t.dispose();
}

/**
 * 8 hex of the saved heights a project carries (FNV-1a over `kind=mm` in key order), '' when there are none. Part of the
 * offline file's storage key (fix step, review finding "adversarial" 5): heights typed into an earlier download of a
 * version were applied over the newer saved heights of every later download of it in the same browser.
 */
export function savedHeightsTag(heights: ViewerProject['heights']): string {
  const entries = Object.entries(heights ?? {}).filter(([, v]) => typeof v === 'number' && Number.isFinite(v)).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  if (!entries.length) return '';
  let h = 0x811c9dc5;
  for (const ch of entries.map(([k, v]) => `${k}=${v}`).join(',')) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, '0');
}

export function resolveOptions(project: ViewerProject, options: ViewerOptions | undefined,
  download: (blob: Blob, fileName: string) => void): ResolvedOptions {
  const address = options?.address ?? {};
  const testHook = options?.testHook === true;
  const furnitureHeights = options?.furnitureHeights === 'host' ? 'host' : 'local';
  // `<prefix><photoName>:<stamp>` (DESIGN.md 11.2, 18.31); in the offline file ('local') with saved heights in it, also
  // `:<savedHeightsTag>`: what was typed over one set of saved heights stays with that set, so a later download with other
  // saved heights opens with its own (a file without saved heights keeps the plain key, as before)
  const tag = furnitureHeights === 'local' ? savedHeightsTag(project.heights) : '';
  return {
    address,
    build: options?.build ?? address.build ?? (project.stages ? 'settings' : 'skip'),
    furnitureHeights,
    storageKey: `${options?.storageKeyPrefix ?? STORAGE_KEY_PREFIX}${project.model.photoName}:${project.stamp}${tag ? `:${tag}` : ''}`,
    testHook,
    pixelRatioCap: options?.pixelRatioCap ?? 2,
    download: options?.download ?? download,
    noDownload: address.nodownload === true,
    testFailAt: testHook ? options?.testFailAt ?? null : null,
  };
}

/**
 * The camera start of presentation.camera: 'fixed' (bank, suite, house) or 'fitSlabs' (the hotel page's: aimed at the
 * middle of the floor plates at targetY, from `away`, panned left by half of min(panel right, width / 2) in metres per
 * pixel at the target's distance). fitSlabs needs the panel (init step 4).
 */
export function applyCameraStart(ctx: ViewerContext): void {
  const cam = ctx.presentation.camera, camera = ctx.camera, controls = ctx.controls;
  if (cam.kind === 'fixed') {
    camera.position.set(cam.position[0], cam.position[1], cam.position[2]);
    controls.target.set(cam.target[0], cam.target[1], cam.target[2]);
  } else {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const p of ctx.model.parts) if (p.kind === 'slab') for (const [x, y] of p.o) {
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
    const mx = Number.isFinite(x0) ? (x0 + x1) / 2 : 0, my = Number.isFinite(y0) ? (y0 + y1) / 2 : 0;
    const away = new Vector3(cam.away[0], cam.away[1], cam.away[2]);
    const right = new Vector3(away.z, 0, -away.x).normalize();          // the screen's right, on the ground
    const { width, height } = ctx.size();
    const metresPerPx = 2 * away.length() * Math.tan(camera.fov * Math.PI / 360) / height;
    let panelRight = 0;
    if (cam.panForPanel) {
      let right0 = 0;
      try { right0 = ctx.rectOf(ctx.panel.el).right; } catch { right0 = 0; }
      panelRight = Math.min(right0, width / 2);
    }
    const target = new Vector3(mx, cam.targetY, -my).addScaledVector(right, -panelRight / 2 * metresPerPx);
    controls.target.copy(target);
    camera.position.copy(target).add(away);
  }
  controls.update();
}

export const createContext = ((container: HTMLElement, project: ViewerProject, options: ViewerOptions | undefined): CoreContext => {
  const core = createDisposer();
  const disposer = createDisposer();
  try {
    const model = project.model;
    const presentation = resolvePresentation(project.presentation, model);
    const events = createEventBus<ViewerEvents>();
    const bus = createEventBus<InternalEvents>();
    const id = `wtv-${nextId++}`;

    // the root (C), removed last; then the renderer (throws when WebGL cannot start: the root goes again)
    const ui = createRoot(container, presentation.accent, project.stamp, core);
    const renderer = new WebGLRenderer({ antialias: true });
    const canvas = renderer.domElement;
    const scene = new Scene();
    core.add(() => {                                      // the scene graph, the self-check, the renderer and its context
      const own = rendererTextures(renderer, scene);
      disposeTree(scene);
      for (const t of own) t.dispose();
      const mem = renderer.info.memory;
      if (mem.geometries !== 0 || mem.textures !== 0) {
        console.warn(`[viewer] dispose left ${mem.geometries} geometries and ${mem.textures} textures on the GPU`);
      }
      scene.clear();
      renderer.dispose();
      renderer.forceContextLoss();
    });
    ui.root.prepend(canvas);                              // in the document before OrbitControls (its keydown listener)

    let lastSize = { width: 300, height: 150 };
    const size = () => {
      const w = ui.root.clientWidth, h = ui.root.clientHeight;
      if (w > 0 && h > 0) lastSize = { width: w, height: h };
      return { ...lastSize };
    };
    // errors: the error box (C's) and the 'error' event, never page-wide listeners (18.14); each message logged once
    const reported = new Set<string>();
    const reportError = (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      try {
        ui.errorBox.textContent = `Viewer error: ${message}`;
        ui.errorBox.hidden = false;
        ui.errorBox.style.display = 'block';
      } catch { /* the root is gone */ }
      if (!reported.has(message)) { reported.add(message); console.error('[viewer]', err); }
      try { events.emit('error', { message }); } catch (e) { console.error('[viewer] error listener failed', e); }
    };
    const resolved = resolveOptions(project, options, (blob, fileName) => {
      const url = disposer.objectUrl(URL.createObjectURL(blob));
      const a = el('a', { attrs: { href: url, download: fileName } });
      a.style.display = 'none';
      ui.root.append(a);
      a.click();
      a.remove();
      disposer.timeout(() => URL.revokeObjectURL(url), 4000);
    });
    const cap = () => Math.min(typeof devicePixelRatio === 'number' && devicePixelRatio > 0 ? devicePixelRatio : 1, resolved.pixelRatioCap);
    const start = size();
    renderer.setPixelRatio(cap());
    renderer.setSize(start.width, start.height, false);

    scene.background = new Color(BACKGROUND);
    scene.add(new HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
    const sun = new DirectionalLight(0xffffff, 1.6);
    sun.position.set(-20, 40, 15);
    scene.add(sun);
    const camera = new PerspectiveCamera(40, start.width / start.height, 0.1, presentation.camera.far);
    if (presentation.camera.kind === 'fixed') camera.position.set(...presentation.camera.position);
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    // the prototypes' (three 0.160) wheel / pinch zoom and transparent draw order (fix step: core/controls.ts, sort.ts)
    if (!usePrototypeZoom(controls)) console.warn('[viewer] OrbitControls changed: the zoom is three\'s own, not the prototypes\'');
    usePrototypeTransparentSort(renderer, scene);
    // OrbitControls puts its capturing key listeners on canvas.getRootNode() (the document) and, on dispose, asks the
    // canvas for its root node again. A host may detach the container before dispose (React removes a page's DOM before
    // its effect cleanups run): the canvas's root node is then the detached subtree and the document would keep the
    // listener, holding the controls and the camera (integration, F-5). So dispose answers with the root node of connect
    // time when the canvas is no longer in the document.
    const keyRoot = canvas.getRootNode();
    core.add(() => {
      if (canvas.isConnected) { controls.dispose(); return; }
      const shadowed = Object.prototype.hasOwnProperty.call(canvas, 'getRootNode');
      canvas.getRootNode = () => keyRoot;
      try { controls.dispose(); } finally { if (!shadowed) delete (canvas as { getRootNode?: unknown }).getRootNode; }
    });

    // resizes: the root (a ResizeObserver: the staff app's layout, the window) and the pixel ratio (zoom, another screen)
    let watching = true, ratio = cap(), shown = start;
    const onResize = () => {
      if (!watching) return;
      const s = size(), r = cap();
      const changed = s.width !== shown.width || s.height !== shown.height || r !== ratio;
      if (!changed) return;
      shown = s; ratio = r;
      renderer.setPixelRatio(r);
      renderer.setSize(s.width, s.height, false);
      camera.aspect = s.width / s.height;
      camera.updateProjectionMatrix();
      try { bus.emit('resize', { width: s.width, height: s.height }); } catch (err) { reportError(err); }
    };
    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver === 'function') {
      observer = new ResizeObserver(() => onResize());
      observer.observe(ui.root);
    }
    const watchRatio = () => {
      if (!watching || typeof matchMedia !== 'function' || typeof devicePixelRatio !== 'number') return;
      const mq = matchMedia(`(resolution: ${devicePixelRatio}dppx)`);
      core.listen(mq, 'change', () => { onResize(); watchRatio(); }, { once: true });
    };
    watchRatio();
    const stopResize = () => { watching = false; observer?.disconnect(); observer = null; };
    core.add(stopResize);

    const loop = createLoop({ renderer, scene, camera, disposer: core, reportError });
    const emptyBuilt: BuiltScene = { floors: [], toggleObjects: { plates: [], glass: [], single: [] }, plinths: [], groundPlane: null, fitted: {} };
    let tornDown = false;
    const ctx: CoreContext = {
      id, container, ui, renderer, canvas, scene, camera, controls, model, presentation,
      stages: project.stages ?? null, project, options: resolved,
      floors: [] as FloorRecord[], floorByKey: new Map<string, FloorRecord>(), built: emptyBuilt,
      disposer, events, bus, loop,
      visibility: notYet<VisibilityApi>('visibility'), heights: notYet<HeightsApi>('heights'), readouts: notYet<ReadoutsApi>('readouts'),
      size,
      rectOf(elem) {
        const r = elem.getBoundingClientRect(), b = ui.root.getBoundingClientRect();
        return { left: r.left - b.left, top: r.top - b.top, right: r.right - b.left, bottom: r.bottom - b.top, width: r.width, height: r.height };
      },
      reportError,
      panel: notYet<PanelApi>('panel'), pictures: null, modes: notYet<ModesApi>('modes'), furniture: null, replay: null,
      labels: notYet<LabelsApi>('labels'),
      core,
      teardown() {
        if (tornDown) return;
        tornDown = true;
        loop.stop();
        try { if (typeof document !== 'undefined' && document.pointerLockElement === canvas) document.exitPointerLock(); } catch { /* fine */ }
        stopResize();
        disposer.dispose();
        core.dispose();
        events.clear();
        bus.clear();
      },
    };
    if (presentation.camera.kind === 'fixed') applyCameraStart(ctx);
    return ctx;
  } catch (err) {
    disposer.dispose();
    core.dispose();
    throw err;
  }
}) satisfies CreateContext;

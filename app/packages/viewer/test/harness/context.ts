// The shared test context (WORK_BREAKDOWN S.9): makeTestContext({ model, presentation?, stages?, renderer?, container? })
// returns a WORKING ViewerContext built naively, so builders B, C and D test their modules before builder A's real core
// lands; it stays a test kit afterwards (it is replaced by nothing). Scaffold; read-only for builders.
//
// What it builds (DESIGN.md 5.4, naively): ONE mesh per part with the 5.4 extrude rule (Shape(o) with holes h,
// ExtrudeGeometry depth z1 - z0, rotateX(-PI/2), translate to the model level + z0) and an `aDelay` attribute (the sweep),
// coloured by the kind's style (DEFAULT_PART_STYLES + presentation.partStyles), edges per part; the mesh name is the v1
// group name `<floor> <mesh>:<fit>` (several meshes share it here). Colliders: every non-slab part whose style is a
// collider, plus the collider skins (one invisible mesh per floor and glass flag); walkables: one mesh per slab
// (`<floor> floor plate`, also late, the plates tick, `plinths`); rise: every non-slab part ({ mesh, edges, scales, fit });
// `fitted`: the meshes with fit top / clip; stairs (late): tread strips, faint lines above, panels; the ground plane.
// A three-mesh-bvh BVH on every collider and walkable. Floor groups at y = 0 (geometry at the model level).
// Also: a minimal root (hint, error box, a <style> for addStyle, flags) and a slot panel; simple working visibility
// (floor mode, ticks), heights.apply (group position, `scale` items, Walk level; no top / clip refit, no plinth),
// readouts (upHit, downHit, rayHit, cast), a loop with a manual frame(), the disposer and both buses; modes is an
// Orbit-only stub, labels empty, pictures / furniture / replay null (a module under test installs itself into ctx).
//
// renderer: 'fake' (default; Node or happy-dom): a stub with the methods modes and the replay call; 'webgl' (a browser
// harness page): a real WebGLRenderer. In plain Node (no `document`) the root, panel, canvas and container are inert
// stand-ins: use `// @vitest-environment happy-dom` for anything that touches the DOM.
// Clean up with ctx.disposer.dispose().
import {
  BufferAttribute, BufferGeometry, Color, DirectionalLight, DoubleSide, EdgesGeometry, ExtrudeGeometry, Float32BufferAttribute,
  FrontSide, Group, HemisphereLight, LineBasicMaterial, LineSegments, Mesh, MeshBasicMaterial, MeshStandardMaterial, Path,
  PerspectiveCamera, PlaneGeometry, Raycaster, Scene, Shape, Vector2, Vector3, WebGLRenderer, Box3, type Material, type Object3D,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { MeshBVH, acceleratedRaycast } from 'three-mesh-bvh';
import type {
  BuiltModel, BuiltScene, FitMode, FloorKey, FloorRecord, FloorSettings, HeightsApi, InternalEvents, LabelsApi, LoopApi, ModesApi,
  ModesState, PanelApi, PanelSlot, Part, PartKind, PartStyle, Presentation, ReadoutsApi, ReplayData, ResolvedOptions,
  ResolvedPresentation, RootApi, SettingsMap, TickPhase, ToggleName, Vec3, ViewerContext, ViewerEvents, ViewerProject, VisibilityApi,
} from '../../src/contracts';
import { createDisposer } from '../../src/core/disposer';
import { createEventBus } from '../../src/core/events';
import { DEFAULT_PART_STYLES } from '../../src/model/styles';
import { el } from '../../src/ui/dom';

export interface TestContextOptions {
  model: BuiltModel;
  /** Raw Presentation v1 (e.g. fixtures/presentation/*.json); naive defaults of DESIGN.md 8 fill the rest. */
  presentation?: Presentation;
  stages?: ReplayData | null;
  renderer?: 'webgl' | 'fake';
  /** Must be connected. Default (with a DOM): a 1400 x 880 div added to document.body. */
  container?: HTMLElement;
  /** Overrides of the resolved options (storage key, download, noDownload ...). */
  options?: Partial<ResolvedOptions>;
  /** Default 'testcontext0'. */
  stamp?: string;
  /** The root size when the DOM cannot measure it (Node, happy-dom). Default 1400 x 880. */
  size?: { width: number; height: number };
}

export interface TestContext extends ViewerContext {
  kit: {
    /** Files the viewer asked to download (options.download). */
    downloads: { blob: Blob; fileName: string }[];
    fake: boolean;
    /** A real DOM (browser or happy-dom) is in use. */
    dom: boolean;
  };
}

const DEFAULT_LABELS = {
  plates: 'Floor plates', glass: 'Glass', rooms: 'Room names', single: 'Single-line items', picture: 'Plan picture', ceilings: 'Ceilings',
  pictureTitle: "Each floor's source picture, laid on its floor plate at the model's scale and position",
};

/** Naive defaults of DESIGN.md 8 (builder A's resolvePresentation is the real one). */
export function naivePresentation(p: Presentation | undefined, model: BuiltModel): ResolvedPresentation {
  const styles = {} as Record<PartKind, PartStyle>;
  for (const [k, s] of Object.entries(DEFAULT_PART_STYLES) as [PartKind, PartStyle][]) styles[k] = { ...s, ...(p?.partStyles?.[k] ?? {}) };
  const camera = p?.camera ?? { kind: 'fixed' as const, position: [24, 27, 29] as Vec3, target: [0, 2.5, 0] as Vec3 };
  return {
    documentTitle: p?.documentTitle ?? model.shortName,
    heading: p?.heading ?? model.project,
    intro: p?.intro ?? [],
    accent: p?.accent ?? '#2f6f8f',
    legend: p?.legend ?? { layout: 'inline', items: [] },
    floorButtons: { all: p?.floorButtons?.all ?? 'Both floors', labels: p?.floorButtons?.labels ?? {} },
    labels: { ...DEFAULT_LABELS, ...(p?.labels ?? {}) },
    camera: { ...camera, far: camera.far ?? 600 },
    partStyles: styles,
    creaseAngle: p?.creaseAngle ?? 25,
    groundPlane: p?.groundPlane ?? null,
    toggles: { plates: true, glass: true, rooms: true, single: true, picture: false, ceilings: true, ...(p?.toggles ?? {}) },
  };
}

// ------------------------------------------------------------------------------------------- Node stand-ins (no DOM)
function inertElement(tag: string, size: { width: number; height: number }): HTMLElement {
  const root = new EventTarget();
  const doc = new EventTarget();
  const node = new EventTarget() as EventTarget & Record<string, unknown>;
  const attrs: Record<string, string> = {};
  const kids: unknown[] = [];
  Object.assign(node, {
    tagName: tag.toUpperCase(), style: {}, dataset: {}, hidden: false, textContent: '', className: '', title: '', isConnected: true,
    children: kids, childNodes: kids, clientWidth: size.width, clientHeight: size.height, width: size.width, height: size.height,
    ownerDocument: doc, getRootNode: () => root,
    append: (...n: unknown[]) => { kids.push(...n); }, appendChild: (n: unknown) => { kids.push(n); return n; },
    prepend: (...n: unknown[]) => { kids.unshift(...n); }, remove: () => {}, contains: () => false,
    setAttribute: (k: string, v: string) => { attrs[k] = String(v); }, getAttribute: (k: string) => attrs[k] ?? null,
    removeAttribute: (k: string) => { delete attrs[k]; }, hasAttribute: (k: string) => k in attrs,
    querySelector: () => null, querySelectorAll: () => [],
    getBoundingClientRect: () => ({ left: 0, top: 0, right: size.width, bottom: size.height, width: size.width, height: size.height, x: 0, y: 0 }),
    setPointerCapture: () => {}, releasePointerCapture: () => {}, hasPointerCapture: () => false, focus: () => {}, blur: () => {},
  });
  return node as unknown as HTMLElement;
}

function fakeRenderer(canvas: HTMLElement, size: { width: number; height: number }): WebGLRenderer {
  let pixelRatio = 1;
  const s = { w: size.width, h: size.height };
  const r = {
    isFake: true,
    domElement: canvas,
    info: { memory: { geometries: 0, textures: 0 }, render: { calls: 0, triangles: 0, points: 0, lines: 0, frame: 0 }, programs: [] as unknown[] },
    capabilities: { getMaxAnisotropy: () => 1, isWebGL2: true },
    outputColorSpace: 'srgb',
    setPixelRatio: (v: number) => { pixelRatio = v; },
    getPixelRatio: () => pixelRatio,
    setSize: (w: number, h: number) => { s.w = w; s.h = h; },
    getSize: (t: Vector2) => t.set(s.w, s.h),
    getDrawingBufferSize: (t: Vector2) => t.set(s.w * pixelRatio, s.h * pixelRatio),
    setAnimationLoop: () => {},
    render: () => { r.info.render.frame++; },
    setRenderTarget: () => {}, getRenderTarget: () => null, readRenderTargetPixels: () => {},
    setClearColor: () => {}, getClearColor: (c: Color) => c, setViewport: () => {}, setScissor: () => {}, setScissorTest: () => {},
    clear: () => {}, compile: () => {}, dispose: () => {}, forceContextLoss: () => {},
  };
  return r as unknown as WebGLRenderer;
}

// --------------------------------------------------------------------------------------------------------- geometry
const fitOf = (p: Part): FitMode => p.fit ?? (p.follow ? 'scale' : 'fixed');
const fitName = (fit: FitMode) => (fit === 'scale' ? 'follow' : 'own');

function extrude(o: [number, number][], h: [number, number][][], z0: number, z1: number, level: number): BufferGeometry {
  const shape = new Shape(o.map(([x, y]) => new Vector2(x, y)));
  for (const hole of h) shape.holes.push(new Path(hole.map(([x, y]) => new Vector2(x, y))));
  const g = new ExtrudeGeometry(shape, { depth: z1 - z0, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, level + z0, 0);
  return g;
}

function bvh(mesh: Mesh): Mesh {
  mesh.geometry.boundsTree = new MeshBVH(mesh.geometry);
  mesh.raycast = acceleratedRaycast;
  return mesh;
}

/** Flat x1, y1, x2, y2 segments -> quads (a strip `width` wide lying at y, or an upright panel `height` tall from y). */
function segmentQuads(flat: number[], y: number, opts: { width?: number; height?: number }): BufferGeometry {
  const pos: number[] = [];
  for (let i = 0; i + 3 < flat.length; i += 4) {
    const x1 = flat[i]!, y1 = flat[i + 1]!, x2 = flat[i + 2]!, y2 = flat[i + 3]!;
    const len = Math.hypot(x2 - x1, y2 - y1) || 1;
    if (opts.height !== undefined) {
      const a = [x1, y, -y1], b = [x2, y, -y2], c = [x2, y + opts.height, -y2], d = [x1, y + opts.height, -y1];
      pos.push(...a, ...b, ...c, ...a, ...c, ...d);
    } else {
      const w = (opts.width ?? 0.03) / 2, nx = (-(y2 - y1) / len) * w, ny = ((x2 - x1) / len) * w;
      const a = [x1 + nx, y, -(y1 + ny)], b = [x2 + nx, y, -(y2 + ny)], c = [x2 - nx, y, -(y2 - ny)], d = [x1 - nx, y, -(y1 - ny)];
      pos.push(...a, ...b, ...c, ...a, ...c, ...d);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.computeVertexNormals();
  return g;
}

function buildNaively(model: BuiltModel, pres: ResolvedPresentation, scene: Scene): BuiltScene {
  const nonSlab = model.parts.filter(p => p.kind !== 'slab');
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of nonSlab) for (const [x, y] of p.o) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const sweep = (cx: number, cy: number) => Math.min(1, Math.max(0, 0.8 * (cx - x0) / ((x1 - x0) || 1) + 0.2 * (y1 - cy) / ((y1 - y0) || 1)));
  const materials = new Map<string, Material>();
  const material = (key: string, make: () => Material) => { let m = materials.get(key); if (!m) materials.set(key, (m = make())); return m; };

  const built: BuiltScene = { floors: [], toggleObjects: { plates: [], glass: [], single: [] }, plinths: [], groundPlane: null, fitted: {} };
  for (const f of model.floors) {
    const group = new Group();
    group.name = f.key;
    scene.add(group);
    const rec: FloorRecord = {
      key: f.key, name: f.name, level: f.level, modelLevel: f.level, wallHeight: f.wallHeight, stack: f.stack ?? 'main',
      group, colliders: [], walkables: [], surfaces: [], late: [], rise: [],          // surfaces: the rooms scaffold's placeholder (R4 fills it)
    };
    built.floors.push(rec);
    built.fitted[f.key] = [];

    for (const p of model.parts.filter(q => q.floor === f.key)) {
      const style = pres.partStyles[p.kind];
      if (p.kind === 'slab') {
        const g = extrude(p.o, p.h, p.z0, p.z1, f.level);
        g.computeVertexNormals();
        const mat = material('slab', () => new MeshStandardMaterial({ color: new Color(style.color), roughness: 0.95, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1, side: FrontSide }));
        const mesh = bvh(new Mesh(g, mat));
        mesh.name = `${f.key} floor plate`;
        group.add(mesh);
        rec.walkables.push(mesh);
        rec.late.push(mesh);
        built.toggleObjects.plates.push(mesh);
        if (p.plinth) built.plinths.push(mesh);
        continue;
      }
      const fit = fitOf(p);
      const g = extrude(p.o, p.h, p.z0, p.z1, f.level);
      let cx = 0, cy = 0;
      for (const [x, y] of p.o) { cx += x; cy += y; }
      cx /= p.o.length; cy /= p.o.length;
      g.setAttribute('aDelay', new BufferAttribute(new Float32Array(g.attributes.position!.count).fill(sweep(cx, cy)), 1));
      const opacity = style.see ?? style.opacity ?? (style.glass ? 0.3 : 1);
      const mat = material(`${p.kind}`, () => new MeshStandardMaterial({
        color: new Color(style.color), roughness: style.roughness ?? 0.85, metalness: style.metalness ?? 0, side: DoubleSide,
        transparent: opacity < 1, opacity, depthWrite: opacity >= 1,
      }));
      const mesh = bvh(new Mesh(g, mat));
      mesh.name = `${f.key} ${style.mesh}:${fitName(fit)}`;
      mesh.renderOrder = style.renderOrder ?? (style.glass ? 3 : p.kind === 'railing' ? 2 : 0);
      const edgeMat = material(`${p.kind} edges`, () => new LineBasicMaterial({ color: new Color(style.edge), transparent: true, opacity: style.edgeOpacity ?? (style.glass ? 0.45 : 0.6) }));
      const edges = new LineSegments(new EdgesGeometry(g, pres.creaseAngle), edgeMat);
      edges.name = `${mesh.name} edges`;
      group.add(mesh, edges);
      if (style.collider !== false) rec.colliders.push(mesh);
      if (style.glass) built.toggleObjects.glass.push(mesh, edges);
      if (style.single) built.toggleObjects.single.push(mesh, edges);
      rec.rise.push({ mesh, edges, scales: fit === 'scale', fit });
      if (fit === 'top' || fit === 'clip') built.fitted[f.key]!.push(mesh);
    }

    for (const glass of [false, true]) {
      const skins = (model.colliderSkins[f.key] ?? []).filter(s => !!s.glass === glass);
      if (!skins.length) continue;
      const merged = mergeGeometries(skins.map(s => extrude(s.o, s.h, s.z0, s.z1, f.level)));
      const mesh = bvh(new Mesh(merged, material('skin', () => new MeshBasicMaterial({ visible: false }))));
      mesh.name = glass ? `${f.key} walk skins (glass)` : `${f.key} walk skins`;
      group.add(mesh);
      rec.colliders.push(mesh);
      if (glass) built.toggleObjects.glass.push(mesh);
    }

    const stairs = model.stairs[f.key];
    if (stairs?.below.length) {
      const mesh = new Mesh(segmentQuads(stairs.below, f.level + 0.012, { width: 0.03 }), material('treads', () => new MeshBasicMaterial({ color: 0x3f8f4f, side: DoubleSide })));
      mesh.name = `${f.key} tread lines`;
      group.add(mesh); rec.late.push(mesh);
    }
    if (stairs?.above.length) {
      const g = new BufferGeometry();
      const pos: number[] = [];
      for (let i = 0; i + 3 < stairs.above.length; i += 4) pos.push(stairs.above[i]!, f.level + 0.02, -stairs.above[i + 1]!, stairs.above[i + 2]!, f.level + 0.02, -stairs.above[i + 3]!);
      g.setAttribute('position', new Float32BufferAttribute(pos, 3));
      const lines = new LineSegments(g, material('above', () => new LineBasicMaterial({ color: 0x5aa65a, transparent: true, opacity: 0.35 })));
      lines.name = `${f.key} stair lines above`;
      group.add(lines); rec.late.push(lines);
    }
    if (stairs?.panels?.length) {
      const mesh = new Mesh(segmentQuads(stairs.panels, f.level, { height: 0.15 }), material('panels', () => new MeshBasicMaterial({ color: 0x5aa65a, side: DoubleSide })));
      mesh.name = `${f.key} stair panels`;
      group.add(mesh); rec.late.push(mesh);
    }
  }
  if (pres.groundPlane) {
    const [w, d] = pres.groundPlane.size;
    const plane = new Mesh(new PlaneGeometry(w, d).rotateX(-Math.PI / 2), new MeshStandardMaterial({ color: new Color(pres.groundPlane.colour) }));
    plane.name = 'ground plane';
    scene.add(plane);
    built.groundPlane = plane;
  }
  return built;
}

// ------------------------------------------------------------------------------------------------------ the context
export function makeTestContext(o: TestContextOptions): TestContext {
  const model = o.model;
  const presentation = naivePresentation(o.presentation, model);
  const stamp = o.stamp ?? 'testcontext0';
  const dom = typeof document !== 'undefined';
  const fake = (o.renderer ?? 'fake') === 'fake';
  const sizeDefault = o.size ?? { width: 1400, height: 880 };
  const disposer = createDisposer();
  const events = createEventBus<ViewerEvents>();
  const bus = createEventBus<InternalEvents>();
  const downloads: { blob: Blob; fileName: string }[] = [];

  // root, panel, canvas
  let container: HTMLElement;
  if (o.container) container = o.container;
  else if (dom) {
    container = document.createElement('div');
    Object.assign(container.style, { position: 'fixed', left: '0', top: '0', width: `${sizeDefault.width}px`, height: `${sizeDefault.height}px` });
    document.body.append(container);
    disposer.add(() => container.remove());
  } else container = inertElement('div', sizeDefault);
  const mk = (tag: 'div', wt: string): HTMLDivElement => (dom ? el(tag, { wt }) : (inertElement(tag, sizeDefault) as HTMLDivElement));
  const root = mk('div', 'root');
  root.setAttribute('data-model-stamp', stamp);
  if (dom) { root.className = 'wtv'; Object.assign(root.style, { position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }); }
  const hint = mk('div', 'hint');
  const errorBox = mk('div', 'error');
  errorBox.hidden = true;
  const styleEl = dom ? document.createElement('style') : null;
  if (styleEl) root.append(styleEl);
  root.append(hint, errorBox);
  container.append(root);
  disposer.add(() => root.remove());
  const ui: RootApi = {
    root, hint, errorBox,
    addStyle: css => { if (styleEl) styleEl.textContent += `\n${css}`; },
    setFlag: (flag, on) => { if (on) root.setAttribute(`data-${flag}`, ''); else root.removeAttribute(`data-${flag}`); },
  };

  const canvas: HTMLCanvasElement = fake ? (dom ? document.createElement('canvas') : (inertElement('canvas', sizeDefault) as HTMLCanvasElement)) : (null as unknown as HTMLCanvasElement);
  const renderer = fake ? fakeRenderer(canvas, sizeDefault) : new WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  const theCanvas = (fake ? canvas : renderer.domElement) as HTMLCanvasElement;
  if (dom) Object.assign(theCanvas.style, { display: 'block', width: '100%', height: '100%' });
  root.prepend(theCanvas);
  const size = () => {
    const w = dom ? root.clientWidth : 0, h = dom ? root.clientHeight : 0;
    return w > 0 && h > 0 ? { width: w, height: h } : { ...sizeDefault };
  };
  renderer.setPixelRatio(Math.min(typeof devicePixelRatio === 'number' ? devicePixelRatio : 1, o.options?.pixelRatioCap ?? 2));
  renderer.setSize(size().width, size().height, false);

  // scene, camera, controls
  const scene = new Scene();
  scene.background = new Color(0xeef0f2);
  scene.add(new HemisphereLight(0xffffff, 0xe4dfd6, 1.6));
  const sun = new DirectionalLight(0xffffff, 1.6);
  sun.position.set(-20, 40, 15);
  scene.add(sun);
  const built = buildNaively(model, presentation, scene);
  const cam = presentation.camera;
  const camera = new PerspectiveCamera(40, size().width / size().height, 0.1, cam.far);
  const controls = new OrbitControls(camera, theCanvas);
  controls.enableDamping = true;
  if (cam.kind === 'fixed') {
    camera.position.set(...cam.position);
    controls.target.set(...cam.target);
  } else {
    const box = new Box3();
    for (const f of built.floors) for (const m of f.walkables) box.expandByObject(m);
    const c = box.isEmpty() ? new Vector3() : box.getCenter(new Vector3());
    controls.target.set(c.x, cam.targetY, c.z);
    camera.position.set(c.x + cam.away[0], cam.targetY + cam.away[1], c.z + cam.away[2]);
  }
  camera.lookAt(controls.target);
  controls.update();

  // floors, visibility, heights, readouts
  const floorByKey = new Map<FloorKey, FloorRecord>(built.floors.map(f => [f.key, f]));
  let floorMode: 'all' | FloorKey = 'all';
  const toggles: Record<ToggleName, boolean> = { ...presentation.toggles };
  const visibility: VisibilityApi = {
    get floorMode() { return floorMode; },
    setFloorMode: m => { floorMode = m; visibility.applyFloor(); bus.emit('floorMode', { floorMode }); },
    applyFloor: () => { for (const f of built.floors) f.group.visible = floorMode === 'all' || floorMode === f.key; },
    get toggles() { return toggles; },
    setToggle: (name, on) => { toggles[name] = on; visibility.applyToggles(); bus.emit('toggles', { toggles: { ...toggles } }); },
    applyToggles: () => {
      for (const name of ['plates', 'glass', 'single'] as const) for (const obj of built.toggleObjects[name]) obj.visible = toggles[name];
    },
    has: name => name === 'rooms' ? model.rooms.length > 0
      : name === 'picture' ? Object.keys(model.pictureFrame ?? {}).length > 0
      : name === 'ceilings' ? false                      // no ceiling meshes in the naive scene (the rooms scaffold's placeholder)
      : built.toggleObjects[name].length > 0,
  };
  const settings: SettingsMap = Object.fromEntries(model.floors.map(f => [f.key, { level: f.level, height: f.wallHeight } satisfies FloorSettings]));
  const heights: HeightsApi = {
    get settings() { return settings; },
    apply: next => {
      for (const [key, s] of Object.entries(next)) {
        const f = floorByKey.get(key);
        if (!f) continue;
        settings[key] = { ...s };
        f.level = s.level;
        f.group.position.y = s.level - f.modelLevel;
        const k = s.height / f.wallHeight;
        for (const item of f.rise) {
          if (!item.scales) continue;
          for (const obj of [item.mesh, item.edges]) if (obj) { obj.scale.y = k; obj.position.y = f.modelLevel * (1 - k); }
        }
      }
      bus.emit('settings', { settings: { ...settings } });
    },
  };
  const ray = new Raycaster();
  const visibleColliders = (key: FloorKey) => (floorByKey.get(key)?.colliders ?? []).filter(m => m.visible);
  const first = (key: FloorKey, origin: Vector3, dir: Vector3, far: number) => {
    ray.set(origin, dir); ray.far = far;
    return ray.intersectObjects(visibleColliders(key), false)[0] ?? null;
  };
  const levelOf = (key: FloorKey) => floorByKey.get(key)?.level ?? 0;
  const readouts: ReadoutsApi = {
    upHit: (key, x, y, h0 = 1.0) => { const hit = first(key, new Vector3(x, levelOf(key) + h0, -y), new Vector3(0, 1, 0), 20); return hit ? hit.distance + h0 : null; },
    downHit: (key, x, y, h0 = 3.0) => { const hit = first(key, new Vector3(x, levelOf(key) + h0, -y), new Vector3(0, -1, 0), 8); return hit ? h0 - hit.distance : null; },
    rayHit: (key, x, y, h, dx, dy, far = 3) => {
      const n = Math.hypot(dx, dy) || 1;
      const hit = first(key, new Vector3(x, levelOf(key) + h, -y), new Vector3(dx / n, 0, -dy / n), far);
      return hit ? { d: hit.distance, name: hit.object.name } : null;
    },
    cast: (key, p, d, far) => { const hit = first(key, new Vector3(...p), new Vector3(...d).normalize(), far); return hit ? { d: hit.distance, name: hit.object.name } : null; },
    // the rooms scaffold's placeholder (rooms/DESIGN.md R-9.8): the floor plate under (x, y), from h0 above the level
    groundAt: (key, x, y, h0 = 3.0) => {
      const f = floorByKey.get(key);
      if (!f) return null;
      ray.set(new Vector3(x, f.level + h0, -y), new Vector3(0, -1, 0)); ray.far = h0 + 8;
      const hit = ray.intersectObjects([...f.surfaces, ...f.walkables].filter(m => m.visible), false)[0];
      return hit ? h0 - hit.distance : null;
    },
  };

  // loop
  const hooks: Record<TickPhase, Set<(now: number) => void>> = { replay: new Set(), modes: new Set(), sync: new Set(), overlay: new Set() };
  let running = false;
  const reportError = (err: unknown) => {
    const message = err instanceof Error ? err.message : String(err);
    errorBox.textContent = message;
    errorBox.hidden = false;
    events.emit('error', { message });
  };
  const runPhase = (phase: TickPhase, now: number) => { for (const fn of hooks[phase]) { try { fn(now); } catch (err) { reportError(err); } } };
  const loop: LoopApi = {
    add: (phase, fn) => { hooks[phase].add(fn); return () => { hooks[phase].delete(fn); }; },
    start: () => { running = true; if (!fake) renderer.setAnimationLoop(t => loop.frame(t)); },
    stop: () => { running = false; renderer.setAnimationLoop(null); },
    frame: (now = typeof performance !== 'undefined' ? performance.now() : Date.now()) => {
      runPhase('replay', now); runPhase('modes', now); runPhase('sync', now);
      renderer.render(scene, camera);
      runPhase('overlay', now);
    },
    get running() { return running; },
  };

  // panel (slots in order), modes (Orbit only), labels (none)
  const panelEl = mk('div', 'panel');
  if (dom) panelEl.className = 'wtv-panel';
  const many = model.floors.length > 1;
  const order: PanelSlot[] = many ? ['title', 'intro', 'floors', 'modes', 'shows', 'legend', 'build', 'furniture'] : ['title', 'intro', 'shows', 'modes', 'legend', 'build', 'furniture'];
  const slots = new Map<PanelSlot, HTMLDivElement>();
  for (const name of [...order, ...(many ? [] : (['floors'] as PanelSlot[]))]) {
    const s = mk('div', `slot-${name}`);
    s.setAttribute('data-slot', name);
    slots.set(name, s);
    if (order.includes(name)) panelEl.append(s);
  }
  root.append(panelEl);
  const panel: PanelApi = { el: panelEl, slot: name => slots.get(name)!, markFloors: () => {} };
  const modesState: ModesState = {
    mode: 'orbit', floor: built.floors[0]!, pos: new Vector3(), foot: built.floors[0]!.level, yaw: 0, pitch: 0, eye: 1.6, lens: 24, orbitLens: 33, straight: false,
    ghostSpeed: 6, keys: new Set(), saved: null, drag: null, dragMoved: false, frame: '3:2', size: 1920, grid: false, camOpen: false,
    last: 0, touch: false, stick: { id: null, x: 0, y: 0 }, vert: 0, locked: false,
  };
  const modes: ModesApi = {
    get mode() { return modesState.mode; },
    state: modesState,
    probe: {
      open: () => 0, clearance: () => 0, onFloor: () => false, crosses: () => false, walk: () => 0,
      foot: () => modesState.foot, ground: () => null,
      visible: () => built.floors.filter(f => f.group.visible).map(f => f.key),
      camera: () => { const d = camera.getWorldDirection(new Vector3()); return { x: camera.position.x, y: camera.position.y, z: camera.position.z, fov: camera.fov, rx: camera.rotation.x, offsetY: camera.view?.offsetY ?? null, dir: [d.x, d.y, d.z] }; },
    },
    setMode: () => {}, goToFloor: () => {}, changeFloor: () => {}, takePhoto: () => Promise.resolve(null), openCam: () => {},
    lock: on => { modesState.locked = on; }, applyAddress: () => {}, tick: () => { controls.update(); },
  };
  const labels: LabelsApi = { labels: [], place: () => {} };

  const resolved: ResolvedOptions = {
    address: {}, build: o.stages ? 'settings' : 'skip', furnitureHeights: 'local',
    storageKey: `walkthrough-furniture-heights:${model.photoName}:${stamp}`, testHook: false, pixelRatioCap: 2,
    download: (blob, fileName) => { downloads.push({ blob, fileName }); }, noDownload: false, testFailAt: null,
    ...o.options,
  };
  const project: ViewerProject = { model, presentation: o.presentation ?? (presentation as unknown as Presentation), stages: o.stages ?? null, pictures: {}, heights: null, stamp };

  disposer.add(() => {
    loop.stop();
    controls.dispose();
    const seen = new Set<{ dispose(): void }>();
    scene.traverse((obj: Object3D) => {
      const m = obj as Mesh;
      if (m.geometry) { m.geometry.boundsTree = undefined; seen.add(m.geometry); }
      const mats = m.material ? (Array.isArray(m.material) ? m.material : [m.material]) : [];
      for (const mat of mats) seen.add(mat);
    });
    for (const thing of seen) thing.dispose();
    renderer.dispose();
    if (!fake) renderer.forceContextLoss();
    events.clear();
    bus.clear();
  });

  const ctx: TestContext = {
    id: `test-${Math.random().toString(36).slice(2, 8)}`,
    container, ui, renderer, canvas: theCanvas, scene, camera, controls, model, presentation, stages: o.stages ?? null, project,
    options: resolved, floors: built.floors, floorByKey, built, disposer, events, bus, loop, visibility, heights, readouts,
    size,
    rectOf: elem => {
      const r = elem.getBoundingClientRect(), base = root.getBoundingClientRect();
      return { left: r.left - base.left, top: r.top - base.top, right: r.right - base.left, bottom: r.bottom - base.top, width: r.width, height: r.height };
    },
    reportError,
    panel, pictures: null, modes, furniture: null, replay: null, labels,
    kit: { downloads, fake, dom },
  };
  visibility.applyFloor();
  visibility.applyToggles();
  return ctx;
}

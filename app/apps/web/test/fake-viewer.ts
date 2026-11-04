// The fake @walkthrough/viewer (WORK_BREAKDOWN F, DESIGN.md 17.4). With VITE_FAKE_VIEWER=1 the web app's Vite config and
// vitest's web project alias `@walkthrough/viewer` to this file, so the staff app's page flow can be tested before the
// real viewer exists. It exports the names packages/viewer/src/index.ts exports:
//   createViewer         a root div with a canvas (a real WebGL context, lost on dispose), a small panel (the heading) and,
//                        when the model has furniture, a legend with a height box per kind ([data-wt=kind-height], typing
//                        rules of furniture_boxes.js) that emits `heightschange`; it records every create / dispose
//                        (fakeViewerLog, window.__fakeViewer) and keeps the real viewer's life cycle: a constructed
//                        stylesheet in document.adoptedStyleSheets, a window and a document listener, the test hook
//                        (window.__walkthrough with live() / created(), a partial __host) when testHook is on, and on
//                        dispose (idempotent) or on a failed create everything taken back
//   parse*               plain casts (an object check, so a model that is not even an object throws ModelError)
//   parseAddressOptions  DESIGN.md 11.3's rules
//   ModelError, VIEWER_VERSION
// Drawing text goes into the DOM with textContent only, as in the real viewer.
import type {
  AddressOptions,
  BuiltModel,
  CreateViewer,
  FloorKey,
  FurnitureApi,
  FurnitureKindView,
  FurniturePieceView,
  HeightMap,
  ModelErrorLike,
  ModelIssue,
  ParseAddressOptions,
  ParseBuiltModel,
  ParsePresentation,
  ParseReplayData,
  PhotoFrame,
  Presentation,
  ReplayData,
  ReplayPhase,
  TestHookHost,
  TestHookThree,
  ToggleName,
  Viewer,
  ViewerEvents,
  ViewerOptions,
  ViewMode,
} from '../../../packages/viewer/src/contracts';

export type * from '../../../packages/viewer/src/contracts';

export const VIEWER_VERSION = '0.0.0-fake';

/** As the real one: `issues` carry JSON Pointer paths. */
export class ModelError extends Error implements ModelErrorLike {
  readonly issues: ModelIssue[];

  constructor(issues: ModelIssue[], message?: string) {
    super(message ?? `[viewer] model: ${issues.length} issue(s)` +
      (issues.length ? `: ${issues.slice(0, 3).map(i => `${i.path}: ${i.message}`).join('; ')}` : ''));
    this.name = 'ModelError';
    this.issues = issues;
  }
}

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

export const parseBuiltModel: ParseBuiltModel = json => {
  if (!isObject(json)) throw new ModelError([{ path: '', message: 'must be an object' }]);
  if (!Array.isArray(json.floors)) throw new ModelError([{ path: '', message: "must have required property 'floors'" }]);
  return json as unknown as BuiltModel;
};

export const parseReplayData: ParseReplayData = json => {
  if (!isObject(json)) throw new ModelError([{ path: '', message: 'must be an object' }], '[viewer] stages: must be an object');
  return json as unknown as ReplayData;
};

export const parsePresentation: ParsePresentation = json => {
  if (!isObject(json)) throw new ModelError([{ path: '', message: 'must be an object' }], '[viewer] presentation: must be an object');
  return json as unknown as Presentation;
};

// -------------------------------------------------------------------------------------------- address options (D-11.3)
const FRAMES: PhotoFrame[] = ['screen', '16:9', '3:2', '4:3', '1:1', '4:5', '9:16'];
const num = (s: string | null): number | null => {
  if (s === null) return null;
  const v = Number.parseFloat(s);
  return Number.isFinite(v) ? v : null;
};
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export const parseAddressOptions: ParseAddressOptions = search => {
  const q = typeof search === 'string' ? new URLSearchParams(search) : search;
  const a: AddressOptions = {};
  if (q.has('mode') || q.get('build') === '0') a.build = 'skip';
  else if (q.get('build') === 'play') a.build = 'play';
  const speed = q.get('speed');
  if (speed === 'quick' || speed === 'normal' || speed === 'slow') a.speed = speed;
  if (q.get('captions') === '0') a.captions = false;
  const mode = q.get('mode');
  if (mode === 'walk' || mode === 'ghost') a.mode = mode;
  const floor = q.get('floor');
  if (floor) a.floor = floor;   // an empty floor= is dropped, as packages/viewer/src/address.ts does
  if (q.has('x')) a.point = { x: num(q.get('x')), y: num(q.get('y')), z: num(q.get('z')) };
  const yaw = num(q.get('yaw'));
  if (yaw !== null) a.yaw = yaw;
  const pitch = num(q.get('pitch'));
  if (pitch !== null) a.pitch = pitch;
  const lens = num(q.get('lens'));
  if (lens !== null) a.lens = clamp(lens, 12, 85);
  const eye = num(q.get('eye'));
  if (eye !== null) a.eye = clamp(eye, 0.8, 2.2);
  if (q.get('cam') === '1') a.cam = true;
  const frame = q.get('frame');
  if (frame && (FRAMES as string[]).includes(frame)) a.frame = frame as PhotoFrame;
  if (q.get('size') === '4k') a.size = 3840;
  if (q.get('straight') === '1') a.straight = true;
  if (q.get('touch') === '1') a.touch = true;
  if (q.get('nodownload') === '1') a.nodownload = true;
  if (q.get('shot') === '1') a.shot = true;
  if (q.get('picture') === '1') a.picture = true;
  else if (q.get('picture') === '0') a.picture = false;
  if (q.get('test') === '1') a.test = true;
  return a;
};

// --------------------------------------------------------------------------------------------------------- the record
export interface FakeViewerRecord {
  event: 'create' | 'dispose' | 'fail';
  /** The created-counter value of the viewer (0 for a failed create). */
  n: number;
  projectId: string | null;
  version: number | null;
  stamp: string;
  options: ViewerOptions | null;
  heights: HeightMap | null;
  pictures: Partial<Record<FloorKey, string>>;
  hasStages: boolean;
  error?: string;
}

/** Every create / dispose / failed create in this page, in order. */
export const fakeViewerLog: FakeViewerRecord[] = [];
let liveCount = 0;
let createdCount = 0;

export interface FakeViewerGlobal {
  log: FakeViewerRecord[];
  live(): number;
  created(): number;
  /** The live viewers (newest last). */
  viewers: FakeViewer[];
}
export interface FakeViewer extends Viewer {
  /** Tests: emit a public event as the real viewer would. */
  emit<E extends keyof ViewerEvents>(event: E, payload: ViewerEvents[E]): void;
  readonly fake: true;
}

declare global {
  interface Window { __fakeViewer?: FakeViewerGlobal }
}

const liveViewers: FakeViewer[] = [];
function globalRecord(): FakeViewerGlobal {
  return { log: fakeViewerLog, live: () => liveCount, created: () => createdCount, viewers: liveViewers };
}
if (typeof window !== 'undefined') window.__fakeViewer = globalRecord();

/** Tests: the counters back to zero (a fresh page). */
export function resetFakeViewer(): void {
  fakeViewerLog.length = 0;
  liveViewers.length = 0;
  liveCount = 0;
  createdCount = 0;
}

// ------------------------------------------------------------------------------------------------------------- styles
const FAKE_CSS = `
.wtv[data-fake-viewer] { position: relative; width: 100%; height: 100%; overflow: hidden; background: #eef0f2;
  font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1d2329; container: wtv / size; }
.wtv[data-fake-viewer] canvas { display: block; width: 100%; height: 100%; }
.wtv[data-fake-viewer] .fake-panel { position: absolute; top: 12px; left: 12px; width: min(330px, calc(100% - 48px));
  max-height: calc(100% - 60px); overflow: auto; padding: 12px 14px; border-radius: 10px; background: #ffffffee;
  box-shadow: 0 1px 6px #0002; }
.wtv[data-fake-viewer] .fake-panel h1 { font-size: 15px; margin: 0 0 6px; }
.wtv[data-fake-viewer] .fake-note { color: #5b6670; font-size: 12px; margin: 0 0 8px; }
.wtv[data-fake-viewer] .fake-row { display: grid; grid-template-columns: minmax(0, 1fr) 64px; gap: 6px; align-items: center;
  font-size: 12.5px; padding: 1px 0; }
.wtv[data-fake-viewer] .fake-row input { font: inherit; text-align: right; padding: 2px 5px; border: 1px solid #d5dade;
  border-radius: 5px; }
.wtv[data-fake-viewer] .fake-row input[data-bad] { border-color: #b42318; background: #fdecea; }
.wtv[data-fake-viewer] .fake-row input[data-edited] { border-color: var(--accent, #2f6f8f); }
.wtv[data-fake-viewer] .fake-badge { position: absolute; right: 12px; bottom: 10px; color: #5b6670; font-size: 12px; }
`;

// --------------------------------------------------------------------------------------------------- the fake viewer
const MIN_H = 10;
const MAX_H = 5000;
const whole = (v: number) => Math.floor(v + 0.5);
/** furniture_boxes.js `typed`: whole mm 10 - 5000, or null ('', '4,5', '-3', 'abc', 6, 9999). */
export function typedHeight(s: string): number | null {
  const v = /^\s*\d+(\.\d*)?\s*$/.test(s) ? whole(Number(s)) : Number.NaN;
  return v >= MIN_H && v <= MAX_H ? v : null;
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string> = {}, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}

export const createViewer: CreateViewer = (container, project, options = {}) => {
  // 1. Parse before touching the DOM; the container must be in the document (DESIGN.md 11.2).
  const model = parseBuiltModel(project.model);
  const presentation = parsePresentation(project.presentation);
  const stages = project.stages ? parseReplayData(project.stages, model) : null;
  if (!container.isConnected) throw new Error('[viewer] createViewer: the container is not in the document');

  const record = (event: FakeViewerRecord['event'], n: number, error?: string): FakeViewerRecord => ({
    event, n, projectId: project.ids?.projectId ?? null, version: project.ids?.version ?? null, stamp: project.stamp,
    options: options ?? null, heights: project.heights ? { ...project.heights } : null, pictures: { ...(project.pictures ?? {}) },
    hasStages: !!stages, ...(error ? { error } : {}),
  });

  const undo: (() => void)[] = [];
  const runUndo = () => {
    while (undo.length) {
      try { undo.pop()!(); } catch { /* keep going */ }
    }
  };
  const listeners = new Map<keyof ViewerEvents, Set<(p: never) => void>>();
  const emit = <E extends keyof ViewerEvents>(event: E, payload: ViewerEvents[E]) => {
    for (const fn of [...(listeners.get(event) ?? [])]) (fn as (p: ViewerEvents[E]) => void)(payload);
  };

  // Furniture state (the real viewer's starting heights: the model's, then project.heights over them).
  const kindsWithPieces = (model.furnitureKinds ?? [])
    .map(k => ({ k, count: (model.furniture ?? []).filter(p => p.kind === k.key).length }))
    .filter(x => x.count > 0);
  const modelHeight = new Map(kindsWithPieces.map(({ k }) => [k.key, whole(k.height)]));
  const height = new Map(modelHeight);
  const applyMap = (map: HeightMap | null | undefined, resetMissing: boolean) => {
    if (resetMissing) for (const [k, v] of modelHeight) height.set(k, v);
    for (const [k, v] of Object.entries(map ?? {})) {
      const mm = whole(Number(v));
      if (modelHeight.has(k) && mm >= MIN_H && mm <= MAX_H) height.set(k, mm);
    }
  };
  applyMap(project.heights, false);
  const differences = (): HeightMap => {
    const out: HeightMap = {};
    for (const [k, v] of height) if (v !== modelHeight.get(k)) out[k] = v;
    return out;
  };
  const inputs = new Map<string, HTMLInputElement>();
  const showRow = (key: string, keepText = false) => {
    const input = inputs.get(key);
    if (!input) return;
    const v = height.get(key)!;
    if (!keepText) { input.value = String(v); input.removeAttribute('data-bad'); }
    if (v !== modelHeight.get(key)) input.setAttribute('data-edited', ''); else input.removeAttribute('data-edited');
  };

  let mode: ViewMode = 'orbit';
  let floorKey: FloorKey = model.floors[0]?.key ?? '';
  let phase: ReplayPhase = 'off';
  const toggles: Record<ToggleName, boolean> = { plates: true, glass: true, rooms: true, single: true, picture: false };
  let disposed = false;
  let n = 0;

  try {
    // 2. The root, its stylesheet, the canvas with a WebGL context.
    const root = el('div', { class: 'wtv', 'data-wt': 'root', 'data-model-stamp': project.stamp, 'data-fake-viewer': '' });
    container.append(root);
    undo.push(() => root.remove());
    if (typeof CSSStyleSheet === 'function' && 'replaceSync' in CSSStyleSheet.prototype && 'adoptedStyleSheets' in document) {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(FAKE_CSS);
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
      undo.push(() => { document.adoptedStyleSheets = document.adoptedStyleSheets.filter(s => s !== sheet); });
    } else {
      root.append(el('style', {}, FAKE_CSS));
    }
    root.style.setProperty('--accent', presentation.accent ?? '#2f6f8f');
    const canvas = el('canvas', { 'data-fake-canvas': '' });
    root.append(canvas);
    const gl = canvas.getContext('webgl2') as WebGL2RenderingContext | null;   // as three r186: WebGL 2 only, one try
    if (!gl) throw new Error('[viewer] WebGL is not available (the fake viewer could not get a context)');
    undo.push(() => { gl.getExtension('WEBGL_lose_context')?.loseContext(); });
    const draw = () => {
      if (gl.isContextLost()) return;
      gl.clearColor(0xee / 255, 0xf0 / 255, 0xf2 / 255, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
    };
    draw();

    // 3. A window and a document listener, as the real viewer has (resize; keys).
    const onResize = () => draw();
    window.addEventListener('resize', onResize);
    undo.push(() => window.removeEventListener('resize', onResize));
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as Node | null;
      if (t && t !== document.body && t !== document.documentElement && !root.contains(t)) return;   // the app's controls keep their keys
      if (e.code === 'Digit1') setMode('orbit');
      else if (e.code === 'Digit2') setMode('walk');
      else if (e.code === 'Digit3') setMode('ghost');
    };
    document.addEventListener('keydown', onKey);
    undo.push(() => document.removeEventListener('keydown', onKey));

    // 4. The panel: the heading, and the furniture legend.
    const panel = el('div', { class: 'fake-panel', 'data-wt': 'panel' });
    panel.append(el('h1', { 'data-wt': 'heading' }, presentation.heading ?? ''));
    panel.append(el('p', { class: 'fake-note' }, 'Fake viewer (VITE_FAKE_VIEWER=1): the page flow without the 3D viewer.'));
    if (kindsWithPieces.length) {
      const block = el('div', { 'data-wt': 'furniture' });
      block.append(el('div', { 'data-wt': 'furniture-title' }, 'Furniture boxes'));
      const before = new Map<string, number>();
      for (const { k, count } of kindsWithPieces) {
        const row = el('div', { class: 'fake-row', 'data-wt': 'furniture-row', 'data-kind': k.key });
        row.append(el('span', { 'data-wt': 'kind-label', title: k.label }, `${k.label} (${count})`));
        const input = el('input', {
          type: 'text', 'data-wt': 'kind-height', inputmode: 'numeric', autocomplete: 'off', spellcheck: 'false',
          title: `Height in mm, ${MIN_H} to ${MAX_H}`, 'aria-label': `${k.label}: height in mm`,
        });
        inputs.set(k.key, input);
        row.append(input);
        block.append(row);
        const commit = (cancel: boolean) => {
          const v = cancel ? null : typedHeight(input.value);
          const to = v ?? before.get(k.key) ?? height.get(k.key)!;
          if (to !== height.get(k.key)) setTyped(k.key, to, false); else showRow(k.key);
        };
        input.addEventListener('focus', () => {
          before.set(k.key, height.get(k.key)!);
          const v0 = input.value;
          setTimeout(() => { if (document.activeElement === input && input.value === v0) input.select(); }, 0);
        });
        input.addEventListener('input', () => {
          const v = typedHeight(input.value);
          if (v === null && input.value.trim() !== '') input.setAttribute('data-bad', ''); else input.removeAttribute('data-bad');
          if (v !== null && v !== height.get(k.key)) setTyped(k.key, v, true);
        });
        input.addEventListener('blur', () => commit(false));
        input.addEventListener('keydown', e => {
          if (e.key === 'Enter') { commit(false); input.blur(); }
          else if (e.key === 'Escape') { commit(true); input.blur(); }
        });
        showRow(k.key);
      }
      const reset = el('button', { type: 'button', 'data-wt': 'furniture-reset' }, 'Reset heights');
      reset.addEventListener('click', () => {
        applyMap(null, true);
        for (const key of inputs.keys()) showRow(key);
        emit('heightschange', { heights: differences(), source: 'reset' });
      });
      const buttons = el('div', { 'data-wt': 'furniture-buttons' });
      buttons.append(reset);
      block.append(buttons);
      panel.append(block);
    }
    root.append(panel);
    root.append(el('div', { class: 'fake-badge', 'data-wt': 'hint' }, `fake viewer · ${project.stamp}`));
  } catch (err) {
    runUndo();
    fakeViewerLog.push(record('fail', 0, err instanceof Error ? err.message : String(err)));
    throw err;
  }

  function setTyped(key: string, mm: number, keepText: boolean) {
    height.set(key, mm);
    showRow(key, keepText);
    emit('heightschange', { heights: differences(), source: 'typed' });
  }
  function setMode(m: ViewMode) {
    if (m === mode) return;
    mode = m;
    emit('modechange', { mode, floor: floorKey });
  }
  const setPhase = (p: ReplayPhase) => {
    if (p === phase) return;
    phase = p;
    emit('replayphase', { phase });
  };
  if (stages) {
    const build = options.build ?? options.address?.build ?? 'settings';
    phase = build === 'skip' ? 'done' : build;
  }

  const furniture: FurnitureApi | null = kindsWithPieces.length ? {
    pieces: () => (model.furniture ?? []).filter(p => modelHeight.has(p.kind)).map(p => {
      const h = height.get(p.kind)! / 1000;
      return { ...p, approach: [...p.approach], z0: 0, z1: h, visible: true, blocks: true, blocking: true } satisfies FurniturePieceView;
    }),
    kinds: () => kindsWithPieces.map(({ k, count }) => ({
      key: k.key, label: k.label, colour: k.colour, height: height.get(k.key)!, defaultHeight: modelHeight.get(k.key)!, count,
      visible: true, blocks: k.blocks,
    }) satisfies FurnitureKindView),
    setHeight: (key, mm) => {
      const v = whole(Number(mm));
      if (!modelHeight.has(key) || !(v >= MIN_H && v <= MAX_H)) return false;
      setTyped(key, v, false);
      return true;
    },
    setVisible: key => modelHeight.has(key),
    setBlocks: key => modelHeight.has(key),
    setKeepDoorways: () => true,
    keepDoorways: () => true,
    reset: () => {
      applyMap(null, true);
      for (const key of inputs.keys()) showRow(key);
      emit('heightschange', { heights: differences(), source: 'reset' });
    },
    csv: () => '',
    saveCsv: () => '',
    meshOf: () => null,
    apply: () => undefined,
    heights: () => differences(),
    setHeights: map => {
      applyMap(map, true);
      for (const key of inputs.keys()) showRow(key);
    },
  } : null;

  let resolveReady!: () => void;
  const ready = new Promise<void>(r => { resolveReady = r; });
  const raf = typeof requestAnimationFrame === 'function' ? requestAnimationFrame : (fn: () => void) => setTimeout(fn, 16);
  raf(() => resolveReady());

  n = ++createdCount;
  liveCount++;

  const viewer: FakeViewer = {
    fake: true,
    ready,
    get mode() { return mode; },
    get disposed() { return disposed; },
    setMode,
    goToFloor: key => { if (model.floors.some(f => f.key === key)) { floorKey = key; emit('modechange', { mode, floor: key }); } },
    showFloors: () => undefined,
    setToggle: (name, on) => { toggles[name] = on; },
    getToggles: () => ({ ...toggles }),
    openCamera: () => undefined,
    takePhoto: async () => null,
    replay: stages ? {
      get phase() { return phase; },
      generate: () => setPhase('play'),
      skip: () => setPhase('done'),
      openSettings: () => setPhase('settings'),
    } : null,
    furniture,
    getHeights: () => differences(),
    setHeights: map => {
      applyMap(map, true);
      for (const key of inputs.keys()) showRow(key);
    },
    on: (event, fn) => {
      let set = listeners.get(event);
      if (!set) { set = new Set(); listeners.set(event, set); }
      set.add(fn as (p: never) => void);
      return () => { set.delete(fn as (p: never) => void); };
    },
    emit,
    dispose: () => {
      if (disposed) return;
      disposed = true;
      runUndo();
      listeners.clear();
      liveCount--;
      const i = liveViewers.indexOf(viewer);
      if (i >= 0) liveViewers.splice(i, 1);
      if (typeof window !== 'undefined' && window.__walkthrough?.viewer === viewer) {
        delete window.__walkthrough;
        delete window.__host;
      }
      fakeViewerLog.push(record('dispose', n));
    },
  };

  liveViewers.push(viewer);
  if (options.testHook && typeof window !== 'undefined') {
    window.__walkthrough = {
      THREE: {} as TestHookThree,
      viewer,
      version: VIEWER_VERSION,
      live: () => liveCount,
      created: () => createdCount,
      gpu: () => ({ geometries: 0, textures: 0, programs: 0 }),
    };
    window.__host = {
      model,
      furniture,
      pictures: {
        objs: [],
        ready: Promise.resolve(Object.keys(project.pictures ?? {}).map(() => true)),
        src: { ...(project.pictures ?? {}) },
        show: () => undefined,
      },
    } as unknown as TestHookHost;
  }
  fakeViewerLog.push(record('create', n));
  return viewer;
};

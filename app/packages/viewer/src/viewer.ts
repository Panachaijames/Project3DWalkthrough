// createViewer: the assembly, in the init order of DESIGN.md 11.4 (failure path 11.2, dispose 11.8). Owner: builder A.
//  1. parse (ModelError before the DOM is touched); the container must be connected
//  2. createContext: root, renderer, scene, lights, camera (a fixed start), controls, resize
//  3. buildScene -> floors and groups in the scene, the ground plane; pictures; visibility; heights; readouts
//  4. panel (C); then the fitSlabs camera start (it needs the panel)
//  5. modes (B)    6. furniture (C)    7. replay (D) when there are stages
//  8. labels; the test hook when asked; then the start-up in the prototypes' order: replay.start (else applyFloor),
//     applyToggles, modes.applyAddress, the four loop hooks (registered here and only here), loop.start
// Any throw after step 1 tears down whatever exists (root, context, listeners, timers, stylesheet, window hooks) and is
// rethrown; testFailAt (with testHook) throws at the start of a named step for the leak checks.
import type {
  CreateViewer, EventBus, FloorKey, FurnitureApi, HeightMap, InternalEvents, PieceEditMap, ToggleName, Viewer, ViewerEvents,
  ViewerOptions, ViewMode,
} from './contracts';
import { applyCameraStart, createContext, type CoreContext } from './core/context';
import { buildScene } from './core/build';
import { createHeights } from './core/heights';
import { createLabels } from './core/labels';
import { counters } from './core/live';
import { createPictures } from './core/pictures';
import { createReadouts } from './core/readouts';
import { createVisibility } from './core/visibility';
import { installFurniture } from './furniture/index';
import { parseBuiltModel, parseReplayData } from './model/parse';
import { parsePresentation, resolvePresentation } from './model/presentation';
import { installModes } from './modes/index';
import { installReplay } from './replay/index';
import { installTestHook } from './testhook/hook';
import { createPanel } from './ui/panel';

type Step = NonNullable<ViewerOptions['testFailAt']>;

export const createViewer: CreateViewer = (container, project, options) => {
  // 1. everything that can be wrong with the project, before anything is touched
  const model = parseBuiltModel(project.model);
  const presentation = parsePresentation(project.presentation);
  resolvePresentation(presentation, model);
  const stages = project.stages ? parseReplayData(project.stages, model) : null;
  if (!container || typeof container.isConnected !== 'boolean' || !container.isConnected) {
    throw new Error('[viewer] createViewer: the container is not in the document (container.isConnected is false)');
  }
  const testHook = options?.testHook === true;
  const failAt = (step: Step) => {
    if (testHook && options?.testFailAt === step) throw new Error(`[viewer] testFailAt ${step}`);
  };

  let ctx: CoreContext | null = null;
  try {
    // 2. the context
    failAt('context');
    ctx = createContext(container, { ...project, model, presentation, stages }, options) as CoreContext;
    const c = ctx;
    bridgeEvents(c.bus, c.events);

    // 3. the model, the pictures, the ticks, Build settings, the read-outs
    failAt('build');
    const built = buildScene(model, c.presentation);
    c.built = built;
    c.floors = built.floors;
    c.floorByKey = new Map(built.floors.map(f => [f.key, f]));
    for (const f of built.floors) c.scene.add(f.group);
    if (built.groundPlane) c.scene.add(built.groundPlane);
    c.pictures = createPictures(c);
    c.visibility = createVisibility(c);
    c.heights = createHeights(c);
    c.readouts = createReadouts(c);

    // 4. the panel, then the camera start that needs it
    failAt('panel');
    c.panel = createPanel(c);
    if (c.presentation.camera.kind === 'fitSlabs') applyCameraStart(c);

    // 5 - 7. the modes, the furniture, the replay
    failAt('modes');
    c.modes = installModes(c);
    failAt('furniture');
    c.furniture = installFurniture(c);
    failAt('replay');
    c.replay = stages ? installReplay(c) : null;

    // 8. the labels, the handle and the test hook, the start-up
    failAt('labels');
    c.labels = createLabels(c);
    const viewer = makeViewer(c);
    if (testHook) installTestHook(c, viewer);

    failAt('start');
    const address = c.options.address;
    if (c.replay) c.replay.start(c.options.build, address);       // a. as each page's installBuildReplay did
    else c.visibility.applyFloor();
    c.visibility.applyToggles();                                    // b. the pages' applyChecks()
    c.modes.applyAddress(address);                                  // c. the pages' modes.applyUrl()
    const replay = c.replay, modes = c.modes, pictures = c.pictures, labels = c.labels;
    if (replay) c.loop.add('replay', now => replay.tick(now));     // d. the frame hooks, here and only here
    c.loop.add('modes', now => modes.tick(now));
    if (pictures) c.loop.add('sync', () => pictures.sync());
    c.loop.add('overlay', () => labels.place());
    c.loop.start();                                                 // e.
    counters.up();
    return viewer;
  } catch (err) {
    ctx?.teardown();
    throw err;
  }
};

/**
 * The public events made by viewer.ts from the bus, each with one emitter (DESIGN.md 11.5): modechange only when the mode or
 * the floor differs from the last one emitted (the modes emit bus 'mode' from every HUD update, as the prototype's onChange,
 * so also on each lens change); heightschange only for what the legend did (typed, reset), never for setHeights (api) or
 * the doorways tick (tick); boxeschange only for what was deleted or restored in the viewer (removed, restored), never for
 * setPieceEdits (api), so a host that saves on the event and sets what was saved cannot loop (docs/boxes/DESIGN.md 2.8).
 */
export function bridgeEvents(bus: EventBus<InternalEvents>, events: EventBus<ViewerEvents>): void {
  let lastMode: { mode: ViewMode; floor: FloorKey } | null = null;
  bus.on('mode', ({ mode, floor }) => {
    if (lastMode && lastMode.mode === mode && lastMode.floor === floor) return;
    lastMode = { mode, floor };
    events.emit('modechange', { mode, floor });
  });
  bus.on('furniture', ({ heights, source }) => {
    if (source === 'typed' || source === 'reset') events.emit('heightschange', { heights: { ...heights }, source });
  });
  bus.on('pieces', ({ pieceEdits, source }) => {
    if (source === 'removed' || source === 'restored') events.emit('boxeschange', { pieceEdits: copyEdits(pieceEdits), source });
  });
}

/** A copy of an edits map, one level down (the host may keep it). */
const copyEdits = (e: PieceEditMap): PieceEditMap => Object.fromEntries(Object.entries(e).map(([id, edit]) => [id, { ...edit }]));

/**
 * Viewer.furniture: the furniture module's API, inert once the viewer is disposed, like every other handle method (fix
 * step, review finding "code" 12: a host holding a disposed handle, a StrictMode remount or a version switch, could still
 * type heights and write them to the version's localStorage key). After dispose the writes do nothing and say so (false),
 * meshOf is null; the reads answer the last state. The same for the deleted boxes (docs/boxes/DESIGN.md 8.2): removePiece
 * and restorePiece answer [], restoreAll and setPieceEdits do nothing, pieceEdits answers the last state.
 */
export function guardFurniture(api: FurnitureApi | null, isDisposed: () => boolean): FurnitureApi | null {
  if (!api) return null;
  const live = () => !isDisposed();
  return {
    pieces: () => api.pieces(),
    kinds: () => api.kinds(),
    setHeight: (key, mm) => live() && api.setHeight(key, mm),
    setVisible: (key, on) => live() && api.setVisible(key, on),
    setBlocks: (key, on) => live() && api.setBlocks(key, on),
    setKeepDoorways: on => live() && api.setKeepDoorways(on),
    keepDoorways: () => api.keepDoorways(),
    reset: () => { if (live()) api.reset(); },
    csv: () => api.csv(),
    saveCsv: () => (live() ? api.saveCsv() : api.csv()),
    meshOf: id => (live() ? api.meshOf(id) : null),
    apply: () => { if (live()) api.apply(); },
    heights: () => api.heights(),
    setHeights: h => { if (live()) api.setHeights(h); },
    pieceEdits: () => api.pieceEdits(),
    setPieceEdits: e => { if (live()) api.setPieceEdits(e); },
    removePiece: id => (live() ? api.removePiece(id) : []),
    restorePiece: id => (live() ? api.restorePiece(id) : []),
    restoreAll: () => { if (live()) api.restoreAll(); },
  };
}

function makeViewer(c: CoreContext): Viewer {
  let disposed = false;
  const ready = Promise.all([c.pictures ? c.pictures.ready : Promise.resolve([]), c.loop.firstFrame]).then(() => undefined);
  const replay = c.replay;
  const viewer: Viewer = {
    ready,
    get mode() { return c.modes.mode; },
    get disposed() { return disposed; },
    setMode(mode) { if (!disposed) c.modes.setMode(mode); },
    goToFloor(key) { if (!disposed) c.modes.goToFloor(key); },
    showFloors(which) {
      if (disposed) return;
      // the floor buttons: in Walk they change the floor you are on; otherwise they show or hide floors (D-11.5)
      if (c.modes.mode === 'walk') c.modes.goToFloor(which === 'all' ? c.floors[0]!.key : which);
      else c.visibility.setFloorMode(which);
    },
    setToggle(name: ToggleName, on: boolean) { if (!disposed) c.visibility.setToggle(name, on); },
    getToggles() { return { ...c.visibility.toggles }; },
    openCamera(open) { if (!disposed) c.modes.openCam(open); },
    takePhoto() { return disposed ? Promise.resolve(null) : c.modes.takePhoto(); },
    replay: replay ? {
      get phase() { return replay.phase; },
      generate() { if (!disposed) replay.generate(); },
      skip() { if (!disposed) replay.skip(); },
      openSettings() { if (!disposed) replay.openSettings(); },
    } : null,
    furniture: guardFurniture(c.furniture, () => disposed),
    getHeights(): HeightMap { return c.furniture ? { ...c.furniture.heights() } : {}; },
    setHeights(heights: HeightMap) { if (!disposed && c.furniture) c.furniture.setHeights(heights ?? {}); },
    getPieceEdits(): PieceEditMap { return c.furniture ? copyEdits(c.furniture.pieceEdits()) : {}; },
    setPieceEdits(e: PieceEditMap) { if (!disposed && c.furniture) c.furniture.setPieceEdits(e ?? {}); },
    on<E extends keyof ViewerEvents>(event: E, fn: (payload: ViewerEvents[E]) => void) {
      return disposed ? () => {} : c.events.on(event, fn);
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      c.teardown();
      counters.down();
    },
  };
  return viewer;
}

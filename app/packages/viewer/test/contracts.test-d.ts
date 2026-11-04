// Scaffold: every export of DESIGN.md 11.1 assigned to its contracts.ts alias, so a builder whose signature drifts fails
// `npm run typecheck` (tsc -p packages/viewer/tsconfig.test.json). Type-level only: nothing here runs.
import type * as C from '../src/contracts';
import * as index from '../src/index';
import { createViewer } from '../src/viewer';
import { parseAddressOptions } from '../src/address';
import { ModelError, parseBuiltModel, parseReplayData } from '../src/model/parse';
import { DEFAULT_REPLAY_TEXTS, parsePresentation, resolvePresentation, type ReplayTexts } from '../src/model/presentation';
import { DEFAULT_PART_STYLES } from '../src/model/styles';
import { VIEWER_VERSION } from '../src/version';
import { createContext } from '../src/core/context';
import { buildScene } from '../src/core/build';
import { createHeights } from '../src/core/heights';
import { createVisibility } from '../src/core/visibility';
import { createLabels, layoutLabels } from '../src/core/labels';
import { createPictures } from '../src/core/pictures';
import { createReadouts } from '../src/core/readouts';
import { createLoop } from '../src/core/loop';
import { withBvh } from '../src/core/bvh';
import { createDisposer } from '../src/core/disposer';
import { createEventBus } from '../src/core/events';
import { installTestHook } from '../src/testhook/hook';
import { clear, el } from '../src/ui/dom';
import { createRoot } from '../src/ui/root';
import { BASE_CSS } from '../src/ui/css';
import { createPanel } from '../src/ui/panel';
import { installModes } from '../src/modes/index';
import { frameRect, lensFov, outSize, viewFov } from '../src/modes/camera';
import { photoName } from '../src/modes/photo';
import { installFurniture } from '../src/furniture/index';
import { csvField, fixedDecimals, furnitureCsv, parseTypedHeight, stopsWalk, undersideMm, wholeMm } from '../src/furniture/logic';
import { readStoredState, writeStoredState } from '../src/furniture/storage';
import { installReplay } from '../src/replay/index';
import { ease, fillCaption, stepTimes } from '../src/replay/timeline';

// index.ts (the public entry)
export const checks = [
  index.createViewer satisfies C.CreateViewer,
  index.parseAddressOptions satisfies C.ParseAddressOptions,
  index.parseBuiltModel satisfies C.ParseBuiltModel,
  index.parseReplayData satisfies C.ParseReplayData,
  index.parsePresentation satisfies C.ParsePresentation,
  index.VIEWER_VERSION satisfies string,
  new index.ModelError([]) satisfies C.ModelErrorLike,
];

// module by module (A)
const _createViewer: C.CreateViewer = createViewer;
const _parseAddressOptions: C.ParseAddressOptions = parseAddressOptions;
const _parseBuiltModel: C.ParseBuiltModel = parseBuiltModel;
const _parseReplayData: C.ParseReplayData = parseReplayData;
const _parsePresentation: C.ParsePresentation = parsePresentation;
const _resolvePresentation: C.ResolvePresentationFn = resolvePresentation;
const _modelError: C.ModelErrorLike = new ModelError([{ path: '/parts/0/z1', message: 'not above z0' }]);
const _replayTexts: ReplayTexts = DEFAULT_REPLAY_TEXTS;
const _stepTitles: Record<C.StepKey, string> = DEFAULT_REPLAY_TEXTS.stepTitles;
const _styles: Record<C.PartKind, C.PartStyle> = DEFAULT_PART_STYLES;
const _version: string = VIEWER_VERSION;
const _createContext: C.CreateContext = createContext;
const _buildScene: C.BuildScene = buildScene;
const _createHeights: C.CreateHeights = createHeights;
const _createVisibility: C.CreateVisibility = createVisibility;
const _createLabels: C.CreateLabels = createLabels;
const _layoutLabels: C.LayoutLabels = layoutLabels;
const _createPictures: C.CreatePictures = createPictures;
const _createReadouts: C.CreateReadouts = createReadouts;
const _createLoop: C.CreateLoop = createLoop;
const _withBvh: C.WithBvh = withBvh;
const _installTestHook: C.InstallTestHook = installTestHook;

// scaffold (complete)
const _createDisposer: C.CreateDisposer = createDisposer;
const _createEventBus: C.CreateEventBus = createEventBus;
const _el: C.El = el;
const _clear: (node: Node) => void = clear;

// C (ui, furniture)
const _createRoot: C.CreateRoot = createRoot;
const _baseCss: string = BASE_CSS;
const _createPanel: C.CreatePanel = createPanel;
const _installFurniture: C.InstallFurniture = installFurniture;
const _wholeMm: C.WholeMm = wholeMm;
const _parseTypedHeight: C.ParseTypedHeight = parseTypedHeight;
const _fixedDecimals: C.FixedDecimals = fixedDecimals;
const _csvField: C.CsvField = csvField;
const _furnitureCsv: C.FurnitureCsv = furnitureCsv;
const _undersideMm: C.UndersideMm = undersideMm;
const _stopsWalk: C.StopsWalk = stopsWalk;
const _readStoredState: C.ReadStoredState = readStoredState;
const _writeStoredState: C.WriteStoredState = writeStoredState;

// B (modes)
const _installModes: C.InstallModes = installModes;
const _lensFov: C.LensFov = lensFov;
const _viewFov: C.ViewFov = viewFov;
const _frameRect: C.FrameRect = frameRect;
const _outSize: C.OutSize = outSize;
const _photoName: C.PhotoName = photoName;

// D (replay)
const _installReplay: C.InstallReplay = installReplay;
const _stepTimes: C.StepTimes = stepTimes;
const _fillCaption: C.FillCaption = fillCaption;
const _ease: C.Ease = ease;

export const assigned = [
  _createViewer, _parseAddressOptions, _parseBuiltModel, _parseReplayData, _parsePresentation, _resolvePresentation,
  _modelError, _replayTexts, _stepTitles, _styles, _version, _createContext, _buildScene, _createHeights, _createVisibility,
  _createLabels, _layoutLabels, _createPictures, _createReadouts, _createLoop, _withBvh, _installTestHook, _createDisposer,
  _createEventBus, _el, _clear, _createRoot, _baseCss, _createPanel, _installFurniture, _wholeMm, _parseTypedHeight,
  _fixedDecimals, _csvField, _furnitureCsv, _undersideMm, _stopsWalk, _readStoredState, _writeStoredState, _installModes,
  _lensFov, _viewFov, _frameRect, _outSize, _photoName, _installReplay, _stepTimes, _fillCaption, _ease,
];

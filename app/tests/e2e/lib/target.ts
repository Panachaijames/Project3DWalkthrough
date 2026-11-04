// The two targets of the ported browser checks (DESIGN.md 17.4; WORK_BREAKDOWN S.9). Scaffold; read-only for builders.
//   E2E_TARGET=app (default): the offline files dist/offline/<projectId>-v<n>.html, with the new selectors.
//   E2E_TARGET=prototype:     the prototype pages, with their selectors and the shim (lib/prototype-shim.ts), so each
//                             builder proves the port of its checks before the app exists.
// Checks of behaviour this design changes on purpose are tagged @app-only; the config skips them on the prototype target.
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import type { Locator, Page } from '@playwright/test';
import type {} from '../../../packages/viewer/src/contracts';
import { installPrototypeShim } from './prototype-shim';

export type Target = 'app' | 'prototype';
export const TARGET: Target = process.env.E2E_TARGET === 'prototype' ? 'prototype' : 'app';
export const isApp = TARGET === 'app';
export const APP_ONLY = '@app-only';
export const TIMED = '@timed';

export const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
export const PROTOTYPES = path.resolve(APP, '..');

export type VersionKey = 'bank-v1' | 'bank-v2' | 'suite' | 'house' | 'hotel';
export interface VersionRef {
  key: VersionKey;
  projectId: string;
  version: number;
  /** The prototype page, relative to the project folder. */
  prototype: string;
  /** Floor keys in model order. */
  floors: string[];
  /** The model-data stamp (the house's is the sha1 of its converted model.json: read it from version.json at app time). */
  stamp: string | null;
  hasReplay: boolean;
  hasFurniture: boolean;
}

export const VERSIONS: Record<VersionKey, VersionRef> = {
  'bank-v1': { key: 'bank-v1', projectId: 'bank-sampeng', version: 1, prototype: 'bank_test/previous_before_fix_round_2026-10-27/bank_3d_preview.html', floors: ['L1', 'L2'], stamp: '4b02dc17f286', hasReplay: true, hasFurniture: false },
  'bank-v2': { key: 'bank-v2', projectId: 'bank-sampeng', version: 2, prototype: 'bank_test/bank_3d_preview.html', floors: ['L1', 'L2'], stamp: 'c3a9408304a2', hasReplay: true, hasFurniture: true },
  suite: { key: 'suite', projectId: 'presidential-suite', version: 1, prototype: 'presidential_test/presidential_3d_preview.html', floors: ['suite'], stamp: 'f1b95c53eb3d', hasReplay: true, hasFurniture: true },
  house: { key: 'house', projectId: 'sukhumvit-house', version: 1, prototype: 'cad_test/house_3d_preview.html', floors: ['ground', 'upper'], stamp: null, hasReplay: true, hasFurniture: true },
  hotel: { key: 'hotel', projectId: 'hotel-lobby', version: 1, prototype: 'hotel_test/hotel_3d_preview.html', floors: ['F1', 'F2'], stamp: '6ab030750886', hasReplay: false, hasFurniture: true },
};

/** The file of a version on this target. */
export function pagePath(v: VersionKey): string {
  const ref = VERSIONS[v];
  return isApp ? path.join(APP, 'dist', 'offline', `${ref.projectId}-v${ref.version}.html`) : path.join(PROTOTYPES, ref.prototype);
}

/** The file URL of a version on this target, with an address query (e.g. '?build=0&nodownload=1&test=1'). */
export function pageUrl(v: VersionKey, query = ''): string {
  return pathToFileURL(pagePath(v)).href + query;
}

// ------------------------------------------------------------------------------------------------- selectors (DESIGN.md 11.6)
type Sel = string;
export interface SelectorMap {
  root: Sel; panel: Sel; hint: Sel; legend: Sel; room: Sel; error: Sel; heading: Sel; intro: Sel; stampMeta: Sel;
  floorButton(key: 'all' | string): Sel; floorButtons: Sel;
  toggle(name: 'plates' | 'glass' | 'rooms' | 'single' | 'picture'): Sel;
  modeButton(mode: 'orbit' | 'walk' | 'ghost'): Sel; cameraBtn: Sel;
  hud: Sel; hudText: Sel; hudCamera: Sel; exit: Sel; cross: Sel;
  cameraPanel: Sel; cameraClose: Sel; lens: Sel; lensValue: Sel; lensPreset(mm: number): Sel; eye: Sel; eyeValue: Sel;
  tilt: Sel; tiltValue: Sel; straight: Sel; first: Sel; firstNote: Sel;
  frameSelect: Sel; sizeSelect: Sel; px: Sel; grid: Sel; shot: Sel; photos: Sel; frame: Sel; flash: Sel;
  stick: Sel; updown: Sel; up: Sel; down: Sel; snap: Sel;
  replayCard: Sel; replaySettings: Sel; replayPlay: Sel; replayFacts: Sel; replayLayers: Sel; replayFile: Sel; replayLayersTitle: Sel;
  replayInput(floor: string, prop: 'level' | 'height'): Sel; replaySpeed(speed: 'quick' | 'normal' | 'slow'): Sel;
  replayCaptions: Sel; replayGo: Sel; replaySkipSettings: Sel; replaySkip: Sel;
  replayStep(state?: 'done' | 'now' | 'todo'): Sel; replayBar: Sel; replayCaption: Sel; replayAgain: Sel; replayOpen: Sel;
  furniture: Sel; furnitureTitle: Sel; furnitureNote: Sel; furnitureAll: Sel; furnitureKeep: Sel; furnitureButtons: Sel;
  furnitureReset: Sel; furnitureSave: Sel; furnitureTip: Sel;
  furnitureRow(kind: string): Sel; kindShow: Sel; kindSwatch: Sel; kindLabel: Sel; kindHeight: Sel; kindStops: Sel;
}

const wt = (name: string) => `[data-wt=${name}]`;
const q = (s: string) => JSON.stringify(s);

export const APP_SELECTORS: SelectorMap = {
  root: wt('root'), panel: wt('panel'), hint: wt('hint'), legend: wt('legend'), room: wt('room'), error: wt('error'),
  heading: wt('heading'), intro: wt('intro'), stampMeta: 'meta[name=model-data]',
  floorButton: key => `${wt('floors')} [data-floor=${q(key)}]`, floorButtons: `${wt('floors')} [data-floor]`,
  toggle: name => `input${wt('toggle')}[data-toggle=${name}]`,
  modeButton: mode => `${wt('modes')} [data-mode=${mode}]`, cameraBtn: wt('camera-btn'),
  hud: wt('hud'), hudText: wt('hud-text'), hudCamera: wt('hud-camera'), exit: wt('exit'), cross: wt('cross'),
  cameraPanel: wt('camera-panel'), cameraClose: wt('camera-close'), lens: wt('lens'), lensValue: wt('lens-value'),
  lensPreset: mm => `${wt('lens-preset')}[data-mm="${mm}"]`, eye: wt('eye'), eyeValue: wt('eye-value'), tilt: wt('tilt'),
  tiltValue: wt('tilt-value'), straight: wt('straight'), first: wt('first'), firstNote: wt('first-note'),
  frameSelect: wt('frame-select'), sizeSelect: wt('size-select'), px: wt('px'), grid: wt('grid'), shot: wt('shot'),
  photos: wt('photos'), frame: wt('frame'), flash: wt('flash'),
  stick: wt('stick'), updown: wt('updown'), up: wt('up'), down: wt('down'), snap: wt('snap'),
  replayCard: wt('replay-card'), replaySettings: wt('replay-settings'), replayPlay: wt('replay-play'), replayFacts: wt('replay-facts'),
  replayLayers: wt('replay-layers'), replayFile: wt('replay-file'), replayLayersTitle: wt('replay-layers-title'),
  replayInput: (floor, prop) => `${wt('replay-card')} input[data-floor=${q(floor)}][data-prop=${prop}]`,
  replaySpeed: speed => `${wt('replay-speed')} [data-speed=${speed}]`, replayCaptions: wt('replay-captions'),
  replayGo: wt('replay-go'), replaySkipSettings: wt('replay-skip-settings'), replaySkip: wt('replay-skip'),
  replayStep: state => `${wt('replay-steps')} li${state ? `[data-state=${state}]` : ''}`, replayBar: `${wt('replay-bar')} i`,
  replayCaption: wt('replay-caption'), replayAgain: wt('replay-again'), replayOpen: wt('replay-open'),
  furniture: wt('furniture'), furnitureTitle: wt('furniture-title'), furnitureNote: wt('furniture-note'), furnitureAll: wt('furniture-all'),
  furnitureKeep: wt('furniture-keep'), furnitureButtons: wt('furniture-buttons'), furnitureReset: wt('furniture-reset'),
  furnitureSave: wt('furniture-save'), furnitureTip: wt('furniture-tip'),
  furnitureRow: kind => `${wt('furniture-row')}[data-kind=${q(kind)}]`, kindShow: wt('kind-show'), kindSwatch: wt('kind-swatch'),
  kindLabel: wt('kind-label'), kindHeight: wt('kind-height'), kindStops: wt('kind-stops'),
};

export const PROTOTYPE_SELECTORS: SelectorMap = {
  root: 'body', panel: '#panel', hint: '#hint', legend: '.legend', room: '.room', error: '#vm-err',
  heading: '#panel h1', intro: '#panel > p', stampMeta: 'meta[name=model-data]',
  floorButton: key => `#floors [data-f=${q(key === 'all' ? 'both' : key)}]`, floorButtons: '#floors [data-f]',
  toggle: name => `#${name}`,
  modeButton: mode => `#vm-modes [data-m=${mode}]`, cameraBtn: '#vm-cam-btn',
  hud: '#vm-hud', hudText: '#vm-hud-t', hudCamera: '#vm-hud-cam', exit: '#vm-exit', cross: '#vm-cross',
  cameraPanel: '#vm-cam', cameraClose: '#vm-cam-close', lens: '#vm-lens', lensValue: '#vm-lens-v',
  lensPreset: mm => `[data-mm="${mm}"]`, eye: '#vm-eye', eyeValue: '#vm-eye-v', tilt: '#vm-tilt', tiltValue: '#vm-tilt-v',
  straight: '#vm-straight', first: '#vm-first', firstNote: '#vm-first-note',
  frameSelect: '#vm-frame-sel', sizeSelect: '#vm-size', px: '#vm-px', grid: '#vm-grid', shot: '#vm-shot', photos: '#vm-photos',
  frame: '#vm-frame', flash: '#vm-flash',
  stick: '#vm-stick', updown: '#vm-ud', up: '#vm-up', down: '#vm-down', snap: '#vm-snap',
  replayCard: '#br-card', replaySettings: '#br-settings', replayPlay: '#br-play', replayFacts: '#br-card ul', replayLayers: '#br-card details',
  replayFile: '#br-card .br-file', replayLayersTitle: '#br-card details summary',
  replayInput: (floor, prop) => `#br-card input[data-k=${q(floor)}][data-p=${prop}]`,
  replaySpeed: speed => `#br-speed [data-s=${speed}]`, replayCaptions: '#br-cap', replayGo: '#br-go', replaySkipSettings: '#br-skip0',
  replaySkip: '#br-skip',
  replayStep: state => `#br-steps li${state === 'done' ? '.br-done' : state === 'now' ? '.br-now' : state === 'todo' ? ':not(.br-done):not(.br-now)' : ''}`,
  replayBar: '#br-bar i', replayCaption: '#br-sub', replayAgain: '#br-again', replayOpen: '#br-open',
  furniture: '.fb-block', furnitureTitle: '.fb-title span', furnitureNote: '.fb-note', furnitureAll: '.fb-all', furnitureKeep: '.fb-keep',
  furnitureButtons: '.fb-btns', furnitureReset: '.fb-reset', furnitureSave: '.fb-save', furnitureTip: '.fb-tip',
  furnitureRow: kind => `.fb-row[data-k=${q(kind)}]`, kindShow: '.fb-show', kindSwatch: '.fb-sw', kindLabel: '.fb-lab', kindHeight: '.fb-h',
  kindStops: '.fb-blk',
};

/** The selector map of this target. */
export const sel: SelectorMap = isApp ? APP_SELECTORS : PROTOTYPE_SELECTORS;

/** An active button: aria-pressed="true" (app) or class "on" (prototype). */
export async function isOn(el: Locator): Promise<boolean> {
  return el.evaluate((e, app) => (app ? e.getAttribute('aria-pressed') === 'true' : e.classList.contains('on')), isApp);
}

/** A furniture height box's state: data-edited / data-bad (app) or .fb-edited / .fb-bad (prototype). */
export async function hasFlag(el: Locator, flag: 'edited' | 'bad'): Promise<boolean> {
  return el.evaluate((e, a) => (a.app ? e.hasAttribute(`data-${a.flag}`) : e.classList.contains(`fb-${a.flag}`)), { app: isApp, flag });
}

// -------------------------------------------------------------------------------- the house's mesh classes (DESIGN.md 17.4)
export type MeshClass = 'wall' | 'lintel' | 'piece' | 'pane' | 'glass' | 'single';
const MESH_CLASSES: Record<Target, Record<MeshClass, RegExp>> = {
  prototype: {
    wall: /:wall$/, lintel: /:lintels and sills$/, piece: /:(lintels and sills|window panes)$/, pane: /:window panes$/,
    glass: /:glass$/, single: /:single$/,
  },
  app: {
    wall: / solid:follow$/, lintel: / solid:top$/, piece: / (solid:top|sill:clip|pane:top|pane:clip)$/, pane: / pane:(top|clip)$/,
    glass: / glass:follow$/, single: / single:own$/,
  },
};
/** Does a ray hit's mesh name belong to the class on this target? (Classify by class, never by a literal name.) */
export function meshIs(name: string | null | undefined, cls: MeshClass): boolean {
  return !!name && MESH_CLASSES[TARGET][cls].test(name);
}
/** The first class a mesh name belongs to ('piece' is checked after the narrower lintel / pane), or null. */
export function meshClass(name: string | null | undefined): MeshClass | null {
  for (const cls of ['wall', 'lintel', 'pane', 'piece', 'glass', 'single'] as MeshClass[]) if (meshIs(name, cls)) return cls;
  return null;
}

// --------------------------------------------------------------------------------------------- fitted meshes, floor plates
/** Names of the meshes refitted on a wall-height change, per floor: app __host.fitted (ground 4, upper 2), prototype __host.pieces (2 and 2). */
export async function fittedNames(page: Page): Promise<Record<string, string[]>> {
  return page.evaluate(app => {
    const h = window.__host as unknown as Record<string, unknown>;
    if (app) {
      const fitted = h.fitted as Record<string, { name: string }[]>;
      return Object.fromEntries(Object.entries(fitted).map(([k, ms]) => [k, ms.map(m => m.name)]));
    }
    const pieces = (h.pieces ?? {}) as Record<string, Record<string, unknown>>;
    return Object.fromEntries(Object.entries(pieces).map(([k, byName]) => [k, Object.keys(byName)]));
  }, isApp);
}

export interface PlateRing { o: [number, number][]; h: [number, number][][] }
/** The floor plates' outlines per floor: app = the slab parts' { o, h } from __host.model; prototype = __host.plates. */
export async function plates(page: Page): Promise<Record<string, PlateRing[]>> {
  return page.evaluate(app => {
    const h = window.__host as unknown as Record<string, unknown>;
    if (!app) return h.plates as Record<string, PlateRing[]>;
    const model = h.model as { floors: { key: string }[]; parts: { floor: string; kind: string; o: [number, number][]; h: [number, number][][] }[] };
    const out: Record<string, PlateRing[]> = {};
    for (const f of model.floors) out[f.key] = model.parts.filter(p => p.floor === f.key && p.kind === 'slab').map(p => ({ o: p.o, h: p.h }));
    return out;
  }, isApp);
}

// ------------------------------------------------------------------------------------------------- network, readiness
/**
 * App target: every request that is not file:, data: or blob: is aborted and recorded (the offline file must need no
 * network). Prototype target: nothing (the pages load three.js from cdn.jsdelivr.net). Call before page.goto.
 */
export async function noNetwork(page: Page): Promise<{ requests: string[] }> {
  const requests: string[] = [];
  if (!isApp) return { requests };
  page.on('request', r => { if (!/^(file|data|blob):/i.test(r.url())) requests.push(r.url()); });
  await page.route(/^(?!file:|data:|blob:)/i, route => route.abort('blockedbyclient'));
  return { requests };
}

/**
 * Waits until the viewer is up. App: window.__walkthrough.viewer.ready (needs ?test=1). Prototype: window.__viewer, then
 * 1.2 s as viewer-modes/cdp.mjs goto did, then the shim.
 */
export async function waitReady(page: Page, timeoutMs = 60_000): Promise<void> {
  if (isApp) {
    await page.waitForFunction(() => !!window.__walkthrough?.viewer, undefined, { timeout: timeoutMs });
    await page.evaluate(() => window.__walkthrough!.viewer.ready);
    return;
  }
  await page.waitForFunction(() => !!window.__viewer, undefined, { timeout: timeoutMs });
  await page.waitForTimeout(1200);
  await installPrototypeShim(page);
}

/** Opens a version on this target ('?build=0&nodownload=1&test=1' unless given) and waits until it is ready. */
export async function openVersion(page: Page, v: VersionKey, query = '?build=0&nodownload=1&test=1'): Promise<void> {
  await page.goto(pageUrl(v, query));
  await waitReady(page);
}

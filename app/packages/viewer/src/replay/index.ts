// installReplay: the build replay, the "loading phase" (port of viewer-modes/build_replay.js; DESIGN.md 7, 11, 12, 13).
// Owner: builder D.
//
//   Build settings  the drawing in top view; each floor's level and wall height; the layers found; the replay speed
//   Generate        seven steps with this drawing's numbers: read the drawing, sort the layers, line up the floors,
//                   pair the wall faces, merge into wall runs, raise the walls, finish; then the normal viewer
// The build itself takes seconds; the replay shows the steps the builder recorded, slowed down to watch.
//
// What the prototype's host passed, the viewer context has: the floor records (group, rise, late), the replay data
// (ctx.stages), the ground plane (the house page's `hide` list: ctx.built.groundPlane), the heights (ctx.heights.apply:
// levels, wall scale, plinths, fitted parts, Walk levels: the replay never scales geometry itself), and the restore hook
// (ctx.visibility.applyFloor / applyToggles, ctx.furniture.apply). Modes are locked while the card or the replay is up.
// Start-up is start(build, address), called by viewer.ts before modes.applyAddress (DESIGN.md 11.4); the per-frame work
// is tick(), which viewer.ts registers in the loop's 'replay' phase (no ctx.loop.add here).
import { Plane, Vector3, type LineSegments, type Material, type Mesh } from 'three';
import type { FloorSettings, InstallReplay, ReplayApi, ReplayPhase, ReplayState, ReplayStep, SettingsMap, StepKey, Vec2 } from '../contracts';
import { applyScene, fadeLate, materialsOf, recordLate, restoreLate, showSolids, type LateLook, type RiseRt } from './apply';
import { freeRect, type Pose } from './camera';
import { REPLAY_CSS } from './css';
import {
  boundsEmpty, lineBounds, makeReplayObjects, partBounds, replayColors, unmakeReplayObjects, type Made, type ReplayFloorRt,
} from './objects';
import { installRiseShader } from './shader';
import { clamp01, DT_CAP, fillCaption, HOLD_MS, isSpeed, SPEEDS, stepTimes } from './timeline';
import { buildUi, markSpeed, readSetting, renderCaption, renderSteps, replayTexts, setBar, show, syncInputs } from './ui';

/** Keys go to the viewer unless you are typing, or using the arrow keys on a focused slider or list (viewer_modes.js). */
function typing(e: KeyboardEvent): boolean {
  const t = e.target as Element | null;
  if (!t || typeof t.matches !== 'function') return false;
  if (t.matches('textarea, input[type=text], input[type=number], input[type=search], input:not([type])')) return true;
  return t.matches('input[type=range], select') && (e.code || '').startsWith('Arrow');
}

const copySettings = (s: SettingsMap): SettingsMap =>
  Object.fromEntries(Object.entries(s).map(([k, v]) => [k, { level: v.level, height: v.height } satisfies FloorSettings]));

export const installReplay: InstallReplay = ctx => {
  const stages = ctx.stages;
  if (!stages) return null;
  const { camera, controls, renderer, scene } = ctx;
  const texts = replayTexts(stages);
  const colors = replayColors(stages);
  const ground = ctx.built.groundPlane;

  // ---------------------------------------------------------------- the floors, as the replay sees them (model order)
  const floors: ReplayFloorRt[] = ctx.floors.map(rec => {
    const mf = ctx.model.floors.find(f => f.key === rec.key);
    const level = mf?.level ?? rec.modelLevel, height = mf?.wallHeight ?? rec.wallHeight;
    const sf = stages.floors?.[rec.key];
    const lines = sf?.lines ?? {};
    let b = lineBounds(lines);
    if (boundsEmpty(b)) b = partBounds(ctx.model.parts, rec.key);
    const sheet: Vec2 = Array.isArray(sf?.sheet) ? [Number(sf.sheet[0]) || 0, Number(sf.sheet[1]) || 0] : [0, 0];
    return {
      rec, key: rec.key, name: rec.name, level, height, sheet, lines, pieces: sf?.pieces ?? {}, rings: sf?.rings ?? {}, b,
      u: { uRise: { value: 1 }, uBase: { value: level } },
    };
  });

  const times = stepTimes(texts.stepTitles);
  const steps: ReplayStep[] = times.map(t => ({ ...t, caption: (s: SettingsMap) => fillCaption(stages.captions?.[t.key] ?? '', s) }));
  const timesByKey = Object.fromEntries(times.map(t => [t.key, [t.t0, t.t1] as const])) as Record<StepKey, readonly [number, number]>;
  const st: ReplayState = {
    phase: 'off', T: 0, speed: 'normal', captions: true, last: 0, endAt: 0, step: null,
    settings: Object.fromEntries(floors.map(f => [f.key, { level: f.level, height: f.height }])),
  };
  /** The view the replay ends on: the start-up view, or the view you left when you replay from the viewer. */
  const final: Pose = { pos: camera.position.clone(), target: controls.target.clone() };
  const scanPlane = new Plane(new Vector3(-1, 0, 0), 0);      // keeps x <= constant
  const sweepPlane = new Plane(new Vector3(-1, 0, 0), 0);

  // ---------------------------------------------------------------- the walls grow: the shader patch on every rise item
  // Every solid of a floor rises with its floor's uniforms. A material shared by solids of two floors (one per kind in
  // the test kit) would carry one floor's uniforms for both: the other floor's solids get their own copy (tracked).
  const rises = new Map<ReplayFloorRt, RiseRt[]>();
  const owners = new Map<Material, ReplayFloorRt>();
  const copies = new Map<Material, Map<ReplayFloorRt, Material>>();
  const ownMaterial = (m: Material, f: ReplayFloorRt, patch: boolean): Material => {
    const by = owners.get(m);
    if (by === f) return m;
    if (by === undefined) { owners.set(m, f); if (patch) installRiseShader(m, f.u); return m; }
    let perFloor = copies.get(m);
    if (!perFloor) copies.set(m, (perFloor = new Map()));
    let copy = perFloor.get(f);
    if (!copy) {
      copy = ctx.disposer.track(m.clone());
      perFloor.set(f, copy);
      owners.set(copy, f);
      if (patch) installRiseShader(copy, f.u);
    }
    return copy;
  };
  const ownMaterials = (obj: Mesh | LineSegments, f: ReplayFloorRt, patch: boolean): void => {
    const m = obj.material;
    obj.material = Array.isArray(m) ? m.map(x => ownMaterial(x, f, patch)) : ownMaterial(m, f, patch);
  };
  for (const f of floors) {
    const list: RiseRt[] = [];
    for (const item of f.rec.rise) {
      ownMaterials(item.mesh, f, true);
      item.mesh.frustumCulled = false;                       // the drawn shape can differ from the stored one
      if (item.edges) ownMaterials(item.edges, f, false);
      list.push({ item, edgeOpacity: item.edges ? (materialsOf(item.edges)[0]?.opacity ?? 0.6) : 0.6 });
    }
    rises.set(f, list);
  }
  const look: LateLook = new WeakMap();
  recordLate(floors, look);

  // ---------------------------------------------------------------- UI: the card and the caption in the root, the Build row in the panel
  const ui = buildUi({ floors: floors.map(f => ({ key: f.key, name: f.name })), stages, texts, steps });
  ctx.ui.addStyle(REPLAY_CSS);
  ctx.ui.root.append(ui.card, ui.caption);
  (ctx.panel.slot('build') ?? ctx.panel.el).append(ui.row);
  ctx.disposer.add(() => { ui.card.remove(); ui.caption.remove(); ui.row.remove(); });

  const listen = ctx.disposer.listen.bind(ctx.disposer) as (t: EventTarget, type: string, fn: (e: Event) => void) => void;
  for (const b of ui.speed) {
    listen(b, 'click', () => { const s = b.getAttribute('data-speed'); if (isSpeed(s)) { st.speed = s; markSpeed(ui, st.speed); } });
  }
  for (const i of ui.inputs) {
    listen(i, 'change', () => {
      const cur = st.settings[i.getAttribute('data-floor') ?? ''];
      const prop = i.getAttribute('data-prop') === 'height' ? 'height' : 'level';
      if (cur) cur[prop] = readSetting(i.value, prop, cur[prop]);
      syncInputs(ui, st.settings); applySettings();
    });
  }
  listen(ui.captions, 'change', () => { st.captions = ui.captions.checked; });
  listen(ui.go, 'click', () => generate());
  listen(ui.skipSettings, 'click', () => skip());
  listen(ui.skip, 'click', () => skip());
  listen(ui.again, 'click', () => { openSettings(); generate(); });
  listen(ui.open, 'click', () => openSettings());

  // ---------------------------------------------------------------- replay objects (made fresh for every run)
  let made: Made | null = null;
  function make(): void {
    unmake();
    made = makeReplayObjects({ scene, floors, colors, accent: ctx.presentation.accent, scanPlane, sweepPlane });
  }
  function unmake(): void {
    if (!made) return;
    unmakeReplayObjects(made, scene);
    made = null;
  }
  ctx.disposer.add(unmake);

  // ---------------------------------------------------------------- settings -> the model (core/heights does all of it)
  function applySettings(): void {
    ctx.heights.apply(copySettings(st.settings));
  }

  // ---------------------------------------------------------------- the camera
  function setPose(p: Pose): void { camera.position.copy(p.pos); controls.target.copy(p.target); camera.lookAt(p.target); }

  // ---------------------------------------------------------------- apply(T): the scene, the camera, the step list, bar and caption
  function apply(T: number): void {
    if (!made) return;
    const size = ctx.size();
    const cardRect = ui.card.style.display === 'none' ? null : ctx.rectOf(ui.card);
    const p = applyScene(T, {
      made, floors, rises, settings: st.settings, colors, times: timesByKey, scanPlane, sweepPlane, look, ground,
      view: { width: size.width, height: size.height, fov: camera.fov },
      fr: freeRect(size, cardRect, st.captions && st.phase === 'play'), final,
    });
    setPose(p);
    const now = steps.find(s => T < s.t1) ?? steps[steps.length - 1]!, ended = T >= 1;
    if (st.step !== now.key || st.captionDirty || st.ended !== ended) {      // at the very end, tick the last step too
      st.step = now.key; st.captionDirty = false; st.ended = ended;
      renderSteps(ui, steps, T, now);
      renderCaption(ui, now.title, now.caption(st.settings));
    }
    setBar(ui, T);
    show(ui.caption, st.captions && st.phase === 'play');
  }

  // ---------------------------------------------------------------- phases: settings -> play -> done
  let told: ReplayPhase = 'off';
  function phaseChanged(): void {                  // bus replayPhase (labels, panel) and the public replayphase event
    if (st.phase === told) return;
    told = st.phase;
    try { ctx.bus.emit('replayPhase', { phase: st.phase }); } catch (err) { ctx.reportError(err); }
    try { ctx.events.emit('replayphase', { phase: st.phase }); } catch (err) { ctx.reportError(err); }
  }
  function restore(): void {                       // the viewer's own visibility rules again (the pages' restore hook)
    const hooks = [() => ctx.visibility.applyFloor(), () => ctx.visibility.applyToggles(), () => ctx.furniture?.apply()];
    for (const hook of hooks) { try { hook(); } catch (err) { ctx.reportError(err); } }
  }
  function enter(): void {                         // hide the finished model, show the drawing
    const modes = ctx.modes;
    if (modes) { if (modes.mode !== 'orbit') modes.setMode('orbit'); modes.lock(true); }
    // Finish any glide left from the last mouse drag now, so it does not keep turning the view during or after the replay.
    const damping = controls.enableDamping;
    controls.enableDamping = false; controls.update(); controls.enableDamping = damping;
    ctx.ui.setFlag('replay', true);
    controls.enabled = false;
    renderer.localClippingEnabled = true;
    for (const f of floors) f.rec.group.visible = true;
    recordLate(floors, look);                      // late objects added since install (their own look, not yet faded)
    make();
    show(ui.card, true);
  }
  function openSettings(): void {
    const fromViewer = st.phase === 'done';
    enter();
    // Started from the viewer (Replay / Build settings): end on the view you left, not the start-up view.
    if (fromViewer) { final.pos.copy(camera.position); final.target.copy(controls.target); }
    st.phase = 'settings'; st.T = 0;
    show(ui.settings, true); show(ui.play, false);
    syncInputs(ui, st.settings); markSpeed(ui, st.speed); applySettings();
    apply(0);
    show(ui.caption, false);
    phaseChanged();
  }
  function generate(): void {
    if (st.phase !== 'settings') openSettings();
    applySettings();
    st.phase = 'play'; st.T = 0; st.step = null; st.paused = false; st.endAt = 0; st.last = performance.now();
    show(ui.settings, false); show(ui.play, true);
    apply(0);
    phaseChanged();
  }
  function finish(): void {                        // the normal viewer, exactly as without the replay
    st.T = 1;
    if (made) apply(1);
    unmake();
    for (const f of floors) {
      f.rec.group.position.set(0, st.settings[f.key]!.level - f.level, 0);
      showSolids(f, rises.get(f) ?? [], 1, 1);
    }
    fadeLate(floors, look, ground, 1);
    restoreLate(floors, look, ground);
    setPose({ pos: final.pos.clone(), target: final.target.clone() });
    renderer.localClippingEnabled = false;
    controls.enabled = true;
    show(ui.card, false); show(ui.caption, false);
    ctx.ui.setFlag('replay', false);
    st.phase = 'done';
    restore();
    ctx.modes?.lock(false);
    phaseChanged();
  }
  function skip(): void {
    if (st.phase === 'off' || st.phase === 'done') return;
    finish();
  }
  function seek(T: number): void {                 // jump to a moment of the replay and hold it there (tests, screenshots)
    if (st.phase !== 'play') generate();
    st.paused = true; st.T = clamp01(Number.isFinite(T) ? T : 0); st.step = null;
    apply(st.T);
  }
  function tick(now: number): void {
    if (st.phase === 'settings') { apply(0); return; }
    if (st.phase !== 'play') return;
    if (st.paused) { apply(st.T); return; }
    const t = Number.isFinite(now) ? now : performance.now();
    const dt = Math.min(DT_CAP, Math.max(0, (t - st.last) / 1000));
    st.last = t;
    st.T = Math.min(1, st.T + dt / SPEEDS[st.speed]);
    apply(st.T);
    if (st.T >= 1) { if (!st.endAt) st.endAt = t + HOLD_MS; else if (t >= st.endAt) { st.endAt = 0; finish(); } }
  }

  // Esc skips the replay while it plays (a key of the viewer: on the page or inside the root, not while typing).
  const root = ctx.ui.root, doc = root.ownerDocument;
  listen(doc.defaultView ?? window, 'keydown', e => {
    const k = e as KeyboardEvent;
    if (k.code !== 'Escape' || st.phase !== 'play') return;
    const t = k.target;
    const onPage = !t || t === doc || t === doc.body || t === doc.documentElement || t === doc.defaultView;
    if (!onPage && !(t instanceof Node && root.contains(t))) return;
    if (typing(k)) return;
    skip(); k.preventDefault();
  });

  const api: ReplayApi = {
    get phase() { return st.phase; },
    state: st,
    steps,
    generate,
    skip,
    openSettings,
    seek,
    tick,
    // Start-up (DESIGN.md 11.4 step 8a): ?build=0 (or any ?mode=) skips straight to the model; ?build=play starts at once.
    start(build, address) {
      if (isSpeed(address.speed)) st.speed = address.speed;
      if (address.captions === false) { st.captions = false; ui.captions.checked = false; }
      if (build === 'skip') { st.phase = 'done'; applySettings(); phaseChanged(); return; }
      openSettings();
      if (build === 'play') generate();
    },
  };
  return api;
};

// @vitest-environment happy-dom
// Builder D: installReplay on the shared test context (makeTestContext, fake renderer) with the bank stages (DESIGN.md
// 17.2 replay): start() for each of the three values, phases settings -> play -> done in real time, seek, apply(T)
// idempotent, the hand-over state, the late objects and the ground plane fading in at the end, furniture boxes last,
// the card's inputs, the view you left, Esc, the phase events, the buttons, dispose.
import { BoxGeometry, EdgesGeometry, LineBasicMaterial, LineSegments, Mesh, MeshStandardMaterial, ShaderLib, Vector3, type Material, type Object3D } from 'three';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { FurnitureApi, ModesApi, Presentation, ReplayApi, ReplayData, ReplayPhase, StepKey } from '../../../src/contracts';
import { materialsOf } from '../../../src/replay/apply';
import { DOWN } from '../../../src/replay/camera';
import { installReplay } from '../../../src/replay/index';
import { makeTestContext, type TestContext } from '../../harness/context';
import { card, model, presentation, stages, synthStages } from './helpers';

let live: TestContext[] = [];
afterEach(() => { for (const c of live) c.disposer.dispose(); live = []; document.body.replaceChildren(); });

const WITH_GROUND = (p: Presentation): Presentation => ({ ...p, groundPlane: { size: [80, 50], colour: '#dfe3e0' } });

function setup(o: { model?: string; stages?: ReplayData | null; presentation?: Presentation; before?: (ctx: TestContext) => void } = {}) {
  const m = model(o.model ?? 'bank-v2');
  const ctx = makeTestContext({ model: m, presentation: o.presentation ?? presentation('bank-sampeng-v2'), stages: o.stages === undefined ? stages('bank-v2') : o.stages });
  live.push(ctx);
  o.before?.(ctx);
  const replay = installReplay(ctx);
  ctx.replay = replay;
  return { ctx, replay: replay!, m };
}
const $ = (ctx: TestContext, wt: string) => ctx.ui.root.querySelector(`[data-wt=${wt}]`) as HTMLElement;
const shown = (e: HTMLElement | null) => !!e && e.style.display === 'block';
/** The floor's rise uniform, read the way the GPU gets it (through the material's onBeforeCompile). */
function uRise(mesh: Mesh): number {
  const sh = { uniforms: {} as Record<string, { value: number }>, vertexShader: ShaderLib.physical.vertexShader, fragmentShader: ShaderLib.physical.fragmentShader };
  (mesh.material as Material).onBeforeCompile(sh as never, null as never);
  return sh.uniforms.uRise!.value;
}
/** Everything apply(T) sets, as one string. */
function snapshot(ctx: TestContext): string {
  const out: unknown[] = [];
  ctx.scene.traverse((o: Object3D) => out.push([o.name, o.visible, o.position.toArray(), o.scale.toArray(), materialsOf(o).map(m => [m.opacity, m.transparent])]));
  out.push(ctx.camera.position.toArray(), ctx.controls.target.toArray(), ctx.floors.map(f => (f.rise[0] ? uRise(f.rise[0].mesh) : null)));
  return JSON.stringify(out);
}
const lateLook = (ctx: TestContext) => ctx.floors.flatMap(f => f.late.flatMap(o => { const r: unknown[] = []; o.traverse(n => { const ms = materialsOf(n); if (ms.length) r.push([n.visible, ms.map(m => [m.opacity, m.transparent])]); }); return r; }));
const fakeFurniture = (apply: () => void): FurnitureApi => ({
  pieces: () => [], kinds: () => [], setHeight: () => false, setVisible: () => false, setBlocks: () => false, setKeepDoorways: () => false,
  keepDoorways: () => true, reset: () => {}, csv: () => '', saveCsv: () => '', meshOf: () => null, apply, heights: () => ({}), setHeights: () => {},
});
/** A position without -0 (toEqual tells -0 from 0). */
const at0 = (o: Object3D) => o.position.toArray().map(v => v + 0);

describe('installReplay', () => {
  it('is null without replay data (the hotel)', () => {
    const { replay, ctx } = setup({ model: 'hotel', stages: null, presentation: presentation('hotel-lobby') });
    expect(replay).toBeNull();
    expect(ctx.ui.root.querySelector('[data-wt=replay-card]')).toBeNull();
  });

  it('installs: card and caption in the root, the Build row in slot build, its CSS, the shader patch on every rise item', () => {
    let loopAdds = 0;
    const { ctx, replay } = setup({ before: c => { const add = c.loop.add; c.loop.add = (...a) => { loopAdds++; return add(...a); }; } });
    expect(loopAdds).toBe(0);                               // viewer.ts registers replay.tick (DESIGN.md 11.4 step 8d)
    expect(replay.phase).toBe('off');
    expect($(ctx, 'replay-card').parentElement).toBe(ctx.ui.root);
    expect($(ctx, 'replay-caption').parentElement).toBe(ctx.ui.root);
    expect(ctx.panel.slot('build').querySelector('[data-wt=replay-row]')).not.toBeNull();
    expect(ctx.ui.root.querySelector('style')!.textContent).toContain('[data-wt=replay-card]');
    expect(shown($(ctx, 'replay-card'))).toBe(false);
    for (const f of ctx.floors) for (const r of f.rise) {
      expect(r.mesh.frustumCulled).toBe(false);
      expect(uRise(r.mesh)).toBe(1);
      expect(r.mesh.geometry.getAttribute('aDelay')).toBeDefined();
    }
    // the kit shares one material per kind across floors: each floor's solids now have their own (one uniform set each)
    const mats = ctx.floors.map(f => new Set(f.rise.flatMap(r => [...materialsOf(r.mesh), ...(r.edges ? materialsOf(r.edges) : [])])));
    for (const m of mats[0]!) expect(mats[1]!.has(m)).toBe(false);
    expect(replay.steps.map(s => [s.key, s.title, s.t0, s.t1])).toEqual(card('bank-sampeng-v2').steps.map(s => [s.key, s.title, s.t0, s.t1]));
  });

  it('has the captions the bank page showed at the default settings (__build.steps[].caption(state.settings))', () => {
    const { replay } = setup();
    expect(replay.steps.map(s => s.caption(replay.state.settings))).toEqual(card('bank-sampeng-v2').steps.map(s => s.caption));
    expect(replay.state.settings).toEqual(card('bank-sampeng-v2').settings);
  });
});

describe('start(build, address) (DESIGN.md 11.4)', () => {
  it("'skip': phase done and the model's heights applied, nothing else", () => {
    const { ctx, replay } = setup({ presentation: WITH_GROUND(presentation('bank-sampeng-v2')) });
    const furniture = vi.fn();
    ctx.furniture = fakeFurniture(furniture);
    const heights = vi.spyOn(ctx.heights, 'apply'), floor = vi.spyOn(ctx.visibility, 'applyFloor'), toggles = vi.spyOn(ctx.visibility, 'applyToggles');
    const lock = vi.spyOn(ctx.modes, 'lock'), setMode = vi.spyOn(ctx.modes, 'setMode');
    const cam = [ctx.camera.position.toArray(), ctx.controls.target.toArray(), ctx.camera.quaternion.toArray()], late = lateLook(ctx);
    const phases: ReplayPhase[] = [];
    ctx.bus.on('replayPhase', e => phases.push(e.phase));
    replay.start('skip', { speed: 'slow', captions: false });
    expect(replay.phase).toBe('done');
    expect(heights).toHaveBeenCalledTimes(1);
    expect(heights).toHaveBeenCalledWith({ L1: { level: 0, height: 3.7 }, L2: { level: 3.7, height: 3.7 } });
    expect([floor, toggles, furniture, lock, setMode].map(s => s.mock.calls.length)).toEqual([0, 0, 0, 0, 0]);
    expect([ctx.camera.position.toArray(), ctx.controls.target.toArray(), ctx.camera.quaternion.toArray()]).toEqual(cam);
    expect(ctx.controls.enabled).toBe(true);
    expect(ctx.modes.state.locked).toBe(false);
    expect(lateLook(ctx)).toEqual(late);
    expect(ctx.built.groundPlane!.visible).toBe(true);
    expect(shown($(ctx, 'replay-card'))).toBe(false);
    expect(ctx.ui.root.hasAttribute('data-replay')).toBe(false);
    expect(ctx.floors.every(f => !f.group.children.some(c => c.name === 'build replay'))).toBe(true);
    expect(replay.state.speed).toBe('slow');
    expect(replay.state.captions).toBe(false);
    expect(phases).toEqual(['done']);
    replay.tick(1e6);
    expect(replay.phase).toBe('done');
  });

  it("'settings': the card on the drawing, modes locked, controls off, late objects and the ground plane hidden", () => {
    const { ctx, replay } = setup({ presentation: WITH_GROUND(presentation('bank-sampeng-v2')) });
    const heights = vi.spyOn(ctx.heights, 'apply');
    replay.start('settings', {});
    expect(replay.phase).toBe('settings');
    expect(shown($(ctx, 'replay-card'))).toBe(true);
    expect(shown($(ctx, 'replay-settings'))).toBe(true);
    expect($(ctx, 'replay-play').style.display).toBe('none');
    expect(shown($(ctx, 'replay-caption'))).toBe(false);
    expect([...ctx.ui.root.querySelectorAll<HTMLInputElement>('[data-wt=replay-card] input[type=number]')].map(i => i.value)).toEqual(card('bank-sampeng-v2').inputs.map(i => i.value));
    expect(ctx.modes.state.locked).toBe(true);
    expect(ctx.controls.enabled).toBe(false);
    expect(ctx.renderer.localClippingEnabled).toBe(true);
    expect(ctx.ui.root.hasAttribute('data-replay')).toBe(true);
    expect(heights).toHaveBeenCalledWith({ L1: { level: 0, height: 3.7 }, L2: { level: 3.7, height: 3.7 } });
    expect(ctx.floors.every(f => f.group.visible && f.group.children.some(c => c.name === 'build replay'))).toBe(true);
    expect(lateLook(ctx).every(x => (x as [boolean])[0] === false)).toBe(true);
    expect(ctx.built.groundPlane!.visible).toBe(false);
    expect(ctx.floors.every(f => f.rise.every(r => !r.mesh.visible))).toBe(true);
    // the floors lie side by side on the sheet at the lowest level (Level 2 is drawn 17.08 m east of Level 1)
    expect(at0(ctx.floors[1]!.group)).toEqual([17.08, -3.7, 0]);
    expect(ctx.camera.getWorldDirection(new Vector3()).angleTo(DOWN)).toBeLessThan(1e-6);
    // the settings screen keeps itself up every frame
    replay.tick(5000);
    expect(replay.phase).toBe('settings');
    expect(ctx.floors[1]!.group.position.x).toBe(17.08);
  });

  it("'play': plays at once, with the address speed and captions", () => {
    const a = setup();
    a.replay.start('play', {});
    expect(a.replay.phase).toBe('play');
    expect(shown($(a.ctx, 'replay-play'))).toBe(true);
    expect($(a.ctx, 'replay-settings').style.display).toBe('none');
    expect(shown($(a.ctx, 'replay-caption'))).toBe(true);
    expect($(a.ctx, 'replay-caption').textContent).toBe(`Read the drawing. ${card('bank-sampeng-v2').steps[0]!.caption}`);
    expect(a.replay.state.speed).toBe('normal');
    const b = setup();
    b.replay.start('play', { speed: 'quick', captions: false });
    expect(b.replay.state.speed).toBe('quick');
    expect([...b.ctx.ui.root.querySelectorAll('[data-wt=replay-speed] [data-speed]')].map(x => x.getAttribute('aria-pressed'))).toEqual(['true', 'false', 'false']);
    expect((b.ctx.ui.root.querySelector('[data-wt=replay-captions]') as HTMLInputElement).checked).toBe(false);
    expect(shown($(b.ctx, 'replay-caption'))).toBe(false);
  });

  it('a Walk or Ghost view goes back to Orbit before the card comes up', () => {
    const { ctx, replay } = setup();
    const calls: string[] = [];
    let mode: 'orbit' | 'walk' = 'walk';
    const base = ctx.modes;
    ctx.modes = { ...base, get mode() { return mode; }, setMode: m => { calls.push(`setMode ${m}`); mode = 'orbit'; }, lock: on => { calls.push(`lock ${on}`); } } as ModesApi;
    replay.start('settings', {});
    replay.skip();
    expect(calls).toEqual(['setMode orbit', 'lock true', 'lock false']);
  });
});

describe('phases', () => {
  it('plays settings -> play -> done in real time: dt capped at 0.1 s, never backwards, the end held 700 ms', () => {
    const { ctx, replay } = setup();
    replay.start('play', { speed: 'quick' });
    replay.state.last = 1000;
    replay.tick(1050);
    expect(replay.state.T).toBeCloseTo(0.05 / 9, 12);
    replay.tick(2050);                                     // a 1 s hitch counts as 0.1 s
    expect(replay.state.T).toBeCloseTo(0.15 / 9, 12);
    replay.tick(2000);                                     // a frame time before the last one: no step back
    expect(replay.state.T).toBeCloseTo(0.15 / 9, 12);
    let t = 2000, reached = 0;
    while (replay.phase === 'play' && t < 60000) { t += 100; replay.tick(t); if (!reached && replay.state.T >= 1) reached = t; }
    expect(replay.phase).toBe('done');
    expect(reached).toBeGreaterThan(0);
    expect(t - reached).toBeGreaterThanOrEqual(700);
    expect(t - reached).toBeLessThan(800);
    expect(ctx.modes.state.locked).toBe(false);
  });

  it('apply(T) is idempotent: the same T gives the same scene, camera and step list', () => {
    const { ctx, replay } = setup({ presentation: WITH_GROUND(presentation('bank-sampeng-v2')) });
    replay.start('settings', {});
    for (const T of [0.05, 0.3, 0.5, 0.7, 0.93]) {
      replay.seek(T);
      const a = snapshot(ctx), steps = ctx.ui.root.querySelector('[data-wt=replay-steps]')!.innerHTML;
      replay.seek(T);
      replay.tick(123456);                                  // paused: it holds T
      expect(snapshot(ctx)).toBe(a);
      expect(ctx.ui.root.querySelector('[data-wt=replay-steps]')!.innerHTML).toBe(steps);
      expect(replay.state.T).toBe(T);
      expect(replay.state.paused).toBe(true);
    }
  });

  it('seek: the step list, bar and caption follow T; seek(1) ticks all seven', () => {
    const { ctx, replay } = setup();
    replay.start('settings', {});
    const facts = card('bank-sampeng-v2');
    const state = () => [...ctx.ui.root.querySelectorAll('[data-wt=replay-steps] li')].map(li => li.getAttribute('data-state'));
    replay.seek(0.45);
    expect(replay.phase).toBe('play');
    expect(state()).toEqual(['done', 'done', 'done', 'now', 'todo', 'todo', 'todo']);
    expect(replay.state.step).toBe('pair');
    expect($(ctx, 'replay-caption').textContent).toBe(`Find the wall faces. ${facts.steps[3]!.caption}`);
    expect(($(ctx, 'replay-bar').firstElementChild as HTMLElement).style.width).toBe('45.0%');
    replay.seek(1);
    expect(state()).toEqual(Array(7).fill('done'));
    expect(ctx.ui.root.querySelectorAll('[data-wt=replay-steps] li[data-state=done]').length).toBe(7);
    expect(($(ctx, 'replay-bar').firstElementChild as HTMLElement).style.width).toBe('100.0%');
    expect($(ctx, 'replay-caption').textContent).toBe(`Floors, stairs, room names. ${facts.steps[6]!.caption}`);
    replay.seek(-3);
    expect(replay.state.T).toBe(0);
    expect(state()[0]).toBe('now');
  });

  it('the walls rise floor by floor during the raise step; pieces and runs come and go before them', () => {
    const { ctx, replay } = setup();
    replay.start('settings', {});
    const [lo, hi] = [ctx.floors[0]!, ctx.floors[1]!];
    const times = Object.fromEntries(replay.steps.map(s => [s.key, s])) as unknown as Record<StepKey, { t0: number; t1: number }>;
    const at = (k: StepKey, f: number) => times[k].t0 + (times[k].t1 - times[k].t0) * f;
    replay.seek(at('merge', 0.99));
    expect(lo.rise.some(r => r.mesh.visible)).toBe(false);
    replay.seek(at('raise', 0.3));
    expect(uRise(lo.rise[0]!.mesh)).toBeGreaterThan(0);
    expect(uRise(hi.rise[0]!.mesh)).toBe(0);
    expect(lo.rise.every(r => r.mesh.visible)).toBe(true);
    expect(hi.rise.every(r => !r.mesh.visible)).toBe(true);
    replay.seek(at('raise', 0.7));
    expect(uRise(lo.rise[0]!.mesh)).toBe(1);
    expect(uRise(hi.rise[0]!.mesh)).toBeGreaterThan(0);
    expect(uRise(hi.rise[0]!.mesh)).toBeLessThan(1);
    replay.seek(at('raise', 1));
    expect(uRise(hi.rise[0]!.mesh)).toBeCloseTo(1, 9);
    // the floors are lined up at their levels from the end of the align step on
    replay.seek(at('pair', 0.5));
    expect(at0(hi.group)).toEqual([0, 0, 0]);
  });
});

describe('the hand-over (finish)', () => {
  it('leaves the normal viewer: groups at home, solids full, late opaque, ground plane opaque, restore hooks, unlocked, the view it started on', () => {
    const { ctx, replay } = setup({ presentation: WITH_GROUND(presentation('bank-sampeng-v2')) });
    const edge0 = ctx.floors.map(f => f.rise.map(r => (r.edges ? materialsOf(r.edges)[0]!.opacity : null)));
    const late0 = lateLook(ctx);
    const start = [ctx.camera.position.toArray(), ctx.controls.target.toArray()];
    const furniture = vi.fn();
    ctx.furniture = fakeFurniture(furniture);
    const floor = vi.spyOn(ctx.visibility, 'applyFloor'), toggles = vi.spyOn(ctx.visibility, 'applyToggles');
    replay.start('settings', {});
    const input = ctx.ui.root.querySelector<HTMLInputElement>('[data-wt=replay-card] input[data-floor="L2"][data-prop=level]')!;
    input.value = '5.00'; input.dispatchEvent(new Event('change'));
    replay.generate();
    replay.seek(0.7);
    replay.skip();
    expect(replay.phase).toBe('done');
    expect(ctx.floors.map(f => at0(f.group))).toEqual([[0, 0, 0], [0, 5 - 3.7, 0]]);
    expect(ctx.floors.every(f => f.group.visible)).toBe(true);
    for (const f of ctx.floors) for (const r of f.rise) { expect(r.mesh.visible).toBe(true); expect(uRise(r.mesh)).toBe(1); expect(r.edges!.visible).toBe(true); }
    expect(ctx.floors.map(f => f.rise.map(r => (r.edges ? materialsOf(r.edges)[0]!.opacity : null)))).toEqual(edge0);
    expect(lateLook(ctx)).toEqual(late0);
    const gp = ctx.built.groundPlane!, gm = gp.material as MeshStandardMaterial;
    expect([gp.visible, gm.opacity, gm.transparent]).toEqual([true, 1, false]);
    expect([floor, toggles, furniture].map(s => s.mock.calls.length)).toEqual([1, 1, 1]);
    expect(ctx.modes.state.locked).toBe(false);
    expect(ctx.controls.enabled).toBe(true);
    expect(ctx.renderer.localClippingEnabled).toBe(false);
    expect(shown($(ctx, 'replay-card'))).toBe(false);
    expect(shown($(ctx, 'replay-caption'))).toBe(false);
    expect(ctx.ui.root.hasAttribute('data-replay')).toBe(false);
    expect(ctx.floors.every(f => !f.group.children.some(c => c.name === 'build replay'))).toBe(true);
    expect(ctx.scene.children.some(c => c.name === 'build replay scan')).toBe(false);
    expect([ctx.camera.position.toArray(), ctx.controls.target.toArray()]).toEqual(start);
    // Walk would now use the level set before Generate
    expect(ctx.floors[1]!.level).toBe(5);
    replay.skip();                                          // nothing to skip any more
    expect(floor).toHaveBeenCalledTimes(1);
  });

  it('fades the ground plane with the late objects: hidden in settings and play, fading in during finish, opaque after', () => {
    const { ctx, replay } = setup({ presentation: WITH_GROUND(presentation('bank-sampeng-v2')) });
    const gp = ctx.built.groundPlane!, gm = gp.material as MeshStandardMaterial;
    const plate = ctx.floors[0]!.walkables[0]!, pm = plate.material as MeshStandardMaterial;
    replay.start('settings', {});
    expect([gp.visible, plate.visible]).toEqual([false, false]);
    const fin = replay.steps.find(s => s.key === 'finish')!;
    for (const T of [0.1, 0.5, 0.8, fin.t0]) { replay.seek(T); expect([gp.visible, plate.visible]).toEqual([false, false]); }
    replay.seek((fin.t0 + fin.t1) / 2);
    expect([gp.visible, plate.visible]).toEqual([true, true]);
    expect(gm.opacity).toBeGreaterThan(0.2); expect(gm.opacity).toBeLessThan(0.8); expect(gm.transparent).toBe(true);
    expect(pm.opacity).toBeCloseTo(gm.opacity, 12); expect(pm.transparent).toBe(true);
    replay.seek(1);
    expect([gm.opacity, gm.transparent]).toEqual([1, false]);
    replay.skip();
    expect([gp.visible, gm.opacity, gm.transparent, plate.visible, pm.opacity, pm.transparent]).toEqual([true, 1, false, true, 1, false]);
  });

  it('brings the furniture boxes in last (they are late objects) and the restore hook puts the ticks back', () => {
    let box: Mesh | null = null;
    const { ctx, replay } = setup({
      before: c => {                                        // what installFurniture does before the replay is installed
        const face = new MeshStandardMaterial({ color: '#c0392b', polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
        box = new Mesh(new BoxGeometry(1, 1, 1), face);
        box.name = 'furn:atm:L1-ATM-01';
        box.add(new LineSegments(new EdgesGeometry(box.geometry), new LineBasicMaterial({ color: '#4d1610' })));
        c.floors[0]!.group.add(box); c.floors[0]!.late.push(box);
      },
    });
    const b = box as unknown as Mesh, edge = b.children[0] as LineSegments;
    ctx.furniture = fakeFurniture(() => { b.visible = false; });    // e.g. the kind was hidden in the legend
    replay.start('play', {});
    const raise = replay.steps.find(s => s.key === 'raise')!;
    replay.seek((raise.t0 + raise.t1) / 2);
    expect([b.visible, edge.visible]).toEqual([false, false]);
    replay.seek(1);
    expect([b.visible, edge.visible]).toEqual([true, true]);
    expect([(b.material as Material).opacity, (edge.material as Material).opacity]).toEqual([1, 1]);
    replay.skip();
    expect((b.material as Material).transparent).toBe(false);
    expect((edge.material as Material).transparent).toBe(false);
    expect(b.visible).toBe(false);                          // put back by the furniture's apply()
  });
});

describe('the card', () => {
  it('reads the boxes (clamped, an empty box keeps its value), applies the heights, and the captions quote them', () => {
    const { ctx, replay } = setup();
    const heights = vi.spyOn(ctx.heights, 'apply');
    replay.start('settings', {});
    const box = (k: string, p: string) => ctx.ui.root.querySelector<HTMLInputElement>(`[data-wt=replay-card] input[data-floor="${k}"][data-prop=${p}]`)!;
    const set = (k: string, p: string, v: string) => { const i = box(k, p); i.value = v; i.dispatchEvent(new Event('change')); return i.value; };
    expect(set('L2', 'level', '5.00')).toBe('5.00');
    expect(heights).toHaveBeenLastCalledWith({ L1: { level: 0, height: 3.7 }, L2: { level: 5, height: 3.7 } });
    expect(set('L2', 'level', '')).toBe('5.00');
    expect(replay.state.settings.L2!.level).toBe(5);
    expect(set('L2', 'level', '250')).toBe('200.00');
    expect(set('L2', 'level', '5')).toBe('5.00');
    expect(set('L1', 'height', '15')).toBe('12.00');
    expect(set('L1', 'height', '0.2')).toBe('1.00');
    expect(set('L1', 'height', '3')).toBe('3.00');
    expect(heights).toHaveBeenLastCalledWith({ L1: { level: 0, height: 3 }, L2: { level: 5, height: 3.7 } });
    const caps = replay.steps.map(s => s.caption(replay.state.settings));
    expect(caps.some(c => c.includes('rises to 5.00 m'))).toBe(true);
    expect(caps.some(c => c.includes('Walls rise to 3.00 m on Level 1 and 3.70 m on Level 2'))).toBe(true);
    replay.skip();
    replay.openSettings();
    expect([box('L1', 'height').value, box('L2', 'level').value]).toEqual(['3.00', '5.00']);
  });

  it('ends on the view you left when you replay from the viewer, on the start-up view otherwise', () => {
    const { ctx, replay } = setup();
    replay.start('skip', {});
    ctx.camera.position.set(10, 20, 30); ctx.controls.target.set(1, 2, 3); ctx.camera.lookAt(ctx.controls.target);
    $(ctx, 'replay-again').click();
    expect(replay.phase).toBe('play');
    replay.seek(0.4);
    expect(ctx.camera.position.toArray()).not.toEqual([10, 20, 30]);
    replay.skip();
    ctx.camera.position.toArray().forEach((v, i) => expect(v).toBeCloseTo([10, 20, 30][i]!, 9));
    ctx.controls.target.toArray().forEach((v, i) => expect(v).toBeCloseTo([1, 2, 3][i]!, 9));
  });

  it('the buttons: Generate, Skip on the card, Skip while playing, Replay the build, Build settings, speed, captions', () => {
    const { ctx, replay } = setup();
    replay.start('settings', {});
    ($(ctx, 'replay-speed').querySelector('[data-speed=slow]') as HTMLElement).click();
    expect(replay.state.speed).toBe('slow');
    expect($(ctx, 'replay-speed').querySelector('[aria-pressed=true]')!.getAttribute('data-speed')).toBe('slow');
    const cap = ctx.ui.root.querySelector('[data-wt=replay-captions]') as HTMLInputElement;
    cap.checked = false; cap.dispatchEvent(new Event('change'));
    expect(replay.state.captions).toBe(false);
    $(ctx, 'replay-go').click();
    expect(replay.phase).toBe('play');
    expect(shown($(ctx, 'replay-caption'))).toBe(false);
    $(ctx, 'replay-skip').click();
    expect(replay.phase).toBe('done');
    $(ctx, 'replay-open').click();
    expect(replay.phase).toBe('settings');
    expect($(ctx, 'replay-speed').querySelector('[aria-pressed=true]')!.getAttribute('data-speed')).toBe('slow');
    $(ctx, 'replay-skip-settings').click();
    expect(replay.phase).toBe('done');
    $(ctx, 'replay-again').click();
    expect(replay.phase).toBe('play');
    replay.skip();
  });
});

describe('keys, events, dispose', () => {
  const esc = (target: EventTarget) => target.dispatchEvent(new KeyboardEvent('keydown', { code: 'Escape', key: 'Escape', bubbles: true, cancelable: true }));

  it('Esc skips while it plays: from the page or inside the root, not from the host page\'s own controls or while typing', () => {
    const { ctx, replay } = setup();
    replay.start('settings', {});
    esc(document.body);
    expect(replay.phase).toBe('settings');                  // only while it plays
    replay.generate();
    const outside = document.createElement('button');
    document.body.append(outside);
    esc(outside);
    expect(replay.phase).toBe('play');
    const typingBox = document.createElement('input');
    typingBox.type = 'text';
    ctx.ui.root.append(typingBox);
    esc(typingBox);
    expect(replay.phase).toBe('play');
    const ev = new KeyboardEvent('keydown', { code: 'Escape', key: 'Escape', bubbles: true, cancelable: true });
    ctx.canvas.dispatchEvent(ev);
    expect(replay.phase).toBe('done');
    expect(ev.defaultPrevented).toBe(true);
    replay.openSettings(); replay.generate();
    esc(document.body);
    expect(replay.phase).toBe('done');
  });

  it('emits bus replayPhase and the public replayphase once per change', () => {
    const { ctx, replay } = setup();
    const bus: ReplayPhase[] = [], pub: ReplayPhase[] = [];
    ctx.bus.on('replayPhase', e => bus.push(e.phase));
    ctx.events.on('replayphase', e => pub.push(e.phase));
    replay.start('settings', {});
    replay.openSettings();
    replay.generate();
    replay.seek(0.5);
    replay.skip();
    replay.skip();
    $(ctx, 'replay-again').click();
    replay.skip();
    expect(bus).toEqual(['settings', 'play', 'done', 'settings', 'play', 'done']);
    expect(pub).toEqual(bus);
  });

  it('dispose takes the card, the caption, the Build row, the replay objects, the copies and the key listener away', () => {
    const { ctx, replay } = setup();
    replay.start('play', {});
    replay.seek(0.5);
    const mats = new Set(ctx.floors[1]!.rise.map(r => r.mesh.material as Material)), freed = new Set<Material>();
    for (const m of mats) m.addEventListener('dispose', () => freed.add(m));
    const groups = ctx.floors.map(f => f.group.children.find(c => c.name === 'build replay')!);
    ctx.disposer.dispose();
    live = live.filter(c => c !== ctx);
    expect(document.querySelector('[data-wt=replay-card], [data-wt=replay-caption], [data-wt=replay-row]')).toBeNull();
    expect(groups.every(g => g.parent === null)).toBe(true);
    expect(ctx.scene.children.some(c => c.name === 'build replay scan')).toBe(false);
    expect(freed.size).toBe(mats.size);
    esc(document.body);
    expect(replay.phase).toBe('play');                      // no listener left
  });
});

describe('other shapes of replay data', () => {
  it('one floor (the suite): it rises at once (no stagger), with {suitelevel} placeholders filled', () => {
    const m = model('suite');
    const { ctx, replay } = setup({ model: 'suite', stages: synthStages(m), presentation: presentation('presidential-suite') });
    replay.start('play', {});
    expect(replay.steps.find(s => s.key === 'align')!.caption(replay.state.settings)).toBe('Floors at +0.00 m and 0.00 m.');
    expect(replay.steps.find(s => s.key === 'raise')!.caption(replay.state.settings)).toBe('Walls rise to 3.00 m; {nokeylevel} stays.');
    const raise = replay.steps.find(s => s.key === 'raise')!;
    replay.seek(raise.t0 + (raise.t1 - raise.t0) * 0.7);
    expect(uRise(ctx.floors[0]!.rise[0]!.mesh)).toBe(1);
    replay.skip();
    expect(replay.phase).toBe('done');
  });

  it('a floor with no lines in the replay data is framed by its parts (the camera stays finite)', () => {
    const m = model('bank-v2'), data = stages('bank-v2');
    const empty: ReplayData = { ...data, floors: { ...data.floors, L2: { sheet: [0, 0], lines: {}, pieces: {}, rings: {} } } };
    const { ctx, replay } = setup({ stages: empty });
    replay.start('play', {});
    for (const T of [0, 0.3, 0.6, 0.9]) {
      replay.seek(T);
      expect(ctx.camera.position.toArray().every(Number.isFinite)).toBe(true);
      expect(ctx.controls.target.toArray().every(Number.isFinite)).toBe(true);
    }
    expect(m.floors.length).toBe(2);
  });

  it('a floor missing from the replay data and step titles / colours from the file', () => {
    const data = stages('bank-v2');
    const partial: ReplayData = {
      ...data, floors: { L1: data.floors.L1! }, stepTitles: { read: 'Read it', finish: 'Done' }, layersTitle: 'Layers found',
      colors: { wall: '#7a6650', glass: '#2f86a8', window: '#4a9cc0', stair: '#2e8b47', door: '#c0702a' },
    };
    const { ctx, replay } = setup({ stages: partial });
    replay.start('settings', {});
    expect(replay.steps.map(s => s.title)).toEqual(['Read it', 'Sort the layers', 'Line up the levels', 'Find the wall faces', 'Merge, cut the openings', 'Raise the walls', 'Done']);
    expect($(ctx, 'replay-layers-title').textContent).toBe('Layers found');
    replay.seek(0.5);
    expect(ctx.floors[1]!.group.children.find(c => c.name === 'build replay')!.children.length).toBe(0);
    expect(ctx.camera.position.toArray().every(Number.isFinite)).toBe(true);
    replay.skip();
  });
});

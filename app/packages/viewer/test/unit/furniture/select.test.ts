// @vitest-environment happy-dom
// Builder C, step BX (docs/boxes/DESIGN.md 2.2 - 2.4, 8.2): selecting a furniture box and deleting it on the shared test
// context: the Orbit click, the Walk / Ghost aim at the crosshair, the marker, the card, the keys and their guards, the
// hover label's extra line, and when the selection clears.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Color, Vector3, type Group, type LineSegments, type Material, type Mesh } from 'three';
import type { BuiltModel, FurnitureApi, ResolvedOptions } from '../../../src/contracts';
import { installFurniture } from '../../../src/furniture/index';
import { AIM_HOLD_MS, AIM_REACH, CLICK_SLOP, HOLD_MOVE, MARKER_COLOUR, MARKER_GROW } from '../../../src/furniture/select';
import { createPhotos } from '../../../src/modes/photo';
import { fadeLate, recordLate, restoreLate, type LateLook } from '../../../src/replay/apply';
import type { ReplayFloorRt } from '../../../src/replay/objects';
import { makeTestContext, type TestContext } from '../../harness/context';
import { FURNISHED, loadModel } from './util';

let live: TestContext[] = [];
function mount(model: BuiltModel, options: Partial<ResolvedOptions> = { editBoxes: true }) {
  const ctx = makeTestContext({ model, stamp: 'abcdef123456', options });
  const F = installFurniture(ctx)!;
  ctx.furniture = F;
  live.push(ctx);
  // the view from above (as the hover checks): the default view looks over the mini model's east wall
  const rect = { left: 0, top: 0, right: 1400, bottom: 880, width: 1400, height: 880, x: 0, y: 0, toJSON: () => ({}) } as DOMRect;
  vi.spyOn(ctx.canvas, 'getBoundingClientRect').mockReturnValue(rect);
  vi.spyOn(ctx.ui.root, 'getBoundingClientRect').mockReturnValue(rect);
  ctx.camera.position.set(0, 40, 8);
  ctx.camera.lookAt(0, 0, 0);
  ctx.scene.updateMatrixWorld(true);
  ctx.camera.updateMatrixWorld();
  return { ctx, F };
}
beforeEach(() => { localStorage.clear(); });
afterEach(() => { for (const c of live) c.disposer.dispose(); live = []; localStorage.clear(); vi.restoreAllMocks(); });

const mini = () => loadModel('mini');
const q = <T extends Element = HTMLElement>(ctx: TestContext, sel: string) => ctx.ui.root.querySelector<T & Element>(sel) as unknown as T;
const card = (ctx: TestContext) => q(ctx, '[data-wt=box-card]');
const toast = (ctx: TestContext) => q(ctx, '[data-wt=box-toast]');
const open = (e: HTMLElement | null) => !!e && e.style.display === 'block';
const text = (ctx: TestContext, wt: string) => card(ctx).querySelector(`[data-wt=${wt}]`)?.textContent ?? null;
const marker = (ctx: TestContext) => ctx.scene.getObjectByName('furniture-selection') as Group;
const wait = (ms: number) => new Promise(r => setTimeout(r, ms));

/** The id of the box the marker stands on (its matrix is the box's world matrix, grown), or null when it is not shown. */
function marked(ctx: TestContext, F: FurnitureApi): string | null {
  const m = marker(ctx);
  if (!m.visible) return null;
  const at = new Vector3().setFromMatrixPosition(m.matrix);
  for (const p of F.pieces()) {
    const w = F.meshOf(p.id)!.getWorldPosition(new Vector3());
    if (Math.abs(w.x - at.x) < 1e-6 && Math.abs(w.z - at.z) < 1e-6 && Math.abs(w.y - at.y) < 0.05) return p.id;
  }
  return 'somewhere else';
}
/** Screen (client) coordinates of a three.js point. */
const screen = (ctx: TestContext, x: number, y: number, z: number) => {
  const v = new Vector3(x, y, z).project(ctx.camera);
  return [(v.x + 1) / 2 * 1400, (1 - v.y) / 2 * 880] as const;
};
/** A spot on the top of a box, `along` m from its middle along its long axis. */
const top = (ctx: TestContext, F: FurnitureApi, id: string, along = 0) => {
  const p = F.pieces().find(x => x.id === id)!, r = p.rot * Math.PI / 180;
  return screen(ctx, p.x + along * Math.cos(r), ctx.floorByKey.get(p.floor)!.modelLevel + p.z1, -(p.y + along * Math.sin(r)));
};
interface ClickOpt { detail?: number; pointerType?: string; dragBy?: number; button?: number; moveBackAfter?: number }
function click(ctx: TestContext, at: readonly [number, number], o: ClickOpt = {}): void {
  const [x, y] = at, c = ctx.canvas, type = o.pointerType ?? 'mouse';
  c.dispatchEvent(new PointerEvent('pointerdown', { clientX: x, clientY: y, button: o.button ?? 0, buttons: 1, pointerType: type, bubbles: true }));
  const ux = x + (o.dragBy ?? 0);
  if (o.moveBackAfter) {                                              // a drag out and back to where it started
    c.dispatchEvent(new PointerEvent('pointermove', { clientX: x + o.moveBackAfter, clientY: y, buttons: 1, pointerType: type, bubbles: true }));
  }
  c.dispatchEvent(new PointerEvent('pointerup', { clientX: ux, clientY: y, button: o.button ?? 0, pointerType: type, bubbles: true }));
  c.dispatchEvent(new MouseEvent('click', { clientX: ux, clientY: y, button: o.button ?? 0, detail: o.detail ?? 1, bubbles: true }));
}
// a key with nothing focused goes to the body (as in a browser)
const key = (code: string, init: KeyboardEventInit = {}, target: EventTarget = document.body) =>
  target.dispatchEvent(new KeyboardEvent('keydown', { code, bubbles: true, cancelable: true, ...init }));
const press = (target: EventTarget) => target.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
/** Walk or Ghost, as the modes would say it. */
function setMode(ctx: TestContext, mode: 'orbit' | 'walk' | 'ghost'): void {
  ctx.modes.state.mode = mode;
  ctx.bus.emit('mode', { mode, floor: 'L1' });
}
/** The eye `dist` m straight above the middle of a box's top, looking down at it (the crosshair is the middle of the view). */
function lookDownAt(ctx: TestContext, F: FurnitureApi, id: string, dist: number, along = 0): void {
  const p = F.pieces().find(x => x.id === id)!, r = p.rot * Math.PI / 180;
  const x = p.x + along * Math.cos(r), z = -(p.y + along * Math.sin(r)), y = ctx.floorByKey.get(p.floor)!.modelLevel + p.z1;
  ctx.camera.position.set(x, y + dist, z + 1e-4);
  ctx.camera.lookAt(x, y, z);
  ctx.camera.updateMatrixWorld();
}
const T2 = 'L2-table-001', EDGE = -0.55;                               // the table's edge: the computer stands in its middle

describe('the Orbit click', () => {
  it('a click on a box selects it: the marker on the box, the card at the top right; another box moves it; empty space clears it', () => {
    const { ctx, F } = mount(mini());
    expect(marker(ctx).parent).toBe(ctx.scene);
    expect(marker(ctx).visible).toBe(false);
    expect(open(card(ctx))).toBe(false);
    click(ctx, top(ctx, F, T2, EDGE));
    expect(marked(ctx, F)).toBe(T2);
    expect(open(card(ctx))).toBe(true);
    expect(card(ctx).parentElement).toBe(ctx.ui.root);
    expect(text(ctx, 'box-kind')).toBe('Table / desk');
    click(ctx, top(ctx, F, 'L2-computer-001'));
    expect(marked(ctx, F)).toBe('L2-computer-001');
    expect(text(ctx, 'box-kind')).toBe('Computer / monitor');
    click(ctx, [5, 5]);                                               // the sky
    expect(marked(ctx, F)).toBeNull();
    expect(open(card(ctx))).toBe(false);
    // a box under level 2's floor plate is hidden by it: a click there selects nothing
    click(ctx, top(ctx, F, 'L1-seat-002'));
    expect(marked(ctx, F)).toBeNull();
  });

  it('the marker: the box 2 cm larger on each side, magenta, the outline drawn over everything; it follows a typed height', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, T2, EDGE));
    const m = marker(ctx), mesh = F.meshOf(T2)!;
    const scale = new Vector3().setFromMatrixScale(m.matrix), pos = new Vector3().setFromMatrixPosition(m.matrix);
    expect([scale.x, scale.y, scale.z].map(v => +v.toFixed(6))).toEqual([mesh.scale.x, mesh.scale.y, mesh.scale.z].map(v => +(v + 2 * MARKER_GROW).toFixed(6)));
    expect(pos.y).toBeCloseTo(mesh.getWorldPosition(new Vector3()).y - MARKER_GROW, 6);
    const [fill, outline] = m.children as [Mesh, LineSegments];
    const fm = fill.material as Material & { color: Color }, lm = outline.material as Material & { color: Color };
    expect([fm.transparent, fm.opacity, fm.depthWrite]).toEqual([true, 0.35, false]);
    expect([lm.depthTest, lm.opacity, outline.renderOrder]).toEqual([false, 1, 10]);
    expect(fm.color.equals(new Color(MARKER_COLOUR)) && lm.color.equals(new Color(MARKER_COLOUR))).toBe(true);
    expect(MARKER_COLOUR).toBe('#ff2bd6');
    F.setHeight('table', 1200);
    expect(new Vector3().setFromMatrixScale(m.matrix).y).toBeCloseTo(1.2 + 2 * MARKER_GROW, 6);
    expect(text(ctx, 'box-size')).toBe('1.40 × 1.00 × 1.20 m · Level 2');
    // drawn in a frame: it copies the box's matrix then too (the Build settings may have moved the floor)
    ctx.floorByKey.get('L2')!.group.position.y += 1;
    ctx.scene.updateMatrixWorld(true);
    fill.onBeforeRender(null as never, null as never, null as never, null as never, null as never, null as never);
    expect(new Vector3().setFromMatrixPosition(fill.matrixWorld).y).toBeCloseTo(mesh.getWorldPosition(new Vector3()).y - MARKER_GROW, 6);
  });

  it('the marker colour is no kind\'s colour, in any fixture model', () => {
    const want = new Color(MARKER_COLOUR).getHexString();
    for (const name of ['mini', ...FURNISHED.map(f => f.model)]) {
      for (const k of loadModel(name).furnitureKinds ?? []) expect(new Color(k.colour).getHexString(), `${name} ${k.key}`).not.toBe(want);
    }
  });

  it(`a drag of ${CLICK_SLOP} px or more does not select; less does; a drag out and back does not`, () => {
    const { ctx, F } = mount(mini());
    const at = top(ctx, F, T2, EDGE);
    click(ctx, at, { dragBy: CLICK_SLOP });
    expect(marked(ctx, F)).toBeNull();
    click(ctx, at, { dragBy: CLICK_SLOP - 1 });
    expect(marked(ctx, F)).toBe(T2);
    // a drag does not clear a selection either (orbiting around the selected box)
    click(ctx, [5, 5], { dragBy: 40 });
    expect(marked(ctx, F)).toBe(T2);
    key('Escape');
    // out and back to where it started (last here: the kit's OrbitControls turn the view on the move)
    click(ctx, at, { moveBackAfter: 30 });
    expect(marked(ctx, F)).toBeNull();
    expect(open(card(ctx))).toBe(false);
  });

  it('the second click of a double-click (detail 2) clears the selection: the double-click to walk follows', () => {
    const { ctx, F } = mount(mini());
    const at = top(ctx, F, T2, EDGE);
    click(ctx, at);
    expect(marked(ctx, F)).toBe(T2);
    click(ctx, at, { detail: 2 });
    expect(marked(ctx, F)).toBeNull();
    expect(open(card(ctx))).toBe(false);
  });

  it('not for touch, not another button, not in Walk or Ghost, not while the replay runs, not with the Camera panel open', () => {
    const { ctx, F } = mount(mini());
    const at = top(ctx, F, T2, EDGE);
    click(ctx, at, { pointerType: 'touch' });
    expect(marked(ctx, F)).toBeNull();
    click(ctx, at, { button: 2 });
    expect(marked(ctx, F)).toBeNull();
    ctx.modes.state.locked = true;
    click(ctx, at);
    expect(marked(ctx, F)).toBeNull();
    ctx.modes.state.locked = false;
    ctx.modes.state.camOpen = true;
    click(ctx, at);
    expect(marked(ctx, F)).toBeNull();
    ctx.modes.state.camOpen = false;
    ctx.modes.state.mode = 'ghost';
    click(ctx, at);
    expect(open(card(ctx))).toBe(false);
    ctx.modes.state.mode = 'orbit';
    click(ctx, at);
    expect(marked(ctx, F)).toBe(T2);
  });

  it('without editBoxes a click does nothing: no marker, no card, no listener', () => {
    const { ctx, F } = mount(mini(), {});
    click(ctx, top(ctx, F, T2, EDGE));
    expect(ctx.scene.getObjectByName('furniture-selection')).toBeUndefined();
    expect(card(ctx)).toBeNull();
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
  });
});

describe('the card', () => {
  /** The card of any piece: a deleted box that is restored becomes the selection. */
  const cardOf = (F: FurnitureApi, id: string) => { F.removePiece(id); F.restorePiece(id); };

  it('kind, family, size and floor, the id, Delete box (Del) and ×; "from" for a raised box; no "side by side" line', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, 'L2-computer-001'));
    expect([...card(ctx).children].map(c => c.getAttribute('data-wt'))).toEqual(['box-kind', 'box-family', 'box-size', 'box-id', 'box-buttons', 'box-close']);
    expect(text(ctx, 'box-kind')).toBe('Computer / monitor');
    expect(text(ctx, 'box-family')).toBe('Enscape AssetDefinition - Computer 003');
    expect(text(ctx, 'box-size')).toBe('0.74 × 0.43 × 0.45 m · Level 2, from 0.75 m');
    expect(text(ctx, 'box-id')).toBe('L2-computer-001');
    expect(text(ctx, 'box-delete')).toBe('Delete box (Del)');
    expect(text(ctx, 'box-close')).toBe('×');
    expect(card(ctx).textContent).not.toContain('side by side');
    expect(text(ctx, 'box-undo')).toBeNull();
  });

  it('the builder note of a cabinet with merged fronts and of a piece drawn loose; none on a piece without one', () => {
    const a = mount(mini());
    cardOf(a.F, 'L2-cabinet-001');
    expect(text(a.ctx, 'box-note')).toBe('merged 4 cupboard-door fronts');
    expect(a.ctx.model.furniture!.find(p => p.id === 'L2-cabinet-001')!.n).toBe(4);
    expect(card(a.ctx).textContent).not.toContain('side by side');
    a.ctx.visibility.setFloorMode('L1');
    cardOf(a.F, 'L1-seat-001');
    expect(text(a.ctx, 'box-kind')).toBe('Chair / stool');
    expect(text(a.ctx, 'box-note')).toBeNull();
    const b = mount(loadModel('suite'));
    cardOf(b.F, 'suite-other-001');
    expect(text(b.ctx, 'box-id')).toBe('suite-other-001');
    expect(text(b.ctx, 'box-note')).toBe('drawn loose, not as a block');
  });

  it('what stands on it is said before the delete: "2 pieces stand on it (...): they are deleted with it."', () => {
    const { ctx, F } = mount(mini());
    ctx.visibility.setFloorMode('L1');                                // in Both floors Level 2's plate hides it: no card of it
    cardOf(F, 'L1-table-001');
    expect(text(ctx, 'box-cascade')).toBe('2 pieces stand on it (Computer / monitor, Printer / copier): they are deleted with it.');
    ctx.visibility.setFloorMode('all');
    click(ctx, top(ctx, F, T2, EDGE));
    expect(text(ctx, 'box-cascade')).toBe('1 piece stands on it (Computer / monitor): it is deleted with it.');
    click(ctx, top(ctx, F, 'L2-computer-001'));
    expect(text(ctx, 'box-cascade')).toBeNull();
    // a piece on it that is already deleted is not counted
    F.removePiece('L1-printer-001');
    cardOf(F, 'L1-seat-001');
    F.restorePiece('L1-printer-001');
    F.removePiece('L1-computer-001');
    ctx.visibility.setFloorMode('L1');
    click(ctx, top(ctx, F, 'L1-table-001', 0.8));
    expect(text(ctx, 'box-cascade')).toBe('1 piece stands on it (Printer / copier): it is deleted with it.');
  });

  it('a hostile kind label, family, floor name and note stay text', () => {
    const m = mini();
    m.furnitureKinds!.find(k => k.key === 'table')!.label = '<img src=x onerror="window.__pwned = 1">';
    const t = m.furniture!.find(p => p.id === T2)!;
    t.family = '<b onclick="window.__pwned = 2">family</b>';
    t.note = '<script>window.__pwned = 4</script>';
    m.floors[1]!.name = '<i>Level 2</i>';
    const { ctx, F } = mount(m);
    click(ctx, top(ctx, F, T2, EDGE));
    expect(text(ctx, 'box-kind')).toBe('<img src=x onerror="window.__pwned = 1">');
    expect(text(ctx, 'box-family')).toBe('<b onclick="window.__pwned = 2">family</b>');
    expect(text(ctx, 'box-size')).toBe('1.40 × 1.00 × 0.75 m · <i>Level 2</i>');
    expect(text(ctx, 'box-note')).toBe('<script>window.__pwned = 4</script>');
    expect(card(ctx).querySelectorAll('img, b, i, script').length).toBe(0);
    card(ctx).querySelector<HTMLButtonElement>('[data-wt=box-delete]')!.click();
    expect(text(ctx, 'box-kind')).toBe('Deleted: <img src=x onerror="window.__pwned = 1"> (+1 on it)');
    expect(card(ctx).querySelectorAll('img, b, i, script').length).toBe(0);
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });

  it('Delete box: the box and what stands on it go; the card reads "Deleted: Table / desk (+1 on it)" with Undo, which brings them back selected', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, T2, EDGE));
    card(ctx).querySelector<HTMLButtonElement>('[data-wt=box-delete]')!.click();
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-computer-001', T2]);
    expect(marked(ctx, F)).toBeNull();
    expect(open(card(ctx))).toBe(true);
    expect(text(ctx, 'box-kind')).toBe('Deleted: Table / desk (+1 on it)');
    expect(text(ctx, 'box-delete')).toBeNull();
    const undo = card(ctx).querySelector<HTMLButtonElement>('[data-wt=box-undo]')!;
    expect(undo.textContent).toBe('Undo');
    expect(undo.style.display).toBe('');
    undo.click();
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBe(T2);                                  // back, and selected
    expect(text(ctx, 'box-kind')).toBe('Table / desk');
    // × closes the card and clears the selection
    card(ctx).querySelector<HTMLButtonElement>('[data-wt=box-close]')!.click();
    expect(open(card(ctx))).toBe(false);
    expect(marked(ctx, F)).toBeNull();
    // the "Deleted" card stays until the next click
    click(ctx, top(ctx, F, 'L2-seat-001'));
    key('Delete');
    expect(text(ctx, 'box-kind')).toBe('Deleted: Chair / stool');
    click(ctx, [5, 5]);
    expect(open(card(ctx))).toBe(false);
  });

  it('a card whose Undo is no longer on the stack hides it (edits set from elsewhere)', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, 'L2-seat-001'));
    key('Delete');
    const undo = () => card(ctx).querySelector<HTMLButtonElement>('[data-wt=box-undo]')!;
    expect(undo().style.display).toBe('');
    F.setPieceEdits(F.pieceEdits());                                  // a takeover from another tab
    expect(open(card(ctx))).toBe(true);
    expect(undo().style.display).toBe('none');
    undo().click();
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-seat-001']);
  });
});

describe('the keys', () => {
  it('Delete removes the selected box; Ctrl+Z undoes (the box is back and selected); Esc closes the card and clears the selection', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, T2, EDGE));
    const del = new KeyboardEvent('keydown', { code: 'Delete', bubbles: true, cancelable: true });
    document.body.dispatchEvent(del);
    expect(del.defaultPrevented).toBe(true);
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-computer-001', T2]);
    key('Delete');                                                    // nothing selected now
    expect(Object.keys(F.pieceEdits()).length).toBe(2);
    key('KeyZ', { ctrlKey: true });
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBe(T2);
    key('Escape');
    expect(marked(ctx, F)).toBeNull();
    expect(open(card(ctx))).toBe(false);
    // Cmd+Z too; Backspace, Ctrl+Delete, Ctrl+Shift+Z and a held Delete do nothing
    click(ctx, top(ctx, F, T2, EDGE));
    for (const [code, init] of [['Backspace', {}], ['Delete', { ctrlKey: true }], ['Delete', { repeat: true }], ['KeyZ', { ctrlKey: true, shiftKey: true }], ['KeyZ', {}]] as const) key(code, init);
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBe(T2);
    key('Delete');
    key('KeyZ', { metaKey: true });
    expect(F.pieceEdits()).toEqual({});
  });

  it('the card offers "(Del)" only while the Delete key is armed; the button itself always works (review of 17 Nov)', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, T2, EDGE));                                // the pointerdown on the canvas arms it
    expect(text(ctx, 'box-delete')).toBe('Delete box (Del)');
    const box = q<HTMLInputElement>(ctx, '[data-wt=furniture-row][data-kind="seat"] [data-wt=kind-height]');
    press(box);                                                       // a height typed in the panel, kept with Enter
    expect(text(ctx, 'box-delete')).toBe('Delete box');
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
    F.setHeight('table', 800);                                        // the card is drawn again: still disarmed
    expect(text(ctx, 'box-delete')).toBe('Delete box');
    press(card(ctx).querySelector('[data-wt=box-family]')!);          // a press on the card arms it again
    expect(text(ctx, 'box-delete')).toBe('Delete box (Del)');
    press(document.body);                                             // elsewhere on the page
    expect(text(ctx, 'box-delete')).toBe('Delete box');
    card(ctx).querySelector<HTMLButtonElement>('[data-wt=box-delete]')!.click();
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-computer-001', T2]);
    // restored from the Restore list: the press there disarmed the key
    const open = q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-open]');
    press(open); open.click();
    const restore = q<HTMLButtonElement>(ctx, '[data-wt=box-restore]');
    press(restore); restore.click();
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBe(T2);
    expect(text(ctx, 'box-delete')).toBe('Delete box');
    click(ctx, top(ctx, F, T2, EDGE));
    expect(text(ctx, 'box-delete')).toBe('Delete box (Del)');
  });

  it('a key while typing in a height box, or for another part of the page, is not the viewer\'s', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, T2, EDGE));
    const box = q<HTMLInputElement>(ctx, '[data-wt=furniture-row][data-kind="table"] [data-wt=kind-height]');
    press(ctx.canvas);
    key('Delete', {}, box);                                           // the height box keeps its own Delete
    key('KeyZ', { ctrlKey: true }, box);
    const outside = document.createElement('button');
    document.body.append(outside);
    key('Delete', {}, outside);                                       // the host's own control
    key('Escape', {}, outside);
    outside.remove();
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBe(T2);
    key('Delete');
    expect(Object.keys(F.pieceEdits()).length).toBe(2);
  });

  it('Delete is armed only while the last pointerdown was on the canvas or the card: a press in the side panel disarms it', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, T2, EDGE));
    press(q(ctx, '[data-wt=furniture-row][data-kind="table"]'));      // into the panel (a height just typed, Enter blurs to the body)
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBe(T2);
    press(document.body);                                             // elsewhere on the page
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
    press(card(ctx).querySelector('[data-wt=box-family]')!);          // the card arms it again
    key('Delete');
    expect(Object.keys(F.pieceEdits()).length).toBe(2);
    // Ctrl+Z needs no arming
    press(q(ctx, '[data-wt=furniture-row][data-kind="table"]'));
    key('KeyZ', { ctrlKey: true });
    expect(F.pieceEdits()).toEqual({});
  });

  it('nothing while the replay runs', () => {
    const { ctx, F } = mount(mini());
    click(ctx, top(ctx, F, 'L2-seat-001'));
    key('Delete');
    click(ctx, top(ctx, F, T2, EDGE));
    ctx.modes.state.locked = true;
    key('Delete'); key('KeyZ', { ctrlKey: true });
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-seat-001']);
  });
});

describe('Walk and Ghost: the box at the crosshair', () => {
  it(`the box in the middle of the view, at most ${AIM_REACH} m from the eye, carries the marker; Delete removes it and a line at the bottom says so`, async () => {
    const { ctx, F } = mount(mini());
    press(ctx.canvas);                                                // the click that took the pointer
    lookDownAt(ctx, F, T2, 3, EDGE);
    setMode(ctx, 'walk');
    await wait(60);
    expect(marked(ctx, F)).toBe(T2);
    expect(open(card(ctx))).toBe(false);                              // the mouse is captured: no card
    lookDownAt(ctx, F, 'L2-seat-001', 2);
    await wait(250);                                                  // looked for 10 times a second
    expect(marked(ctx, F)).toBe('L2-seat-001');
    lookDownAt(ctx, F, T2, AIM_REACH + 0.5, EDGE);                    // too far: a box across a hall is not aimed at
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
    expect(marked(ctx, F)).toBeNull();
    lookDownAt(ctx, F, T2, AIM_REACH - 0.5, EDGE);
    key('Delete');                                                    // aimed on the key press itself
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-computer-001', T2]);
    expect(toast(ctx).textContent).toBe('Deleted: Table / desk (+1 on it) · Ctrl+Z to undo');
    expect(toast(ctx).style.display).toBe('block');
    expect(open(card(ctx))).toBe(false);
    expect(ctx.floorByKey.get('L2')!.colliders.includes(F.meshOf(T2)!)).toBe(false);     // the walker can step into the place
    key('KeyZ', { ctrlKey: true });
    expect(F.pieceEdits()).toEqual({});
    expect(toast(ctx).textContent).toBe('Back: Table / desk on Level 2');
    // Ghost the same; a hidden kind is never aimed at
    setMode(ctx, 'ghost');
    lookDownAt(ctx, F, 'L2-seat-001', 2);
    F.setVisible('seat', false);
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
    F.setVisible('seat', true);
    key('Delete');
    expect(Object.keys(F.pieceEdits())).toEqual(['L2-seat-001']);
    expect(toast(ctx).textContent).toBe('Deleted: Chair / stool · Ctrl+Z to undo');
  });

  it(`two quick Deletes take one box: after a delete nothing new is aimed at until the view moves or ${AIM_HOLD_MS} ms have passed (review of 17 Nov)`, () => {
    vi.useFakeTimers();
    try {
      const { ctx, F } = mount(mini());
      const S1 = 'L1-seat-001', S2 = 'L1-seat-002';                    // S2 stands 1 m behind S1 on the line of sight
      const seat = F.pieces().find(p => p.id === S1)!, y = (seat.z0 + seat.z1) / 2;
      const lookFrom = (x: number, ahead = 0) => {                    // level with the chairs, looking along plan y = 1 (three z = -1)
        ctx.camera.position.set(x, y, -1);
        ctx.camera.lookAt(x + 10, y + ahead, -1);
        ctx.camera.updateMatrixWorld();
      };
      press(ctx.canvas);
      lookFrom(-0.5);
      setMode(ctx, 'walk');
      vi.advanceTimersByTime(0);
      expect(marked(ctx, F)).toBe(S1);
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1]);
      expect(toast(ctx).textContent).toBe('Deleted: Chair / stool · Ctrl+Z to undo');
      vi.advanceTimersByTime(100);                                     // the aim is looked for again: nothing new
      expect(marked(ctx, F)).toBeNull();
      key('Delete');                                                   // 0.1 s later, meant for the same box: nothing
      expect(Object.keys(F.pieceEdits())).toEqual([S1]);
      lookFrom(-0.5 + HOLD_MOVE / 2);                                  // a sway under 2 cm is not a move
      vi.advanceTimersByTime(AIM_HOLD_MS - 200);
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1]);
      expect(marked(ctx, F)).toBeNull();
      vi.advanceTimersByTime(200);                                     // the time is up: the box behind is aimed at
      expect(marked(ctx, F)).toBe(S2);
      // Ghost; Ctrl+Z ends the hold at once (the box is back and aimed at again)
      setMode(ctx, 'ghost');
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1, S2]);
      key('KeyZ', { ctrlKey: true });
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1, S2]);           // deleted again at once
      key('KeyZ', { ctrlKey: true });
      key('KeyZ', { ctrlKey: true });
      expect(F.pieceEdits()).toEqual({});
      // a move of the view ends the hold at once: a step forward, or a turn
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1]);
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1]);
      lookFrom(-0.5 + 2 * HOLD_MOVE);
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1, S2]);
      key('KeyZ', { ctrlKey: true });
      key('KeyZ', { ctrlKey: true });
      lookFrom(-0.5);
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1]);
      lookFrom(-0.5, 0.35);                                            // 2° up: S2 is still under the crosshair
      key('Delete');
      expect(Object.keys(F.pieceEdits())).toEqual([S1, S2]);
    } finally { vi.useRealTimers(); }
  });

  it('no aim with the Camera panel open or while the replay runs; back in Orbit the aim marker goes', async () => {
    const { ctx, F } = mount(mini());
    press(ctx.canvas);
    lookDownAt(ctx, F, T2, 3, EDGE);
    ctx.modes.state.camOpen = true;
    setMode(ctx, 'walk');
    await wait(60);
    expect(marked(ctx, F)).toBeNull();
    key('Delete');
    expect(F.pieceEdits()).toEqual({});
    ctx.modes.state.camOpen = false;
    setMode(ctx, 'walk');                                             // closing the Camera panel says 'mode' again
    await wait(60);
    expect(marked(ctx, F)).toBe(T2);
    setMode(ctx, 'orbit');
    expect(marked(ctx, F)).toBeNull();
    await wait(150);
    expect(marked(ctx, F)).toBeNull();
  });

  it('the line at the bottom goes after 6 s, or with the next delete, restore or undo', () => {
    vi.useFakeTimers();
    try {
      const { ctx, F } = mount(mini());
      press(ctx.canvas);
      setMode(ctx, 'walk');
      lookDownAt(ctx, F, 'L2-seat-001', 2);
      key('Delete');
      expect(toast(ctx).style.display).toBe('block');
      vi.advanceTimersByTime(5900);
      expect(toast(ctx).style.display).toBe('block');
      vi.advanceTimersByTime(200);
      expect(toast(ctx).style.display).toBe('none');
      key('KeyZ', { ctrlKey: true });
      expect(toast(ctx).textContent).toBe('Back: Chair / stool on Level 2');
      F.setPieceEdits({});
      expect(toast(ctx).style.display).toBe('none');
    } finally { vi.useRealTimers(); }
  });
});

describe('the hover label and the cursor', () => {
  const move = async (ctx: TestContext, at: readonly [number, number]) => {
    ctx.canvas.dispatchEvent(new PointerEvent('pointermove', { clientX: at[0], clientY: at[1], buttons: 0, pointerType: 'mouse', bubbles: true }));
    await wait(80);
    const tip = q<HTMLDivElement>(ctx, '[data-wt=furniture-tip]');
    return tip.style.display === 'block' ? tip : null;
  };
  it('with editBoxes: a last line "Click to select" and the pointer cursor over a box; no label while the card is open', async () => {
    const { ctx, F } = mount(mini());
    const tip = (await move(ctx, top(ctx, F, T2, EDGE)))!;
    expect(tip.lastElementChild!.getAttribute('data-wt')).toBe('furniture-tip-hint');
    expect(tip.lastElementChild!.textContent).toBe('Click to select');
    expect(tip.textContent).toContain('Table / desk');
    expect(ctx.canvas.style.cursor).toBe('pointer');
    expect(await move(ctx, [5, 5])).toBeNull();
    expect(ctx.canvas.style.cursor).toBe('');
    await move(ctx, top(ctx, F, T2, EDGE));
    ctx.canvas.dispatchEvent(new PointerEvent('pointerleave'));
    expect(ctx.canvas.style.cursor).toBe('');
    await move(ctx, top(ctx, F, T2, EDGE));
    ctx.canvas.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));    // a drag starts
    expect(ctx.canvas.style.cursor).toBe('');
    click(ctx, top(ctx, F, T2, EDGE));
    expect(await move(ctx, top(ctx, F, 'L2-seat-001'))).toBeNull();   // the card is open: no label, the cursor still says "click"
    expect(ctx.canvas.style.cursor).toBe('pointer');
    key('Escape');
    expect(await move(ctx, top(ctx, F, 'L2-seat-001'))).not.toBeNull();
    // while the replay runs a click would not select: no hint, no pointer
    ctx.modes.state.locked = true;
    const locked = (await move(ctx, top(ctx, F, T2, EDGE)))!;
    expect(locked.querySelector('[data-wt=furniture-tip-hint]')).toBeNull();
    expect(ctx.canvas.style.cursor).toBe('');
  });
  it('without editBoxes: the label as it always was, and the cursor is left alone', async () => {
    const { ctx, F } = mount(mini(), {});
    ctx.canvas.style.cursor = 'crosshair';                            // the host's own
    const tip = (await move(ctx, top(ctx, F, T2, EDGE)))!;
    expect(tip.querySelector('[data-wt=furniture-tip-hint]')).toBeNull();
    expect(tip.textContent).toBe('Table / deskIA_J15_WORKING TABLE - 1400W 1000D 750H1.40 × 1.00 × 0.75 m · Level 2');
    expect(ctx.canvas.style.cursor).toBe('crosshair');
    ctx.canvas.dispatchEvent(new PointerEvent('pointerleave'));
    expect(ctx.canvas.style.cursor).toBe('crosshair');
  });
});

describe('when the selection clears', () => {
  const selected = () => {
    const m = mount(mini());
    click(m.ctx, top(m.ctx, m.F, T2, EDGE));
    expect(marked(m.ctx, m.F)).toBe(T2);
    return m;
  };
  it('a mode that is not Orbit, and the Camera panel opening', () => {
    const a = selected();
    setMode(a.ctx, 'walk');
    expect(open(card(a.ctx))).toBe(false);
    const b = selected();
    b.ctx.modes.state.camOpen = true;
    b.ctx.bus.emit('mode', { mode: 'orbit', floor: 'L1' });           // openCam -> updateHud says 'mode'
    expect([marked(b.ctx, b.F), open(card(b.ctx))]).toEqual([null, false]);
    const c = selected();
    c.ctx.bus.emit('mode', { mode: 'orbit', floor: 'L1' });           // a lens change in Orbit: the selection stays
    expect(marked(c.ctx, c.F)).toBe(T2);
  });
  it('its floor hidden, its kind unticked (not another kind\'s tick, not a typed height)', () => {
    const a = selected();
    a.F.setVisible('seat', false); a.F.setHeight('seat', 500); a.F.setKeepDoorways(false);
    expect(marked(a.ctx, a.F)).toBe(T2);
    a.F.setVisible('table', false);
    expect([marked(a.ctx, a.F), open(card(a.ctx))]).toEqual([null, false]);
    const b = selected();
    b.ctx.visibility.setFloorMode('L1');
    expect([marked(b.ctx, b.F), open(card(b.ctx))]).toEqual([null, false]);
    const c = selected();
    c.ctx.visibility.setFloorMode('L2');
    expect(marked(c.ctx, c.F)).toBe(T2);
  });
  it('its box deleted from elsewhere (bus pieces, any source); another box\'s delete leaves it', () => {
    const a = selected();
    a.F.setPieceEdits({ 'L2-seat-001': { removed: true } });
    expect(marked(a.ctx, a.F)).toBe(T2);
    a.F.setPieceEdits({ [T2]: { removed: true } });                    // a takeover from another tab
    expect([marked(a.ctx, a.F), open(card(a.ctx))]).toEqual([null, false]);
  });
  it('the replay starting, and dispose', () => {
    const a = selected();
    a.ctx.bus.emit('replayPhase', { phase: 'settings' });
    expect([marked(a.ctx, a.F), open(card(a.ctx))]).toEqual([null, false]);
    const b = selected();
    b.ctx.bus.emit('replayPhase', { phase: 'done' });
    expect(marked(b.ctx, b.F)).toBe(T2);
    const m = marker(b.ctx), el = card(b.ctx);
    b.ctx.disposer.dispose();
    expect(m.parent).toBeNull();
    expect(el.isConnected).toBe(false);
    key('Delete'); key('KeyZ', { ctrlKey: true });                    // the listeners are gone
    expect(b.F.pieceEdits()).toEqual({});
  });
});

describe('the marker and the build replay', () => {
  it('is in no late list, so the real fadeLate and restoreLate never touch it; after a replay a new selection shows it at its own opacity', () => {
    const { ctx, F } = mount(mini());
    const floors = ctx.floors.map(rec => ({ rec })) as unknown as ReplayFloorRt[];
    const look: LateLook = new WeakMap();
    click(ctx, top(ctx, F, T2, EDGE));
    const m = marker(ctx), [fill, outline] = m.children as [Mesh, LineSegments];
    const late = new Set<unknown>();
    for (const f of ctx.floors) for (const o of f.late) o.traverse(n => late.add(n));
    expect([m, fill, outline].some(o => late.has(o))).toBe(false);
    for (let p = m.parent; p; p = p.parent) expect(late.has(p)).toBe(false);
    recordLate(floors, look);
    fadeLate(floors, look, null, 0);                                  // the replay hides every late object ...
    expect(F.meshOf(T2)!.visible).toBe(false);
    expect([(fill.material as Material).opacity, (outline.material as Material).opacity, fill.visible, outline.visible]).toEqual([0.35, 1, true, true]);
    ctx.bus.emit('replayPhase', { phase: 'settings' });               // ... and says so a moment later: the selection clears
    expect(m.visible).toBe(false);
    fadeLate(floors, look, null, 1);
    restoreLate(floors, look, null);
    F.apply();
    ctx.bus.emit('replayPhase', { phase: 'done' });
    click(ctx, top(ctx, F, T2, EDGE));
    expect(marked(ctx, F)).toBe(T2);
    expect([m.visible, fill.visible, outline.visible]).toEqual([true, true, true]);
    expect([(outline.material as Material).opacity, (fill.material as Material).opacity, (outline.material as Material).transparent]).toEqual([1, 0.35, false]);
  });
});

describe('the marker and photos', () => {
  it('no render of a real photo (modes/photo.ts) shows the marker, selected in Orbit or aimed at in Walk; the next frame shows it again', async () => {
    // a 2D canvas and toBlob for happy-dom (it has neither), as the modes' own tests
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation((() => ({ drawImage: () => {} })) as unknown as HTMLCanvasElement['getContext']);
    const had = Object.getOwnPropertyDescriptor(HTMLCanvasElement.prototype, 'toBlob');
    Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', { configurable: true, writable: true, value: (cb: (b: Blob) => void) => cb(new Blob(['png'], { type: 'image/png' })) });
    try {
      const { ctx, F } = mount(mini(), { editBoxes: true, noDownload: true });
      const seen: boolean[] = [];
      ctx.renderer.render = () => { seen.push(marker(ctx).visible); };
      const flash = document.createElement('div'), thumbs = document.createElement('div');
      const photos = createPhotos(ctx, ctx.modes.state, {
        frameRect: () => ({ x: 0, y: 0, w: 1400, h: 880 }), shift: () => 0, applyCamera: () => {}, where: () => 'overview',
        applyProjection: () => { ctx.camera.clearViewOffset(); ctx.camera.updateProjectionMatrix(); },
        drawFrame: () => {}, flash, photos: thumbs,
      });
      click(ctx, top(ctx, F, T2, EDGE));
      expect(marked(ctx, F)).toBe(T2);
      const shot = photos.takePhoto();
      expect(seen.length).toBeGreaterThan(1);                           // the tiles, then the screen again
      expect(seen.every(v => !v)).toBe(true);
      expect(await shot).toMatchObject({ width: 1920 });
      await wait(20);
      expect(marked(ctx, F)).toBe(T2);                                // back for the next frame
      expect(open(card(ctx))).toBe(true);
      // Walk: the aimed box
      press(ctx.canvas);
      lookDownAt(ctx, F, 'L2-seat-001', 2);
      setMode(ctx, 'walk');
      await wait(60);
      expect(marked(ctx, F)).toBe('L2-seat-001');
      seen.length = 0;
      await photos.takePhoto();
      expect(seen.length).toBeGreaterThan(1);
      expect(seen.every(v => !v)).toBe(true);
      await wait(150);
      expect(marked(ctx, F)).toBe('L2-seat-001');
      // a selection made while it is hushed shows on the next frame; dispose gives the renderer its own method back
      const own = ctx.renderer.setPixelRatio;
      ctx.disposer.dispose();
      expect(ctx.renderer.setPixelRatio).not.toBe(own);
    } finally {
      if (had) Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', had); else delete (HTMLCanvasElement.prototype as { toBlob?: unknown }).toBlob;
    }
  });
});

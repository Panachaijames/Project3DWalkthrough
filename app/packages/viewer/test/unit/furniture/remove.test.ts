// @vitest-environment happy-dom
// Builder C, step BX (docs/boxes/DESIGN.md 2.4 - 2.8, 8.2): deleting and restoring furniture boxes on the shared test
// context: the cascade and the group restore, the colliders, the 'late' list, the live counts, the client's legend, the
// API reads, setPieceEdits, the bus sources, the undo stack, the legend line and the Restore list.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mesh } from 'three';
import type { BuiltModel, FurnitureApi, InternalEvents, PieceEditMap, ResolvedOptions, ViewerEvents } from '../../../src/contracts';
import { installFurniture } from '../../../src/furniture/index';
import { furnitureCsv } from '../../../src/furniture/logic';
import { fadeLate, materialsOf, recordLate, restoreLate, type LateLook } from '../../../src/replay/apply';
import type { ReplayFloorRt } from '../../../src/replay/objects';
import { bridgeEvents } from '../../../src/viewer';
import { makeTestContext, type TestContext } from '../../harness/context';
import { loadModel } from './util';

let live: TestContext[] = [];
function mount(model: BuiltModel, o: { options?: Partial<ResolvedOptions>; edits?: unknown } = {}) {
  const ctx = makeTestContext({ model, stamp: 'abcdef123456', options: o.options });
  if (o.edits !== undefined) ctx.project.pieceEdits = o.edits as PieceEditMap;
  const pieces: InternalEvents['pieces'][] = [], heights: InternalEvents['furniture'][] = [], boxes: ViewerEvents['boxeschange'][] = [];
  ctx.bus.on('pieces', e => pieces.push(e));
  ctx.bus.on('furniture', e => heights.push(e));
  bridgeEvents(ctx.bus, ctx.events);
  ctx.events.on('boxeschange', e => boxes.push(e));
  const F = installFurniture(ctx);
  ctx.furniture = F;
  live.push(ctx);
  return { ctx, F: F!, pieces, heights, boxes };
}
const staff = (model: BuiltModel = mini(), edits?: unknown) => mount(model, { options: { editBoxes: true }, edits });
beforeEach(() => { localStorage.clear(); });
afterEach(() => { for (const c of live) c.disposer.dispose(); live = []; localStorage.clear(); vi.restoreAllMocks(); });

const mini = () => loadModel('mini');
const R = { removed: true } as const;
const q = <T extends Element = HTMLElement>(ctx: TestContext, sel: string) => ctx.ui.root.querySelector<T & Element>(sel) as unknown as T;
const qa = <T extends Element = HTMLElement>(ctx: TestContext, sel: string) => [...ctx.ui.root.querySelectorAll(sel)] as unknown as T[];
const row = (ctx: TestContext, kind: string) => q<HTMLDivElement>(ctx, `[data-wt=furniture-row][data-kind="${kind}"]`);
const label = (ctx: TestContext, kind: string) => row(ctx, kind).querySelector('[data-wt=kind-label]')!.textContent;
const furnColliders = (ctx: TestContext) => ctx.floors.flatMap(f => f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id as string)).sort();
const inLate = (ctx: TestContext, F: FurnitureApi, id: string) => ctx.floors.some(f => f.late.includes(F.meshOf(id)!));
// a key with nothing focused goes to the body (as in a browser)
const key = (code: string, init: KeyboardEventInit = {}) => document.body.dispatchEvent(new KeyboardEvent('keydown', { code, bubbles: true, cancelable: true, ...init }));
const undo = () => key('KeyZ', { ctrlKey: true });
const shown = (e: HTMLElement | null) => !!e && e.style.display !== 'none' && e.isConnected;
const TABLE = ['L1-table-001', 'L1-computer-001', 'L1-printer-001'];

describe('removePiece, restorePiece, restoreAll', () => {
  it('a delete takes the box and what stands on it; the edits map is closed and in the furniture list\'s order', () => {
    const { F, pieces } = staff();
    expect(F.pieceEdits()).toEqual({});
    expect(F.removePiece('L1-table-001')).toEqual(TABLE);              // the box first, then the pieces on it
    expect(Object.keys(F.pieceEdits())).toEqual(['L1-computer-001', 'L1-printer-001', 'L1-table-001']);   // floor, kind (table order), id
    expect(F.pieceEdits()).toEqual({ 'L1-computer-001': R, 'L1-printer-001': R, 'L1-table-001': R });
    expect(F.removePiece('L1-table-001')).toEqual([]);                 // already deleted
    expect(F.removePiece('L1-computer-001')).toEqual([]);
    expect(F.removePiece('nothing')).toEqual([]);
    expect(F.removePiece('L2-computer-001')).toEqual(['L2-computer-001']);   // a piece on a table: the table stays
    expect(F.pieces().find(p => p.id === 'L2-table-001')!.removed).toBeUndefined();
    expect(pieces.map(e => e.source)).toEqual(['removed', 'removed']);
    expect(pieces.at(-1)!.pieceEdits).toEqual(F.pieceEdits());
  });

  it('a restore brings back the group: the table of a computer that went with it, and everything deleted on a restored table', () => {
    const { F, pieces } = staff();
    F.removePiece('L1-table-001');
    expect(F.restorePiece('L1-computer-001')).toEqual(TABLE);          // the top first
    expect(F.pieceEdits()).toEqual({});
    expect(F.restorePiece('L1-computer-001')).toEqual([]);             // not deleted
    expect(F.restorePiece('nothing')).toEqual([]);
    // a computer deleted on its own, then its table: restoring the table brings the computer back too (the record keeps no history)
    F.removePiece('L1-computer-001');
    expect(F.removePiece('L1-table-001')).toEqual(['L1-table-001', 'L1-printer-001']);
    expect(F.restorePiece('L1-table-001')).toEqual(TABLE);
    // a computer deleted on its own, its table standing: only the computer comes back
    F.removePiece('L2-computer-001');
    expect(F.restorePiece('L2-computer-001')).toEqual(['L2-computer-001']);
    expect(pieces.map(e => e.source)).toEqual(['removed', 'restored', 'removed', 'removed', 'restored', 'removed', 'restored']);
  });

  it('Restore all brings everything back, and its Undo (Ctrl+Z) gives back the exact map; with nothing deleted it does nothing', () => {
    const { F, pieces } = staff();
    F.restoreAll();
    expect(pieces).toEqual([]);
    F.removePiece('L1-table-001'); F.removePiece('L1-seat-002'); F.removePiece('L2-cabinet-001');
    const before = F.pieceEdits();
    expect(Object.keys(before).length).toBe(5);
    F.restoreAll();
    expect(F.pieceEdits()).toEqual({});
    expect(pieces.at(-1)).toEqual({ pieceEdits: {}, source: 'restored' });
    undo();
    expect(F.pieceEdits()).toEqual(before);
    expect(Object.keys(F.pieceEdits())).toEqual(Object.keys(before));
    expect(pieces.at(-1)).toEqual({ pieceEdits: before, source: 'removed' });
  });

  it('the undo stack lasts the visit: each step undoes exactly its own delete or restore, newest first', () => {
    const { F, pieces } = staff();
    F.removePiece('L1-computer-001');                                  // 1
    F.removePiece('L1-table-001');                                     // 2: the table and the printer (the computer was gone already)
    F.restorePiece('L1-table-001');                                    // 3: the whole group
    F.removePiece('L1-seat-001');                                      // 4
    undo();                                                            // 4 back
    expect(Object.keys(F.pieceEdits())).toEqual([]);
    undo();                                                            // 3 undone: the group is deleted again
    expect(Object.keys(F.pieceEdits()).sort()).toEqual([...TABLE].sort());
    undo();                                                            // 2 undone: exactly the table and the printer are back
    expect(F.pieceEdits()).toEqual({ 'L1-computer-001': R });
    undo();                                                            // 1 undone
    expect(F.pieceEdits()).toEqual({});
    const n = pieces.length;
    undo();                                                            // nothing left to undo
    expect(pieces.length).toBe(n);
    expect(pieces.slice(4).map(e => e.source)).toEqual(['restored', 'removed', 'restored', 'restored']);   // the undo of a delete says 'restored'
  });
});

describe('what a deleted box is', () => {
  it('hidden, out of the colliders and out of its floor\'s late list; back on restore; apply() and the ticks keep it hidden', () => {
    const { ctx, F } = staff();
    const all = furnColliders(ctx);
    expect(all).toContain('L1-table-001');
    F.removePiece('L1-table-001');
    for (const id of TABLE) {
      expect(F.meshOf(id)!.visible, id).toBe(false);
      expect(inLate(ctx, F, id), id).toBe(false);
      expect(furnColliders(ctx)).not.toContain(id);
      expect(F.meshOf(id)!.parent).toBe(ctx.floorByKey.get('L1')!.group);     // the mesh itself stays
    }
    F.apply();                                                         // the replay's closing apply()
    F.setVisible('table', false); F.setVisible('table', true);
    F.setBlocks('table', false); F.setBlocks('table', true);
    F.setKeepDoorways(false); F.setKeepDoorways(true);
    F.setHeight('table', 700); F.reset();
    for (const id of TABLE) {
      expect(F.meshOf(id)!.visible, id).toBe(false);
      expect(furnColliders(ctx)).not.toContain(id);
    }
    F.restorePiece('L1-table-001');
    for (const id of TABLE) {
      expect(F.meshOf(id)!.visible, id).toBe(true);
      expect(inLate(ctx, F, id), id).toBe(true);
    }
    expect(furnColliders(ctx)).toEqual(all);
    for (const f of ctx.floors) expect(new Set(f.late).size).toBe(f.late.length);       // no box twice in a late list
  });

  it('a restored box of a hidden kind stays hidden and is no collider until the kind is ticked', () => {
    const { ctx, F } = staff();
    F.removePiece('L1-seat-001');
    F.setVisible('seat', false);
    F.restorePiece('L1-seat-001');
    expect(F.meshOf('L1-seat-001')!.visible).toBe(false);
    expect(furnColliders(ctx)).not.toContain('L1-seat-001');
    F.setVisible('seat', true);
    expect(F.meshOf('L1-seat-001')!.visible).toBe(true);
    expect(furnColliders(ctx)).toContain('L1-seat-001');
  });

  it('a deleted box in an approach is no collider whatever the doorways tick says', () => {
    const { ctx, F } = staff();
    F.removePiece('L1-seat-002');
    F.setKeepDoorways(false);
    expect(furnColliders(ctx)).not.toContain('L1-seat-002');
    expect(furnColliders(ctx)).toContain('L2-seat-001');
  });

  it('the build replay never shows it: the real fadeLate and restoreLate do not reach a deleted box, and reach it again once restored', () => {
    const { ctx, F } = staff();
    const floors = ctx.floors.map(rec => ({ rec })) as unknown as ReplayFloorRt[];
    const look: LateLook = new WeakMap();
    recordLate(floors, look);
    F.removePiece('L1-table-001');
    const gone = F.meshOf('L1-table-001')!, kept = F.meshOf('L1-table-002')!;
    fadeLate(floors, look, null, 0);
    expect([gone.visible, kept.visible]).toEqual([false, false]);
    for (const t of [0.3, 0.7, 1]) {
      fadeLate(floors, look, null, t);
      expect([gone.visible, kept.visible], `t = ${t}`).toEqual([false, true]);
    }
    restoreLate(floors, look, null);
    F.apply();
    expect([gone.visible, kept.visible]).toEqual([false, true]);
    F.restorePiece('L1-table-001');
    fadeLate(floors, look, null, 0);
    expect(gone.visible).toBe(false);
    fadeLate(floors, look, null, 1);
    restoreLate(floors, look, null);
    F.apply();
    expect(gone.visible).toBe(true);
    expect(materialsOf(gone).map(m => [m.opacity, m.transparent])).toEqual([[1, false]]);
  });

  it('a kind whose last box went while the replay was fading gets its own look back from apply()', () => {
    const { ctx, F } = staff();
    const floors = ctx.floors.map(rec => ({ rec })) as unknown as ReplayFloorRt[];
    const look: LateLook = new WeakMap();
    recordLate(floors, look);
    fadeLate(floors, look, null, 0.4);
    const plant = F.meshOf('L1-plant-001')!;
    F.setPieceEdits({ 'L1-plant-001': R });                             // a takeover from another tab, mid-replay
    fadeLate(floors, look, null, 1);
    restoreLate(floors, look, null);
    expect(materialsOf(plant)[0]!.opacity).toBeCloseTo(0.4);           // nothing of the plants is in a late list any more
    F.apply();
    expect(materialsOf(plant).map(m => [m.opacity, m.transparent])).toEqual([[1, false]]);
    expect(((plant.children[0] as Mesh).material as { opacity: number }).opacity).toBe(1);
    F.restorePiece('L1-plant-001');
    expect(plant.visible).toBe(true);
  });

  it('while the build replay runs (a takeover from another tab): state, colliders and the late list change at once; a restored box waits for the closing apply()', () => {
    const { ctx, F } = staff(mini(), { 'L1-seat-001': R });
    const floors = ctx.floors.map(rec => ({ rec })) as unknown as ReplayFloorRt[];
    const look: LateLook = new WeakMap();
    recordLate(floors, look);
    const phase = { phase: 'play' };
    ctx.replay = phase as unknown as TestContext['replay'];
    fadeLate(floors, look, null, 0);                                  // the replay has hidden every late object
    const seat = F.meshOf('L1-seat-001')!, table = F.meshOf('L1-table-001')!, other = F.meshOf('L1-table-002')!;
    F.setPieceEdits({ 'L1-table-001': R });                            // the seat is back, the table (and what stands on it) goes
    expect(F.pieces().find(p => p.id === 'L1-seat-001')!.removed).toBeUndefined();
    expect([inLate(ctx, F, 'L1-seat-001'), inLate(ctx, F, 'L1-table-001')]).toEqual([true, false]);
    expect(furnColliders(ctx)).toContain('L1-seat-001');
    expect(furnColliders(ctx)).not.toContain('L1-table-001');
    expect([seat.visible, table.visible, other.visible]).toEqual([false, false, false]);   // nothing pops in before the replay shows it
    fadeLate(floors, look, null, 0.5);                                // the replay fades the late objects in: the seat with them
    expect([seat.visible, table.visible, other.visible]).toEqual([true, false, true]);
    fadeLate(floors, look, null, 1);
    restoreLate(floors, look, null);
    phase.phase = 'done';
    F.apply();
    expect([seat.visible, table.visible, other.visible]).toEqual([true, false, true]);
    // outside the replay a restore shows at once
    F.restorePiece('L1-table-001');
    expect(table.visible).toBe(true);
  });

  it('the starting edits of the project are applied before anything shows (closed; odd values and unknown ids ignored)', () => {
    const edits = { 'L1-table-001': { removed: true }, 'L9-nothing-001': { removed: true }, 'L1-seat-001': 'yes', 'L1-seat-003': { removed: false },
      'L1-plant-001': { removed: true, kind: 'later' }, 'L1-tv-001': null };
    const { ctx, F, pieces, boxes } = staff(mini(), edits);
    expect(Object.keys(F.pieceEdits()).sort()).toEqual(['L1-computer-001', 'L1-plant-001', 'L1-printer-001', 'L1-table-001']);
    expect(F.meshOf('L1-computer-001')!.visible).toBe(false);
    expect(inLate(ctx, F, 'L1-computer-001')).toBe(false);
    expect(furnColliders(ctx)).not.toContain('L1-plant-001');
    expect(F.meshOf('L1-seat-001')!.visible).toBe(true);
    expect([pieces, boxes]).toEqual([[], []]);                         // nothing is announced for what the file carries
    for (const odd of [null, undefined, [], 'x', 7]) expect(staff(mini(), odd).F.pieceEdits()).toEqual({});
  });
});

describe('the API reads', () => {
  it('pieces(): removed only on a deleted box, whose visible and blocking are false; kinds(): every built kind with its live count', () => {
    const { F } = staff();
    const m = mini();
    expect(F.pieces().every(p => !('removed' in p))).toBe(true);
    F.removePiece('L1-table-001'); F.removePiece('L1-plant-001');
    for (const p of F.pieces()) {
      const gone = [...TABLE, 'L1-plant-001'].includes(p.id);
      expect('removed' in p, p.id).toBe(gone);
      if (gone) expect([p.removed, p.visible, p.blocking], p.id).toEqual([true, false, false]);
      else expect(p.visible, p.id).toBe(true);
    }
    expect(F.pieces().length).toBe(m.furniture!.length);
    expect(F.kinds().map(k => k.key)).toEqual(m.furnitureKinds!.map(k => k.key));
    const count = Object.fromEntries(F.kinds().map(k => [k.key, k.count]));
    expect([count.table, count.computer, count.printer, count.plant, count.seat]).toEqual([2, 1, 0, 0, 4]);
    F.restoreAll();
    expect(F.kinds().map(k => k.count)).toEqual(m.furnitureKinds!.map(k => k.count));
    expect(F.pieces().every(p => !('removed' in p))).toBe(true);
  });

  it('csv() leaves the deleted boxes out, and is the text of before once they are back', () => {
    const { F } = staff();
    const m = mini(), full = F.csv();
    expect(full).toBe(furnitureCsv(m, {}));
    F.removePiece('L1-table-001');
    expect(F.csv()).toBe(furnitureCsv(m, {}, new Set(TABLE)));
    expect(F.csv().split('\r\n').length).toBe(full.split('\r\n').length - 3);
    expect(F.saveCsv()).toBe(F.csv());
    F.restoreAll();
    expect(F.csv()).toBe(full);
  });

  it('setPieceEdits: the map replaces the deleted set, closed; unknown ids and odd values ignored; bus source api, no public event; the undo stack is cleared', () => {
    const { F, pieces, boxes } = staff();
    F.removePiece('L1-seat-001');
    expect(boxes.length).toBe(1);
    F.setPieceEdits({ 'L1-table-001': R, 'L9-nothing-001': R, 'L1-seat-003': {}, 'L1-tv-001': 'x' as unknown as { removed: true } });
    expect(F.pieceEdits()).toEqual({ 'L1-computer-001': R, 'L1-printer-001': R, 'L1-table-001': R });     // the seat is back: not in the map
    expect(pieces.at(-1)).toEqual({ pieceEdits: F.pieceEdits(), source: 'api' });
    expect(boxes.length).toBe(1);                                      // nothing public
    undo();                                                            // the seat's delete is no longer on the stack
    expect(pieces.at(-1)!.source).toBe('api');
    expect(F.pieceEdits()).toEqual({ 'L1-computer-001': R, 'L1-printer-001': R, 'L1-table-001': R });
    F.setPieceEdits({});
    expect(F.pieceEdits()).toEqual({});
    F.setPieceEdits(null as unknown as PieceEditMap);
    expect(pieces.slice(-2).map(e => e.source)).toEqual(['api', 'api']);   // every call says so, like setHeights
    expect(boxes.length).toBe(1);
  });

  it('the public boxeschange: the whole map each time, for deletes, restores and undos, never for setPieceEdits', () => {
    const { F, boxes } = staff();
    F.removePiece('L1-table-001');
    F.restorePiece('L1-printer-001');
    F.removePiece('L1-seat-001');
    undo();
    F.setPieceEdits({ 'L1-seat-001': R });
    expect(boxes).toEqual([
      { pieceEdits: { 'L1-computer-001': R, 'L1-printer-001': R, 'L1-table-001': R }, source: 'removed' },
      { pieceEdits: {}, source: 'restored' },
      { pieceEdits: { 'L1-seat-001': R }, source: 'removed' },
      { pieceEdits: {}, source: 'restored' },
    ]);
  });

  it('Reset heights leaves the deleted boxes alone, and a delete says nothing on the heights bus', () => {
    const { ctx, F, heights, pieces } = staff();
    F.setHeight('table', 600);
    F.removePiece('L1-table-001');
    expect(heights.map(e => e.source)).toEqual(['typed']);
    q<HTMLButtonElement>(ctx, '[data-wt=furniture-reset]').click();
    expect(heights.map(e => e.source)).toEqual(['typed', 'reset']);
    expect(pieces.map(e => e.source)).toEqual(['removed']);
    expect(Object.keys(F.pieceEdits()).length).toBe(3);
    expect(F.heights()).toEqual({});
  });

  it('without editBoxes the API still deletes and restores (the offline test hook), for the visit only: nothing is stored', () => {
    const { ctx, F } = mount(mini());
    expect(F.removePiece('L1-table-001')).toEqual(TABLE);
    expect(F.meshOf('L1-table-001')!.visible).toBe(false);
    expect(localStorage.length).toBe(0);
    expect(label(ctx, 'table')).toBe('Table / desk (2)');
    expect(F.restorePiece('L1-table-001')).toEqual(TABLE);
    for (const wt of ['box-card', 'box-toast', 'boxes-restore', 'furniture-removed', 'furniture-edit-hint']) expect(q(ctx, `[data-wt=${wt}]`), wt).toBeNull();
    expect(ctx.scene.getObjectByName('furniture-selection')).toBeUndefined();
  });
});

describe('the legend', () => {
  it('the staff app: live counts in the labels; an emptied kind keeps its row, "(0)" and data-empty; the edit hint under the note', () => {
    const { ctx, F } = staff();
    expect(q(ctx, '[data-wt=furniture-edit-hint]').textContent).toBe('Orbit: click a box to delete it · Walk: aim at it and press Delete');
    const kids = [...q(ctx, '[data-wt=furniture]').children];
    expect(kids.indexOf(q(ctx, '[data-wt=furniture-edit-hint]'))).toBe(kids.indexOf(q(ctx, '[data-wt=furniture-note]')) + 1);
    expect(q(ctx, '[data-wt=furniture-note]').textContent).toBe('Type a height in mm for each kind. Walk: boxes stop you; Ghost passes through.');
    expect(label(ctx, 'table')).toBe('Table / desk (3)');
    F.removePiece('L1-table-001');
    expect([label(ctx, 'table'), label(ctx, 'computer'), label(ctx, 'printer')]).toEqual(['Table / desk (2)', 'Computer / monitor (1)', 'Printer / copier (0)']);
    expect(row(ctx, 'printer').hasAttribute('data-empty')).toBe(true);
    expect(row(ctx, 'table').hasAttribute('data-empty')).toBe(false);
    expect(qa(ctx, '[data-wt=furniture-row]').length).toBe(mini().furnitureKinds!.length);
    // the emptied kind's height stays reachable
    expect(F.setHeight('printer', 350)).toBe(true);
    expect(row(ctx, 'printer').querySelector<HTMLInputElement>('[data-wt=kind-height]')!.value).toBe('350');
    F.restoreAll();
    expect(label(ctx, 'printer')).toBe('Printer / copier (1)');
    expect(row(ctx, 'printer').hasAttribute('data-empty')).toBe(false);
  });

  it('a height being typed keeps its text when a box is deleted', () => {
    const { ctx, F } = staff();
    const box = row(ctx, 'table').querySelector<HTMLInputElement>('[data-wt=kind-height]')!;
    box.value = '6';
    F.removePiece('L1-seat-001');
    expect(box.value).toBe('6');
  });

  it('the client\'s file (editBoxes off): a kind with no live piece gets no row; Keep doorways only with a live box in an approach; counts live', () => {
    const edits = { 'L1-table-001': R, 'L1-plant-001': R };
    const { ctx, F } = mount(mini(), { edits });
    expect(row(ctx, 'printer')).toBeNull();
    expect(row(ctx, 'plant')).toBeNull();
    expect(label(ctx, 'table')).toBe('Table / desk (2)');
    expect(label(ctx, 'computer')).toBe('Computer / monitor (1)');
    expect(qa(ctx, '[data-wt=furniture-row]').length).toBe(mini().furnitureKinds!.length - 2);
    expect(qa(ctx, '[data-wt=furniture-row][data-empty]').length).toBe(0);
    expect(F.kinds().map(k => k.key)).toEqual(mini().furnitureKinds!.map(k => k.key));       // the API lists every built kind
    expect(F.kinds().find(k => k.key === 'printer')!.count).toBe(0);
    expect(q(ctx, '[data-wt=furniture-keep]')).not.toBeNull();
    expect(q(ctx, '[data-wt=furniture-door]').title.startsWith('2 of the boxes stand')).toBe(true);
    // the master tick follows the rows it has
    q<HTMLInputElement>(ctx, '[data-wt=furniture-all]').click();
    expect(q<HTMLInputElement>(ctx, '[data-wt=furniture-all]').indeterminate).toBe(false);
    expect(F.kinds().every(k => !k.visible)).toBe(true);
    // both boxes in an approach deleted: no tick; one left: the tick, counting 1
    const none = mount(mini(), { edits: { 'L1-seat-002': R, 'L2-seat-001': R } });
    expect(q(none.ctx, '[data-wt=furniture-keep]')).toBeNull();
    expect(none.F.keepDoorways()).toBe(true);
    const one = mount(mini(), { edits: { 'L1-seat-002': R } });
    expect(q(one.ctx, '[data-wt=furniture-door]').title.startsWith('1 of the boxes stand')).toBe(true);
    for (const c of [ctx, none.ctx, one.ctx]) {
      for (const wt of ['furniture-removed', 'furniture-edit-hint', 'boxes-restore', 'box-card']) expect(q(c, `[data-wt=${wt}]`), wt).toBeNull();
    }
  });

  it('the staff app keeps the Keep doorways tick while its boxes are deleted; the tooltip counts the live ones', () => {
    const { ctx, F } = staff();
    const tip = () => q(ctx, '[data-wt=furniture-door]').title;
    expect(tip()).toBe('2 of the boxes stand in front of a door or a passage. Ticked: Walk is not stopped by them (they stay drawn), so every doorway can be walked through. Unticked: they stop you like any other box.');
    F.removePiece('L1-seat-002');
    expect(tip().startsWith('1 of the boxes stand in front of a door or a passage. Ticked:')).toBe(true);
    F.removePiece('L2-seat-001');
    expect(tip().startsWith('0 of the boxes stand')).toBe(true);
    expect(q<HTMLInputElement>(ctx, '[data-wt=furniture-keep]').checked).toBe(true);
    undo();
    expect(tip().startsWith('1 of the boxes stand')).toBe(true);
  });
});

describe('the line of the deleted boxes and the Restore list', () => {
  const line = (ctx: TestContext) => q(ctx, '[data-wt=furniture-removed]');
  const pop = (ctx: TestContext) => q(ctx, '[data-wt=boxes-restore]');
  const visible = (b: HTMLElement | null) => !!b && b.style.display !== 'none';

  it('no line with nothing deleted; "3 boxes deleted · Restore…" between the rows and the buttons while something is', () => {
    const { ctx, F } = staff();
    expect(line(ctx)).toBeNull();
    expect(shown(pop(ctx))).toBe(false);
    F.removePiece('L1-seat-001');
    expect(line(ctx).textContent).toBe('1 box deleted · Restore…Undo');
    expect(visible(q(ctx, '[data-wt=boxes-restore-open]'))).toBe(true);
    expect(visible(q(ctx, '[data-wt=boxes-restore-undo]'))).toBe(false);
    F.removePiece('L1-table-001');
    expect(line(ctx).firstElementChild!.textContent).toBe('4 boxes deleted · ');
    const kids = [...q(ctx, '[data-wt=furniture]').children];
    expect(kids.indexOf(line(ctx))).toBe(kids.indexOf(q(ctx, '[data-wt=furniture-buttons]')) - 1);
    expect(kids.indexOf(line(ctx))).toBeGreaterThan(kids.indexOf(qa(ctx, '[data-wt=furniture-row]').at(-1)!));
    expect(qa(ctx, '[data-wt=furniture-buttons] button').map(b => b.textContent)).toEqual(['Reset heights', 'Save list (CSV)']);
    expect(qa(ctx, '[data-wt=furniture-head] span').length).toBe(5);
    F.restorePiece('L1-seat-001'); F.restorePiece('L1-table-001');
    expect(line(ctx)).toBeNull();
  });

  it('the list: one line per group with its dependents folded in, Restore per line, Restore all, × closes; it closes when nothing is left', () => {
    const { ctx, F } = staff();
    F.removePiece('L1-table-001'); F.removePiece('L1-seat-002'); F.removePiece('L2-computer-001');
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-open]').click();
    expect(shown(pop(ctx))).toBe(true);
    expect(pop(ctx).parentElement).toBe(ctx.ui.root);
    const rows = () => qa(ctx, '[data-wt=boxes-restore-row]');
    expect(rows().map(r => r.getAttribute('data-id'))).toEqual(['L1-seat-002', 'L1-table-001', 'L2-computer-001']);
    expect(rows().map(r => r.querySelector('[data-wt=boxes-restore-what]')!.textContent)).toEqual([
      'Chair / stool · mollie_chair_a685_revit - A685 2 · Level 1 L1-seat-002',
      'Table / desk · IA_J15_WORKING TABLE - 1800W 1000D 750H · Level 1 (+2 on it) L1-table-001',
      'Computer / monitor · Enscape AssetDefinition - Computer 003 · Level 2 L2-computer-001',
    ]);
    expect(rows().map(r => r.querySelector('small')!.textContent)).toEqual(['L1-seat-002', 'L1-table-001', 'L2-computer-001']);
    expect(rows().every(r => r.querySelector('[data-wt=box-restore]')!.textContent === 'Restore')).toBe(true);
    expect(q(ctx, '[data-wt=boxes-restore-all]').textContent).toBe('Restore all');
    rows()[1]!.querySelector<HTMLButtonElement>('[data-wt=box-restore]')!.click();
    expect(Object.keys(F.pieceEdits())).toEqual(['L1-seat-002', 'L2-computer-001']);
    expect(rows().map(r => r.getAttribute('data-id'))).toEqual(['L1-seat-002', 'L2-computer-001']);   // the open list follows
    expect(line(ctx).firstElementChild!.textContent).toBe('2 boxes deleted · ');
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-close]').click();
    expect(shown(pop(ctx))).toBe(false);
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-open]').click();
    rows()[0]!.querySelector<HTMLButtonElement>('[data-wt=box-restore]')!.click();
    rows()[0]!.querySelector<HTMLButtonElement>('[data-wt=box-restore]')!.click();
    expect(F.pieceEdits()).toEqual({});
    expect(shown(pop(ctx))).toBe(false);                               // nothing left
    expect(line(ctx)).toBeNull();
  });

  it('Restore all: "All 5 boxes are back · Undo", until the next delete or restore; its Undo puts back the exact map', () => {
    const { ctx, F, boxes } = staff();
    F.removePiece('L1-table-001'); F.removePiece('L1-seat-002'); F.removePiece('L2-computer-001');
    const before = F.pieceEdits();
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-open]').click();
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-all]').click();
    expect(F.pieceEdits()).toEqual({});
    expect(shown(pop(ctx))).toBe(false);
    expect(line(ctx).firstElementChild!.textContent).toBe('All 5 boxes are back · ');
    expect(visible(q(ctx, '[data-wt=boxes-restore-undo]'))).toBe(true);
    expect(visible(q(ctx, '[data-wt=boxes-restore-open]'))).toBe(false);
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-undo]').click();
    expect(F.pieceEdits()).toEqual(before);
    expect(line(ctx).firstElementChild!.textContent).toBe('5 boxes deleted · ');
    expect(boxes.slice(-2)).toEqual([{ pieceEdits: {}, source: 'restored' }, { pieceEdits: before, source: 'removed' }]);
    // again, and then a delete: the line is the count again; a setPieceEdits clears it too
    F.restoreAll();
    expect(line(ctx).firstElementChild!.textContent).toBe('All 5 boxes are back · ');
    F.removePiece('L1-plant-001');
    expect(line(ctx).firstElementChild!.textContent).toBe('1 box deleted · ');
    F.restoreAll();
    expect(line(ctx).firstElementChild!.textContent).toBe('1 box is back · ');
    F.setPieceEdits({});
    expect(line(ctx)).toBeNull();
  });

  it('a hostile kind label, family and floor name stay text in the list', () => {
    const m = mini();
    m.furnitureKinds!.find(k => k.key === 'table')!.label = '<img src=x onerror="window.__pwned = 1">';
    m.furniture!.find(p => p.id === 'L1-table-001')!.family = '<b onclick="window.__pwned = 2">family</b>';
    m.floors[0]!.name = '<script>window.__pwned = 3</script>';
    const { ctx, F } = staff(m);
    F.removePiece('L1-table-001');
    q<HTMLButtonElement>(ctx, '[data-wt=boxes-restore-open]').click();
    const what = q(ctx, '[data-wt=boxes-restore-row] [data-wt=boxes-restore-what]');
    expect(what.textContent).toBe('<img src=x onerror="window.__pwned = 1"> · <b onclick="window.__pwned = 2">family</b> · <script>window.__pwned = 3</script> (+2 on it) L1-table-001');
    expect(pop(ctx).querySelector('img, script, b:not([data-wt]) b')).toBeNull();
    expect(pop(ctx).querySelectorAll('img, script').length).toBe(0);
    expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined();
  });
});

describe('what a restore shows (docs/boxes/DESIGN.md 2.6)', () => {
  const card = (ctx: TestContext) => q(ctx, '[data-wt=box-card]');
  const toast = (ctx: TestContext) => q(ctx, '[data-wt=box-toast]');
  const marker = (ctx: TestContext) => ctx.scene.getObjectByName('furniture-selection')!;

  it('Orbit, the floor showing and the kind ticked: the restored box is the selection (marker and card)', () => {
    const { ctx, F } = staff();
    ctx.visibility.setFloorMode('L1');                                 // its floor alone (Both floors: the next test)
    F.removePiece('L1-table-001');
    const cam = ctx.camera.position.clone();
    F.restorePiece('L1-table-001');
    expect(marker(ctx).visible).toBe(true);
    expect(shown(card(ctx))).toBe(true);
    expect(card(ctx).querySelector('[data-wt=box-kind]')!.textContent).toBe('Table / desk');
    expect(card(ctx).querySelector('[data-wt=box-id]')!.textContent).toBe('L1-table-001');
    expect(card(ctx).querySelector('[data-wt=box-delete]')).not.toBeNull();
    expect(ctx.camera.position.equals(cam)).toBe(true);                // the camera does not move
  });

  it('Orbit, the floor not showing: "Back on Level 1 (not shown: press Level 1)"; the kind hidden: "(... is hidden: tick it to see it)"', () => {
    const { ctx, F } = staff();
    F.removePiece('L1-table-001');
    ctx.visibility.setFloorMode('L2');
    F.restorePiece('L1-table-001');
    expect(marker(ctx).visible).toBe(false);
    expect(card(ctx).querySelector('[data-wt=box-back]')!.textContent).toBe('Back on Level 1 (not shown: press Level 1)');
    expect(card(ctx).querySelector('[data-wt=box-back-kind]')).toBeNull();
    expect(card(ctx).querySelector('[data-wt=box-delete]')).toBeNull();
    ctx.visibility.setFloorMode('L1');
    F.removePiece('L1-seat-001');
    F.setVisible('seat', false);
    F.restorePiece('L1-seat-001');
    expect(card(ctx).querySelector('[data-wt=box-kind]')!.textContent).toBe('Chair / stool');
    expect(card(ctx).querySelector('[data-wt=box-back]')!.textContent).toBe('Back on Level 1');
    expect(card(ctx).querySelector('[data-wt=box-back-kind]')!.textContent).toBe('(Chair / stool is hidden: tick it to see it)');
    key('Escape');
    expect(shown(card(ctx))).toBe(false);
  });

  it('Orbit, Both floors, a Level 1 box under Level 2\'s plate: not shown (no marker through the plate), "Back on Level 1 (under Level 2: press Level 1 to see it)"; beyond the plate\'s edge it is selected (review of 17 Nov)', () => {
    const { ctx, F } = staff();
    expect(ctx.visibility.floorMode).toBe('all');
    F.removePiece('L1-table-001');
    F.restorePiece('L1-table-001');
    expect(marker(ctx).visible).toBe(false);
    expect(shown(card(ctx))).toBe(true);
    expect(card(ctx).querySelector('[data-wt=box-kind]')!.textContent).toBe('Table / desk');
    expect(card(ctx).querySelector('[data-wt=box-back]')!.textContent).toBe('Back on Level 1 (under Level 2: press Level 1 to see it)');
    expect(card(ctx).querySelector('[data-wt=box-delete]')).toBeNull();
    // the TV stands beyond Level 2's plate (x 7; the plate ends at 6.2): seen from above, so it is the selection
    F.removePiece('L1-tv-001');
    F.restorePiece('L1-tv-001');
    expect(marker(ctx).visible).toBe(true);
    expect(card(ctx).querySelector('[data-wt=box-id]')!.textContent).toBe('L1-tv-001');
    // Level 1 alone: no floor shown above it, so it is the selection
    ctx.visibility.setFloorMode('L1');
    F.removePiece('L1-table-001'); F.restorePiece('L1-table-001');
    expect([marker(ctx).visible, card(ctx).querySelector('[data-wt=box-id]')?.textContent]).toEqual([true, 'L1-table-001']);
    // Ctrl+Z of a delete made on Level 1 alone, undone in Both floors: the same rule
    F.removePiece('L1-seat-001');
    ctx.visibility.setFloorMode('all');
    undo();
    expect(marker(ctx).visible).toBe(false);
    expect(card(ctx).querySelector('[data-wt=box-back]')!.textContent).toBe('Back on Level 1 (under Level 2: press Level 1 to see it)');
  });

  it('the floor above is named by its real name (as text), the house\'s too', () => {
    const m = mini();
    m.floors[1]!.name = '<i>Mezzanine</i>';
    const a = staff(m);
    a.F.removePiece('L1-seat-001'); a.F.restorePiece('L1-seat-001');
    expect(card(a.ctx).querySelector('[data-wt=box-back]')!.textContent).toBe('Back on Level 1 (under <i>Mezzanine</i>: press Level 1 to see it)');
    expect(card(a.ctx).querySelectorAll('i').length).toBe(0);
    const b = staff(loadModel('house'));
    b.F.removePiece('ground-seat-001'); b.F.restorePiece('ground-seat-001');
    expect(marker(b.ctx).visible).toBe(false);
    expect(card(b.ctx).querySelector('[data-wt=box-back]')!.textContent).toBe('Back on Ground floor (under Upper floor: press Ground floor to see it)');
  });

  it('Walk or Ghost: no selection, no card; the line at the bottom reads "Back: Table / desk on Level 1"', () => {
    const { ctx, F } = staff();
    F.removePiece('L1-table-001');
    ctx.modes.state.mode = 'walk';
    ctx.bus.emit('mode', { mode: 'walk', floor: 'L1' });
    F.restorePiece('L1-table-001');
    expect(shown(card(ctx))).toBe(false);
    expect(toast(ctx).textContent).toBe('Back: Table / desk on Level 1');
    expect(toast(ctx).style.display).toBe('block');
  });
});

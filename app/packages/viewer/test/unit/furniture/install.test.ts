// @vitest-environment happy-dom
// Builder C: installFurniture on the shared test context (DESIGN.md 5.6, 11.2, 11.5, 17.2): the boxes, the colliders and the
// doorways rule, the legend DOM and its typing state, the storage modes, the bus events, the leniency, the CSV, the hover label.
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Color, Vector3, type LineBasicMaterial, type LineSegments, type Mesh, type MeshStandardMaterial } from 'three';
import type { BuiltModel, FurnitureApi, InternalEvents, ResolvedOptions } from '../../../src/contracts';
import { installFurniture } from '../../../src/furniture/index';
import { furnitureCsv } from '../../../src/furniture/logic';
import { makeTestContext, type TestContext } from '../../harness/context';
import { APP, loadModel, readText } from './util';

let live: TestContext[] = [];
function mount(model: BuiltModel, options?: Partial<ResolvedOptions>, heights?: Record<string, number> | null) {
  const ctx = makeTestContext({ model, stamp: 'abcdef123456', options });
  if (heights !== undefined) ctx.project.heights = heights;
  const events: InternalEvents['furniture'][] = [];
  ctx.bus.on('furniture', e => events.push(e));
  const F = installFurniture(ctx);
  ctx.furniture = F;
  live.push(ctx);
  return { ctx, F: F!, events };
}
beforeEach(() => { localStorage.clear(); });
afterEach(() => { for (const c of live) c.disposer.dispose(); live = []; localStorage.clear(); vi.restoreAllMocks(); });

const mini = () => loadModel('mini');
const q = <T extends Element = HTMLElement>(ctx: TestContext, sel: string) => ctx.ui.root.querySelector<T & Element>(sel) as unknown as T;
const qa = <T extends Element = HTMLElement>(ctx: TestContext, sel: string) => [...ctx.ui.root.querySelectorAll(sel)] as unknown as T[];
const row = (ctx: TestContext, kind: string) => q<HTMLDivElement>(ctx, `[data-wt=furniture-row][data-kind="${kind}"]`);
const box = (ctx: TestContext, kind: string) => q<HTMLInputElement>(ctx, `[data-wt=furniture-row][data-kind="${kind}"] [data-wt=kind-height]`);
const furnColliders = (ctx: TestContext) => Object.fromEntries(ctx.floors.map(f => [f.key, f.colliders.filter(m => m.name.startsWith('furn:')).map(m => m.userData.id as string).sort()]));
const near = (a: number, b: number, tol = 1e-6) => Math.abs(a - b) <= tol;

describe('no furniture', () => {
  it('returns null and adds nothing (no legend, no label, no style, nothing in the groups)', () => {
    const ctx = makeTestContext({ model: loadModel('bank-v1') });
    live.push(ctx);
    const kids = ctx.floors.map(f => f.group.children.length), late = ctx.floors.map(f => f.late.length);
    const css = ctx.ui.root.querySelector('style')!.textContent;
    expect(installFurniture(ctx)).toBeNull();
    expect(ctx.panel.slot('furniture').children.length).toBe(0);
    expect(ctx.ui.root.querySelector('[data-wt=furniture-tip]')).toBeNull();
    expect(ctx.ui.root.querySelector('style')!.textContent).toBe(css);
    expect(ctx.floors.map(f => f.group.children.length)).toEqual(kids);
    expect(ctx.floors.map(f => f.late.length)).toEqual(late);
  });
  it('also when every piece is of an unknown kind (left out with a warning)', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const m = mini();
    m.furniture = m.furniture!.map(p => ({ ...p, kind: 'spaceship' }));
    const ctx = makeTestContext({ model: m });
    live.push(ctx);
    expect(installFurniture(ctx)).toBeNull();
    expect(warn).toHaveBeenCalledTimes(m.furniture.length);
  });
});

describe('the boxes', () => {
  it('one box per piece, a child of its floor group and in its late list, named furn:<kind>:<id>, with userData, an outline, no bounds tree', () => {
    const { ctx, F } = mount(mini());
    const m = mini();
    const all: Mesh[] = [];
    for (const f of ctx.floors) f.group.traverse(o => { if (o.name.startsWith('furn:')) all.push(o as Mesh); });
    expect(all.length).toBe(m.furniture!.length);
    for (const p of m.furniture!) {
      const mesh = F.meshOf(p.id)!;
      const fl = ctx.floorByKey.get(p.floor)!;
      expect(mesh.parent).toBe(fl.group);
      expect(fl.late.includes(mesh)).toBe(true);
      expect(mesh.name).toBe(`furn:${p.kind}:${p.id}`);
      expect(mesh.userData).toMatchObject({ id: p.id, kind: p.kind, family: p.family, floor: p.floor });
      expect((mesh.userData.size as number[]).length).toBe(3);
      expect(mesh.children.some(c => (c as LineSegments).isLineSegments)).toBe(true);
      expect(mesh.geometry.boundsTree).toBeUndefined();
    }
    expect(F.meshOf('nothing')).toBeNull();
  });

  it('stands at (x, modelLevel + z0, -y), w x height x d, turned by rot, coloured by its kind, edges x 0.4; single-sided faces behind the outline', () => {
    const { ctx, F } = mount(mini());
    const kinds = Object.fromEntries(mini().furnitureKinds!.map(k => [k.key, k]));
    for (const p of F.pieces()) {
      const mesh = F.meshOf(p.id)!, fl = ctx.floorByKey.get(p.floor)!;
      expect(near(mesh.position.x, p.x) && near(mesh.position.y, fl.modelLevel + p.z0) && near(mesh.position.z, -p.y)).toBe(true);
      expect(near(mesh.scale.x, p.w) && near(mesh.scale.y, p.z1 - p.z0) && near(mesh.scale.z, p.d)).toBe(true);
      expect(near(mesh.rotation.y, p.rot * Math.PI / 180)).toBe(true);
      const mat = mesh.material as MeshStandardMaterial;
      expect(mat.color.equals(new Color(kinds[p.kind]!.colour))).toBe(true);
      expect(mat.side).toBe(0);                                   // FrontSide
      expect([mat.roughness, mat.polygonOffset, mat.polygonOffsetFactor, mat.polygonOffsetUnits]).toEqual([0.85, true, 1, 1]);
      const edge = (mesh.children[0] as LineSegments).material as LineBasicMaterial;
      expect(edge.color.equals(new Color(kinds[p.kind]!.colour).multiplyScalar(0.4))).toBe(true);
    }
    const z = (id: string) => { const p = F.pieces().find(q => q.id === id)!; return [p.z0, p.z1]; };
    expect(z('L1-computer-001')).toEqual([0.75, 1.2]);
    expect(z('L1-printer-001')).toEqual([0.75, 1.05]);
    expect(z('L1-table-001')).toEqual([0, 0.75]);
    expect(z('L1-tv-001')).toEqual([0.9, 1.5]);
    expect(z('L1-seat-001')).toEqual([0, 0.45]);
    expect(z('L2-computer-001')[0]).toBe(0.75);
  });

  it('the level-2 boxes are built at the model level and follow their group when the Build settings move it', () => {
    const { ctx, F } = mount(mini());
    const L2 = ctx.floorByKey.get('L2')!;
    const before = F.meshOf('L2-table-001')!.getWorldPosition(new Vector3()).y;
    ctx.heights.apply({ L1: { level: 0, height: 3.7 }, L2: { level: 5, height: 3.7 } });
    L2.group.updateMatrixWorld(true);
    expect(near(F.meshOf('L2-table-001')!.position.y, 3.7)).toBe(true);
    expect(near(F.meshOf('L2-table-001')!.getWorldPosition(new Vector3()).y - before, 1.3)).toBe(true);
  });
});

describe('Walk colliders and the doorways rule', () => {
  const expected = (m: BuiltModel, floor: string, keep: boolean) => m.furniture!.filter(p => p.floor === floor
    && m.furnitureKinds!.find(k => k.key === p.kind)!.blocks && !(keep && p.approach.length)).map(p => p.id).sort();

  it('Keep doorways clear on (the default): the boxes of kinds that stop you, not the curtain, not the 2 in an approach; off: those 2 too', () => {
    const { ctx, F } = mount(mini());
    const m = mini();
    expect(F.keepDoorways()).toBe(true);
    expect(furnColliders(ctx)).toEqual({ L1: expected(m, 'L1', true), L2: expected(m, 'L2', true) });
    expect(F.setKeepDoorways(false)).toBe(true);
    expect(furnColliders(ctx)).toEqual({ L1: expected(m, 'L1', false), L2: expected(m, 'L2', false) });
    expect(F.pieces().filter(p => p.approach.length).map(p => [p.id, p.blocking])).toEqual([['L1-seat-002', true], ['L2-seat-001', true]]);
    F.setKeepDoorways(true);
    expect(furnColliders(ctx)).toEqual({ L1: expected(m, 'L1', true), L2: expected(m, 'L2', true) });
    expect(F.meshOf('L1-seat-002')!.visible).toBe(true);           // drawn, but no collider
  });

  it('pieces() carries a copy of the approach and blocking; kinds() is the same with the tick on and off', () => {
    const { F } = mount(mini());
    const k0 = JSON.stringify(F.kinds());
    F.pieces().find(p => p.id === 'L1-seat-002')!.approach.push('L1-099');
    expect(F.pieces().find(p => p.id === 'L1-seat-002')!.approach).toEqual(['L1-001', 'L1-002']);
    F.setKeepDoorways(false);
    expect(JSON.stringify(F.kinds())).toBe(k0);
  });

  it('show off: drawn no more and out of the colliders; stops off: drawn, out of the colliders; the curtain stops you once its stops tick is on', () => {
    const { ctx, F } = mount(mini());
    F.setVisible('seat', false);
    expect(F.meshOf('L1-seat-001')!.visible).toBe(false);
    expect(furnColliders(ctx).L1).not.toContain('L1-seat-001');
    F.setVisible('seat', true);
    F.setBlocks('seat', false);
    expect(F.meshOf('L1-seat-001')!.visible).toBe(true);
    expect(furnColliders(ctx).L1).not.toContain('L1-seat-001');
    F.setBlocks('seat', true);
    expect(furnColliders(ctx).L1).toContain('L1-seat-001');
    expect(furnColliders(ctx).L1).not.toContain('L1-curtain-001');
    F.setBlocks('curtain', true);
    expect(furnColliders(ctx).L1).toContain('L1-curtain-001');
    expect([F.setVisible('nothing', true), F.setBlocks('nothing', true)]).toEqual([false, false]);
  });

  it('a level ray at knee height meets a box that stops you and passes one that does not (the readouts see the very arrays Walk uses)', () => {
    const { ctx, F } = mount(mini());
    const t = F.pieces().find(p => p.id === 'L1-tall-cabinet-001')!;   // 2.8 x 0.41 m, turned 90 degrees, at (5, -3)
    const hit = () => ctx.readouts.rayHit('L1', t.x - 1.5, t.y, 0.35, 1, 0, 3);
    expect(hit()?.name).toBe('furn:tall-cabinet:L1-tall-cabinet-001');
    F.setVisible('tall-cabinet', false);
    expect(hit()?.name ?? null).not.toBe('furn:tall-cabinet:L1-tall-cabinet-001');
    F.setVisible('tall-cabinet', true);
    F.setHeight('coffee-table', 300);                               // below the knee ray: stepped over
    const c = F.pieces().find(p => p.id === 'L1-coffee-table-001')!;
    expect(ctx.readouts.rayHit('L1', c.x - 1.2, c.y, 0.35, 1, 0, 2)?.name ?? null).not.toBe('furn:coffee-table:L1-coffee-table-001');
    F.setHeight('coffee-table', 450);
    expect(ctx.readouts.rayHit('L1', c.x - 1.2, c.y, 0.35, 1, 0, 2)?.name).toBe('furn:coffee-table:L1-coffee-table-001');
  });

  it('apply() puts the ticks back after the replay showed every late object', () => {
    const { ctx, F } = mount(mini());
    F.setVisible('plant', false);
    F.setBlocks('seat', false);
    for (const f of ctx.floors) for (const o of f.late) o.visible = true;           // the replay's end
    F.apply();
    expect(F.meshOf('L1-plant-001')!.visible).toBe(false);
    expect(furnColliders(ctx).L1).not.toContain('L1-seat-001');
    expect(furnColliders(ctx).L1).not.toContain('L1-plant-001');
    expect(furnColliders(ctx).L1).toContain('L1-table-001');
  });
});

describe('the legend', () => {
  it('title, note, master tick, Keep doorways clear between the note and the rows, one row per kind in table order, the buttons', () => {
    const { ctx } = mount(mini());
    const m = mini();
    const block = ctx.panel.slot('furniture').querySelector('[data-wt=furniture]')!;
    expect(block).not.toBeNull();
    expect(q(ctx, '[data-wt=furniture-title]').textContent).toBe('Furniture boxes');
    expect(q(ctx, '[data-wt=furniture-note]').textContent).toBe('Type a height in mm for each kind. Walk: boxes stop you; Ghost passes through.');
    const master = q<HTMLInputElement>(ctx, '[data-wt=furniture-all]');
    expect(master.checked).toBe(true);
    expect(master.closest('label')!.textContent).toBe(' show');
    const keep = qa<HTMLInputElement>(ctx, '[data-wt=furniture-keep]');
    expect(keep.length).toBe(1);
    expect(keep[0]!.checked).toBe(true);
    const label = keep[0]!.closest('label')!;
    expect(label.textContent!.trim()).toBe('Keep doorways clear');
    expect(label.title).toBe('2 of the boxes stand in front of a door or a passage. Ticked: Walk is not stopped by them (they stay drawn), so every doorway can be walked through. Unticked: they stop you like any other box.');
    const kids = [...block.children];
    expect(kids.indexOf(q(ctx, '[data-wt=furniture-note]'))).toBeLessThan(kids.indexOf(label));
    expect(kids.indexOf(label)).toBeLessThan(kids.indexOf(q(ctx, '[data-wt=furniture-head]')));
    const rows = qa<HTMLDivElement>(ctx, '[data-wt=furniture-row]');
    expect(rows.map(r => r.getAttribute('data-kind'))).toEqual(m.furnitureKinds!.map(k => k.key));
    m.furnitureKinds!.forEach((k, i) => {
      const r = rows[i]!;
      expect(r.querySelector('[data-wt=kind-label]')!.textContent).toBe(`${k.label} (${k.count})`);
      expect((r.querySelector('[data-wt=kind-label]') as HTMLElement).title).toBe(k.label);
      expect((r.querySelector('[data-wt=kind-swatch]') as HTMLElement).style.background).toBeTruthy();
      expect((r.querySelector('[data-wt=kind-height]') as HTMLInputElement).value).toBe(String(k.height));
      expect((r.querySelector('[data-wt=kind-height]') as HTMLInputElement).type).toBe('text');
      expect((r.querySelector('[data-wt=kind-show]') as HTMLInputElement).checked).toBe(true);
      expect((r.querySelector('[data-wt=kind-stops]') as HTMLInputElement).checked).toBe(k.blocks);
      expect(r.querySelector('[data-wt=kind-show]')!.getAttribute('aria-label')).toBe(`Show ${k.label}`);
      expect(r.querySelector('[data-wt=kind-height]')!.getAttribute('aria-label')).toBe(`${k.label}: height in mm`);
      expect((r.querySelector('[data-wt=kind-height]') as HTMLElement).title).toBe('Height in mm, 10 to 5000');
      expect(r.querySelector('[data-wt=kind-stops]')!.getAttribute('aria-label')).toBe(`${k.label}: Walk stops you`);
    });
    expect(qa(ctx, '[data-wt=furniture-buttons] button').map(b => b.textContent)).toEqual(['Reset heights', 'Save list (CSV)']);
    expect([...q(ctx, '[data-wt=furniture-head]').children].map(s => s.textContent)).toEqual(['', '', 'Kind', 'mm', 'stops']);
    expect(ctx.ui.root.querySelector('style')!.textContent).toContain('[data-wt=furniture-row]');
  });

  it('no "Keep doorways clear" when no piece stands in an approach; a kind nobody uses gets no row; the label counts the pieces, not count', () => {
    const m = mini();
    m.furniture = m.furniture!.map(p => ({ ...p, approach: [], note: '' }));
    m.furnitureKinds!.unshift({ key: 'atm', label: 'ATM / kiosk', colour: '#c0392b', height: 1500, base: 0, onTop: false, support: false, blocks: true, count: 0 });
    m.furnitureKinds!.find(k => k.key === 'seat')!.count = 99;
    const { ctx, F } = mount(m);
    expect(qa(ctx, '[data-wt=furniture-keep]').length).toBe(0);
    expect(row(ctx, 'atm')).toBeNull();
    expect(F.kinds().map(k => k.key)).not.toContain('atm');
    expect(row(ctx, 'seat').querySelector('[data-wt=kind-label]')!.textContent).toBe('Chair / stool (4)');
    expect(F.kinds().find(k => k.key === 'seat')!.count).toBe(4);
    expect(F.setHeight('atm', 600)).toBe(false);
    expect(F.setKeepDoorways(false)).toBe(true);                    // the API still reads and writes the flag
    expect(F.keepDoorways()).toBe(false);
  });

  it('the ticks: show / stops on a row, the master tick (with a mixed state), the doorways tick, through change events', () => {
    const { ctx, F } = mount(mini());
    const click = (el: HTMLInputElement) => { el.checked = !el.checked; el.dispatchEvent(new Event('change', { bubbles: true })); };
    click(row(ctx, 'plant').querySelector('[data-wt=kind-show]')!);
    expect(F.kinds().find(k => k.key === 'plant')!.visible).toBe(false);
    const master = q<HTMLInputElement>(ctx, '[data-wt=furniture-all]');
    expect([master.checked, master.indeterminate]).toEqual([false, true]);
    click(master);
    expect(F.kinds().every(k => k.visible)).toBe(true);
    expect([master.checked, master.indeterminate]).toEqual([true, false]);
    click(master);
    expect(F.kinds().every(k => !k.visible)).toBe(true);
    expect(qa<HTMLInputElement>(ctx, '[data-wt=kind-show]').every(c => !c.checked)).toBe(true);
    expect(Object.values(furnColliders(ctx)).flat()).toEqual([]);
    click(master);
    click(row(ctx, 'seat').querySelector('[data-wt=kind-stops]')!);
    expect(F.kinds().find(k => k.key === 'seat')!.blocks).toBe(false);
    click(q<HTMLInputElement>(ctx, '[data-wt=furniture-keep]'));
    expect(F.keepDoorways()).toBe(false);
    F.setKeepDoorways(true);
    expect(q<HTMLInputElement>(ctx, '[data-wt=furniture-keep]').checked).toBe(true);
  });

  it('typing: focus selects later, a valid number applies as typed, junk is marked, Enter keeps a good number, Escape and leaving go back', () => {
    const { ctx, F, events } = mount(mini());
    const h = box(ctx, 'table');
    const type = (v: string) => { h.value = v; h.dispatchEvent(new Event('input', { bubbles: true })); };
    const height = () => F.kinds().find(k => k.key === 'table')!.height;
    h.focus();
    expect(document.activeElement).toBe(h);
    type('6');
    expect(height()).toBe(750);
    expect(h.hasAttribute('data-bad')).toBe(true);
    type('60');
    expect(height()).toBe(60);
    expect(h.hasAttribute('data-bad')).toBe(false);
    type('600');
    expect(height()).toBe(600);
    expect(h.value).toBe('600');
    expect(h.hasAttribute('data-edited')).toBe(true);
    expect(F.pieces().find(p => p.id === 'L1-computer-001')!.z0).toBe(0.6);
    h.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    expect(document.activeElement).not.toBe(h);
    expect(height()).toBe(600);
    expect(events.filter(e => e.source === 'typed').map(e => e.heights.table)).toEqual([60, 600]);
    // junk: marked while typed, never kept; 9999 passes through 999 (applied as typed) and leaving brings 600 back
    for (const junk of ['9999', 'abc', '4,5', '']) {
      h.focus(); h.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
      if (junk) for (let i = 1; i <= junk.length; i++) type(junk.slice(0, i));        // key by key, as typed
      else type('');                                                                   // the number deleted
      expect(h.hasAttribute('data-bad')).toBe(junk !== '');
      expect(height()).toBe(junk === '9999' ? 999 : 600);                              // 9999 passes through 999, a valid number
      h.blur(); h.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
      expect([h.value, height()]).toEqual(['600', 600]);
      expect(h.hasAttribute('data-bad')).toBe(false);
    }
    // Escape cancels the edit
    h.focus(); h.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    type('123');
    expect(height()).toBe(123);
    h.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect([h.value, height()]).toEqual(['600', 600]);
    expect(F.setHeight('table', 9)).toBe(false);
    expect(F.setHeight('table', 'abc')).toBe(false);
    expect(F.setHeight('table', '640')).toBe(true);
    expect(height()).toBe(640);
  });

  it('Reset heights brings every kind, box and text back to the model heights and clears the edited marks; the ticks stay', () => {
    const { ctx, F, events } = mount(mini());
    F.setHeight('seat', 500); F.setHeight('table', 600); F.setKeepDoorways(false); F.setVisible('plant', false);
    q<HTMLButtonElement>(ctx, '[data-wt=furniture-reset]').click();
    expect(F.kinds().every(k => k.height === k.defaultHeight)).toBe(true);
    expect(qa<HTMLInputElement>(ctx, '[data-wt=kind-height]').map(b => b.value)).toEqual(mini().furnitureKinds!.map(k => String(k.height)));
    expect(qa(ctx, '[data-wt=kind-height][data-edited]').length).toBe(0);
    expect(F.keepDoorways()).toBe(false);
    expect(F.kinds().find(k => k.key === 'plant')!.visible).toBe(false);
    expect(events.at(-1)).toEqual({ heights: {}, source: 'reset' });
    expect(F.pieces().find(p => p.id === 'L1-computer-001')!.z0).toBe(0.75);
  });
});

describe('heights, events and storage', () => {
  it("bus 'furniture': typed, reset, api (setHeights) and tick, each with the kinds that differ from the model's", () => {
    const { F, events } = mount(mini());
    F.setHeight('table', 600);
    F.setVisible('plant', false);
    F.setKeepDoorways(false);
    F.setHeights({ seat: 480, nothing: 3, table: 'x' as unknown as number });
    F.reset();
    expect(events.map(e => [e.source, e.heights])).toEqual([
      ['typed', { table: 600 }], ['tick', { table: 600 }], ['tick', { table: 600 }], ['api', { seat: 480 }], ['reset', {}],
    ]);
  });

  it('setHeights replaces the typed set (missing kinds go back to the model, unknown kinds and bad values ignored); heights() reads it back', () => {
    const { ctx, F } = mount(mini());
    F.setHeight('table', 600);
    F.setHeights({ seat: 480, 'coffee-table': 9 });
    expect(F.heights()).toEqual({ seat: 480 });
    expect(box(ctx, 'table').value).toBe('750');
    expect(box(ctx, 'seat').value).toBe('480');
    expect(box(ctx, 'seat').hasAttribute('data-edited')).toBe(true);
  });

  it("local mode: typed heights are stored under ctx.options.storageKey (<prefix><photoName>:<stamp>), only the changed ones, then read back", () => {
    const { ctx, F } = mount(mini());
    expect(ctx.options.storageKey).toBe('walkthrough-furniture-heights:Fixture:abcdef123456');
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
    F.setHeight('table', 600); F.setHeight('coffee-table', 420);
    expect(localStorage.getItem(ctx.options.storageKey)).toBe('{"table":600,"coffee-table":420}');
    F.setKeepDoorways(false);
    expect(localStorage.getItem(ctx.options.storageKey)).toBe('{"table":600,"coffee-table":420,"keepDoorways":false}');
    const again = mount(mini());
    expect(again.F.heights()).toEqual({ table: 600, 'coffee-table': 420 });
    expect(again.F.keepDoorways()).toBe(false);
    expect(box(again.ctx, 'table').value).toBe('600');
    expect(again.F.pieces().find(p => p.id === 'L1-computer-001')!.z0).toBe(0.6);
    again.F.reset();
    expect(localStorage.getItem(ctx.options.storageKey)).toBe('{"keepDoorways":false}');
    again.F.setKeepDoorways(true);
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
  });

  it('local mode over saved heights: the starting heights are the saved ones; the model value typed over one is stored and holds after a reload', () => {
    const { ctx, F } = mount(mini(), undefined, { table: 600, nothing: 300, seat: 4 });
    expect(F.heights()).toEqual({ table: 600 });
    expect(F.kinds().find(k => k.key === 'table')!.defaultHeight).toBe(750);
    expect(box(ctx, 'table').hasAttribute('data-edited')).toBe(true);
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
    F.setHeight('table', 750);                                         // the model's value typed over the saved 600
    expect(F.heights()).toEqual({});
    expect(localStorage.getItem(ctx.options.storageKey)).toBe('{"table":750}');
    const again = mount(mini(), undefined, { table: 600 });
    expect(again.F.heights()).toEqual({});
    again.F.setHeight('table', 600);                                   // the saved value typed back: nothing to keep
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
  });

  it("local mode: Reset goes back to the file's heights (the saved ones over the model's), not the model's, and stores nothing (fix step)", () => {
    const { ctx, F, events } = mount(mini(), undefined, { table: 600 });
    F.setHeight('table', 500); F.setHeight('seat', 480);
    expect(JSON.parse(localStorage.getItem(ctx.options.storageKey)!)).toEqual({ table: 500, seat: 480 });
    F.reset();
    expect(F.heights()).toEqual({ table: 600 });
    expect(box(ctx, 'table').value).toBe('600');
    expect(box(ctx, 'seat').value).toBe(String(mini().furnitureKinds!.find(k => k.key === 'seat')!.height));
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
    expect(events.at(-1)).toEqual({ heights: { table: 600 }, source: 'reset' });
    expect(mount(mini(), undefined, { table: 600 }).F.heights()).toEqual({ table: 600 });   // after a reload too
  });

  it("host mode (staff app): Reset goes back to the model's heights over saved ones", () => {
    const { F, events } = mount(mini(), { furnitureHeights: 'host' }, { table: 600 });
    expect(F.heights()).toEqual({ table: 600 });
    F.reset();
    expect(F.heights()).toEqual({});
    expect(events.at(-1)).toEqual({ heights: {}, source: 'reset' });
  });

  it('host mode: no heights stored (only the doorways tick), stored heights not read, the saved heights are the start', () => {
    localStorage.setItem('walkthrough-furniture-heights:Fixture:abcdef123456', '{"table":640,"keepDoorways":false}');
    const { ctx, F } = mount(mini(), { furnitureHeights: 'host' }, { seat: 480 });
    expect(F.heights()).toEqual({ seat: 480 });
    expect(F.keepDoorways()).toBe(false);
    F.setKeepDoorways(true);
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
    F.setHeight('table', 600);
    expect(localStorage.getItem(ctx.options.storageKey)).toBeNull();
    F.setKeepDoorways(false);
    expect(localStorage.getItem(ctx.options.storageKey)).toBe('{"keepDoorways":false}');
  });

  it('a blocked storage: the boxes, the typing, Reset and the doorways tick still work', () => {
    // as a private window with site data off: reading window.localStorage throws (test_boxes.mjs did the same)
    const own = Object.getOwnPropertyDescriptor(window, 'localStorage');
    let reads = 0;
    Object.defineProperty(window, 'localStorage', { configurable: true, get() { reads++; throw new DOMException('blocked for the test', 'SecurityError'); } });
    let mounted: ReturnType<typeof mount>;
    try { mounted = mount(mini()); } finally { /* restored below, after the calls that write */ }
    const { F } = mounted;
    expect(F.setHeight('table', 640)).toBe(true);
    expect(F.pieces().find(p => p.id === 'L1-computer-001')!.z0).toBe(0.64);
    F.setKeepDoorways(false);
    F.reset();
    expect(F.heights()).toEqual({});
    expect(reads).toBeGreaterThan(2);
    if (own) Object.defineProperty(window, 'localStorage', own); else delete (window as unknown as Record<string, unknown>).localStorage;
    expect(() => localStorage.getItem('x')).not.toThrow();
  });
});

describe('the family list', () => {
  it('csv() is furnitureCsv with the heights typed in; saveCsv downloads BOM + csv() as <photoName>_furniture_list.csv', async () => {
    const { ctx, F } = mount(mini());
    F.setHeight('table', 640);
    expect(F.csv()).toBe(furnitureCsv(mini(), { table: 640 }));
    expect(F.saveCsv()).toBe(F.csv());
    expect(ctx.kit.downloads.length).toBe(1);
    const dl = ctx.kit.downloads[0]!;
    expect(dl.fileName).toBe('Fixture_furniture_list.csv');
    expect(dl.blob.type).toMatch(/text\/csv;charset=utf-8/i);
    const bytes = new Uint8Array(await dl.blob.arrayBuffer());
    expect([...bytes.slice(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
    expect(new TextDecoder('utf-8', { ignoreBOM: true }).decode(bytes)).toBe('﻿' + F.csv());
    q<HTMLButtonElement>(ctx, '[data-wt=furniture-save]').click();
    expect(ctx.kit.downloads.length).toBe(2);
  });
  it('nodownload: nothing is downloaded, csv() still works', () => {
    const { ctx, F } = mount(mini(), { noDownload: true });
    expect(F.saveCsv().length).toBeGreaterThan(1000);
    q<HTMLButtonElement>(ctx, '[data-wt=furniture-save]').click();
    expect(ctx.kit.downloads.length).toBe(0);
  });
  it('the bank v2: csv() equals the prototype CSV (no BOM)', () => {
    const { F } = mount(loadModel('bank-v2'));
    const file = readText(path.join(APP, 'fixtures/csv/bank-v2.csv'));
    expect('﻿' + F.csv()).toBe(file);
  });
});

describe('the leniency of DESIGN.md 5.6', () => {
  const broken = (name: string) => JSON.parse(readText(path.join(APP, 'fixtures/models/broken/cross', `furniture-${name}.json`))) as BuiltModel;
  it('unknown kind or floor: left out with a warning (no row, no box); a missing support: on its kind base', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const m = mini();
    const seat = m.furniture!.find(p => p.id === 'L1-seat-001')!;
    m.furniture!.find(p => p.id === 'L1-computer-001')!.on = 'L1-no-such-table';
    m.furniture!.push({ ...seat, id: 'L9-seat-001', floor: 'L9' }, { ...seat, id: 'L1-sofa-001', kind: 'sofa' });
    const { ctx, F } = mount(m);
    expect(F.pieces().length).toBe(17);
    expect(F.pieces().map(p => p.id)).not.toContain('L9-seat-001');
    expect(F.meshOf('L1-sofa-001')).toBeNull();
    expect(F.pieces().find(p => p.id === 'L1-computer-001')!.z0).toBe(0);
    expect(qa(ctx, '[data-wt=furniture-row]').length).toBe(mini().furnitureKinds!.length);
    expect(warn.mock.calls.map(c => c.join(' '))).toEqual([
      'furniture box left out (unknown kind or level): L9-seat-001', 'furniture box left out (unknown kind or level): L1-sofa-001']);
  });
  it('the shared broken corpus (fixtures/models/broken/cross/furniture-*): installs, does what furniture_boxes.js did', () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const uk = mount(broken('unknown-kind'));
    expect(uk.F.meshOf('L1-atm-001')).toBeNull();
    const ms = mount(broken('missing-support'));
    expect(ms.F.pieces().find(p => p.id === 'L1-computer-001')!.z0).toBe(0);
    const ua = mount(broken('unknown-approach'));
    const p28 = broken('unknown-approach').furniture![28]!;
    expect(ua.F.pieces().find(p => p.id === p28.id)!.approach).toEqual(p28.approach);
    expect(ua.F.pieces().find(p => p.id === p28.id)!.blocking).toBe(false);       // kept as it is: the doorways rule uses the list
    const ct = mount(broken('count'));
    expect(ct.F.kinds()[0]!.count).toBe(3);
    expect(row(ct.ctx, 'atm').querySelector('[data-wt=kind-label]')!.textContent).toBe('ATM / kiosk (3)');
  });
});

describe('the hover label', () => {
  function setup(F: FurnitureApi, ctx: TestContext) {
    const rect = { left: 0, top: 0, right: 1400, bottom: 880, width: 1400, height: 880, x: 0, y: 0, toJSON: () => ({}) } as DOMRect;
    vi.spyOn(ctx.canvas, 'getBoundingClientRect').mockReturnValue(rect);
    vi.spyOn(ctx.ui.root, 'getBoundingClientRect').mockReturnValue(rect);
    ctx.camera.position.set(0, 40, 8);                             // from above (the default view looks over the mini model's east wall)
    ctx.camera.lookAt(0, 0, 0);
    ctx.scene.updateMatrixWorld(true);
    ctx.camera.updateMatrixWorld();
    const at = (x: number, y: number, z: number) => { const v = new Vector3(x, y, z).project(ctx.camera); return [(v.x + 1) / 2 * 1400, (1 - v.y) / 2 * 880] as const; };
    const tip = q<HTMLDivElement>(ctx, '[data-wt=furniture-tip]');
    const move = async (x: number, y: number, o: { buttons?: number; pointerType?: string } = {}) => {
      ctx.canvas.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y, buttons: o.buttons ?? 0, pointerType: o.pointerType ?? 'mouse', bubbles: true }));
      await new Promise(r => setTimeout(r, 80));
      return tip.style.display === 'block' ? tip.textContent : null;
    };
    // a spot on the top of a box, `along` m from its middle along its long axis (the table's edge: the computer stands in its middle)
    const top = (id: string, along = 0) => {
      const p = F.pieces().find(q => q.id === id)!, r = p.rot * Math.PI / 180;
      return at(p.x + along * Math.cos(r), ctx.floorByKey.get(p.floor)!.modelLevel + p.z1, -(p.y + along * Math.sin(r)));
    };
    return { tip, move, top, at };
  }

  it('Orbit: kind, family, size, floor; "from" for a raised box; "does not stop you" in an approach while the tick is on; nothing over the sky', async () => {
    const m = mini();
    const { ctx, F } = mount(m);
    const { move, top, tip } = setup(F, ctx);
    const at = top('L2-computer-001');
    const comp = await move(...at);
    expect(comp).toContain('Computer / monitor');
    expect(comp).toContain('0.74 × 0.43 × 0.45 m, from 0.75 m · Level 2');
    // at the pointer + 14 / + 18 px, kept inside the root (4 px from its top left, 8 px from its right and bottom edge)
    const size = ctx.size(), w = tip.offsetWidth, h = tip.offsetHeight;
    const px = (v: string) => { expect(v).toMatch(/px$/); return parseFloat(v); };      // the CSSOM keeps 6 decimals
    expect(px(tip.style.left)).toBeCloseTo(Math.max(4, Math.min(at[0] + 14, size.width - w - 8)), 4);
    expect(px(tip.style.top)).toBeCloseTo(Math.max(4, Math.min(at[1] + 18, size.height - h - 8)), 4);
    expect(tip.parentElement).toBe(ctx.ui.root);
    const seat2 = await move(...top('L1-seat-002'));
    // L1-seat-002 is on level 1, under level 2's floor plate in a view of both floors: hidden
    expect(seat2).toBeNull();
    ctx.visibility.setFloorMode('L1');
    const s2 = await move(...top('L1-seat-002'));
    expect(s2).toContain('Chair / stool');
    expect(s2).toContain('mollie_chair_a685_revit - A685 2');
    expect(s2).toContain('does not stop you: in the approach of L1-001, L1-002');
    F.setKeepDoorways(false);
    const s2off = await move(...top('L1-seat-002'));
    expect(s2off).toContain('Chair / stool');
    expect(s2off).not.toContain('does not stop you');
    F.setVisible('seat', false);
    expect(await move(...top('L1-seat-002'))).toBeNull();
    expect(await move(5, 5)).toBeNull();
  });

  it('nothing while dragging, for touch, in Walk or Ghost; a mode change hides it at once', async () => {
    const { ctx, F } = mount(mini());
    const { move, top, tip } = setup(F, ctx);
    ctx.visibility.setFloorMode('L2');
    expect(await move(...top('L2-table-001', -0.55))).toContain('Table / desk');
    expect(await move(...top('L2-table-001', -0.55), { buttons: 1 })).toBeNull();
    expect(await move(...top('L2-table-001', -0.55), { pointerType: 'touch' })).toBeNull();
    expect(await move(...top('L2-table-001', -0.55))).toContain('Table / desk');
    ctx.modes.state.mode = 'walk';
    ctx.bus.emit('mode', { mode: 'walk', floor: 'L1' });
    expect(tip.style.display).toBe('none');
    expect(await move(...top('L2-table-001', -0.55))).toBeNull();
    ctx.modes.state.mode = 'orbit';
    expect(await move(...top('L2-table-001', -0.55))).toContain('Table / desk');
    ctx.canvas.dispatchEvent(new PointerEvent('pointerleave'));
    expect(tip.style.display).toBe('none');
  });

  it('the label is text: a family with markup stays text', async () => {
    const m = mini();
    m.furniture!.find(p => p.id === 'L2-table-001')!.family = '<img src=x onerror="window.__pwned = 1">';
    m.furnitureKinds!.find(k => k.key === 'table')!.label = '<b>Table</b>';
    const { ctx, F } = mount(m);
    const { move, top, tip } = setup(F, ctx);
    ctx.visibility.setFloorMode('L2');
    const t = await move(...top('L2-table-001', -0.55));
    expect(t).toContain('<img src=x onerror="window.__pwned = 1">');
    expect(tip.querySelector('img')).toBeNull();
    expect(tip.querySelector('b')!.textContent).toBe('<b>Table</b>');
    expect(row(ctx, 'table').querySelector('b')).toBeNull();
    expect(row(ctx, 'table').querySelector('[data-wt=kind-label]')!.textContent).toBe('<b>Table</b> (3)');
  });
});

describe('step BX (docs/boxes/DESIGN.md 2.1, 8.2): without editBoxes and without deleted boxes nothing changed', () => {
  it('the legend, the root and the scene are the same with editBoxes false, with it left out, and with an empty or missing pieceEdits', () => {
    const look = (options: Partial<ResolvedOptions> | undefined, edits?: unknown) => {
      const ctx = makeTestContext({ model: mini(), stamp: 'abcdef123456', options });
      if (edits !== undefined) ctx.project.pieceEdits = edits as never;
      live.push(ctx);
      const F = installFurniture(ctx)!;
      return {
        legend: ctx.panel.slot('furniture').innerHTML,
        rootKids: [...ctx.ui.root.children].map(c => c.getAttribute('data-wt') ?? c.tagName),
        css: ctx.ui.root.querySelector('style')!.textContent,
        sceneKids: ctx.scene.children.map(c => c.name),
        late: ctx.floors.map(f => f.late.length), colliders: furnColliders(ctx), kinds: F.kinds(), pieces: F.pieces(), csv: F.csv(),
        cursor: ctx.canvas.style.cursor,
      };
    };
    const plain = look(undefined);
    expect(look({ editBoxes: false })).toEqual(plain);
    expect(look({}, {})).toEqual(plain);
    expect(look({ editBoxes: false }, null)).toEqual(plain);
    expect(plain.legend).not.toMatch(/furniture-edit-hint|furniture-removed|data-empty/);
    expect(plain.rootKids.filter(k => /^box|^boxes/.test(k))).toEqual([]);
    expect(plain.sceneKids).not.toContain('furniture-selection');
    // the staff app's version page (editBoxes) with nothing deleted: only the edit hint is added to the legend
    const staff = look({ editBoxes: true });
    expect(staff.legend.replace(/<div data-wt="furniture-edit-hint">[^<]*<\/div>/, '')).toBe(plain.legend);
    expect([staff.kinds, staff.pieces, staff.csv, staff.late, staff.colliders]).toEqual([plain.kinds, plain.pieces, plain.csv, plain.late, plain.colliders]);
  });
});

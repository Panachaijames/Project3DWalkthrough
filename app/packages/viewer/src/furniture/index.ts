// installFurniture: the port of furniture/furniture_boxes.js (DESIGN.md 5.6, 11.2, 11.5, 12, 13). Owner: builder C.
//   One coloured box per piece (boxes.ts), a legend with a height text box per kind (legend.ts), Walk stopped by the boxes
//   (Ghost is not), the doorways rule, the hover label in Orbit (hover.ts), the family list as CSV (logic.ts), the typed
//   heights and the doorways tick kept per browser (storage.ts). Returns null when the model has no furniture (nothing added).
// Heights. The starting heights are the model's, then project.heights (the saved ones) over them, then (furnitureHeights
// 'local' only) what this browser stored; Reset goes back to the model's in the staff app ('host') and to the starting
// heights, the file's own, in the offline file ('local'; fix step). Every change goes out on bus
// 'furniture' with its source ('typed', 'reset', 'api' = setHeights, 'tick' = the show / stops / doorways ticks); viewer.ts
// turns only 'typed' and 'reset' into the public heightschange.
// Leniency (DESIGN.md 5.6): a piece whose kind or floor is unknown is left out with a warning; a piece whose `on` names no
// piece stands on its kind's base; approach ids are kept as they are; a kind's count is ignored (the legend counts pieces).
// Deleted boxes (docs/boxes/DESIGN.md 2.4 - 2.8; step BX). A deleted box keeps its mesh and its item: it is hidden, never a
// collider, out of its floor's 'late' list, out of the CSV and out of its kind's count. The deleted set starts from
// project.pieceEdits (read leniently, closed) and is always closed: what stands on a deleted box is deleted with it
// (logic.ts closeRemoved). Every change goes out on bus 'pieces' with its source ('removed', 'restored', 'api' =
// setPieceEdits); viewer.ts turns only 'removed' and 'restored' into the public boxeschange. Deletes, restores and Restore
// all of this visit can be undone (a stack of the ids each changed; setPieceEdits clears it). With options.editBoxes (the
// staff app's version page) boxes can be selected and deleted (select.ts) and restored (restore.ts); without it there is
// no control, and the legend is built from the live pieces only.
import type { FurnitureApi, FurnitureKindView, FurniturePieceView, HeightMap, InstallFurniture, PieceEditMap } from '../contracts';
import { makeBoxes, placeBox, restoreLook, setRemoved, syncKind } from './boxes';
import { FURNITURE_CSS } from './css';
import { installHover } from './hover';
import { makeLegend } from './legend';
import {
  MAX_H, MIN_H, closeRemoved, csvFileName, csvOrder, furnitureCsv, furnitureData, groupsOf, heightFromData, removedIdsOf, stopsWalk,
  undersideOf, wholeMm,
} from './logic';
import { makePicker } from './pick';
import { installSelect } from './select';
import { loadStored, readStoredState, saveStored, writeStoredState } from './storage';
import type { EditEvent, FurnitureState, ItemState, KindState, LegendActions, PieceDraft, UndoEntry } from './types';

const hasOwn = (o: object, key: string) => Object.prototype.hasOwnProperty.call(o, key);

export const installFurniture: InstallFurniture = ctx => {
  const model = ctx.model;

  // ---------------------------------------------------------------- kinds and pieces
  const allKinds: KindState[] = (model.furnitureKinds ?? []).map(k => ({
    key: k.key, label: k.label, colour: k.colour, height: wholeMm(k.height), base: wholeMm(k.base), defaultHeight: wholeMm(k.height),
    visible: true, blocks: k.blocks !== false, items: [],
  }));
  const kindOf = new Map(allKinds.map(k => [k.key, k]));
  const drafts: PieceDraft[] = [];
  for (const d of model.furniture ?? []) {
    const kind = kindOf.get(d.kind), fl = ctx.floorByKey.get(d.floor);
    if (!kind || !fl) { console.warn('furniture box left out (unknown kind or level):', d.id); continue; }
    drafts.push({ d, kind, fl, approach: Array.isArray(d.approach) ? d.approach.map(String) : [] });
  }
  if (!drafts.length) return null;
  const used = new Set(drafts.map(p => p.kind));
  const kinds = allKinds.filter(k => used.has(k));                   // a kind nobody uses gets no row
  // the boxes, kind by kind; each item is made with its mesh (makeBoxes), the items in the model's order
  const items: ItemState[] = makeBoxes(ctx, kinds, drafts);
  const itemOf = new Map<string, ItemState>(items.map(p => [p.d.id, p]));
  const inApproach = items.filter(p => p.approach.length);            // the pieces that stand where a door or a passage is walked through
  let keepDoorways = true;                                            // 'Keep doorways clear': those pieces do not stop Walk

  // ---------------------------------------------------------------- the deleted boxes the project carries
  const editBoxes = ctx.options.editBoxes === true;
  const standing = items.map(p => p.d);                               // what the closure rule reads (id, on)
  const rank = new Map(csvOrder(model, furnitureData(model)).map((d, i) => [d.id, i]));
  // the furniture list's order (floor, kind, id): the order of the edits map and of the Restore list
  const listed = [...items].sort((a, b) => (rank.get(a.d.id) ?? 0) - (rank.get(b.d.id) ?? 0));
  const closed = (ids: Iterable<string>) => closeRemoved([...ids].filter(id => itemOf.has(id)), standing);   // unknown ids are ignored
  for (const id of closed(removedIdsOf(ctx.project.pieceEdits))) setRemoved(itemOf.get(id)!, true);
  const liveCount = (k: KindState) => k.items.reduce((n, p) => n + (p.removed ? 0 : 1), 0);
  const removedIds = () => new Set(items.filter(p => p.removed).map(p => p.d.id));
  const pieceEdits = (): PieceEditMap => Object.fromEntries(listed.filter(p => p.removed).map(p => [p.d.id, { removed: true as const }]));
  // the client's file (no editBoxes): the deletions are fixed when the file loads, so a kind without a live piece gets no row
  const legendKinds = editBoxes ? kinds : kinds.filter(k => liveCount(k) > 0);

  // ---------------------------------------------------------------- the starting heights, and what this browser kept
  const saved = ctx.project.heights ?? {};
  for (const k of kinds) {
    const v = hasOwn(saved, k.key) ? heightFromData(saved[k.key]) : null;
    if (v !== null) k.height = v;
  }
  const baseline: HeightMap = Object.fromEntries(kinds.map(k => [k.key, k.height]));
  const mode = ctx.options.furnitureHeights, storeKey = ctx.options.storageKey;
  const stored = readStoredState(loadStored(storeKey), (model.furnitureKinds ?? []).filter(k => kindOf.get(k.key)?.items.length));
  if (mode === 'local') for (const k of kinds) if (hasOwn(stored.heights, k.key)) k.height = stored.heights[k.key]!;
  if (!stored.keepDoorways) keepDoorways = false;
  const persist = () => {
    const now: HeightMap = Object.fromEntries(kinds.map(k => [k.key, k.height]));
    saveStored(storeKey, writeStoredState({ heights: now, keepDoorways }, mode, baseline));
  };

  // ---------------------------------------------------------------- the boxes
  const pieceById = new Map(items.map(p => [p.d.id, p.d]));
  const under = (p: ItemState) => undersideOf(p.d, pieceById, kind => kindOf.get(kind)!.height, kind => kindOf.get(kind)!.base);
  const placeAll = () => { for (const p of items) placeBox(p, under(p)); };
  const stops = (p: ItemState) => !p.removed && stopsWalk(p.kind, p.approach, keepDoorways);
  const sync = (k: KindState) => syncKind(k, stops);

  // ---------------------------------------------------------------- what changed goes out on the bus
  const heights = (): HeightMap => Object.fromEntries(kinds.filter(k => k.height !== k.defaultHeight).map(k => [k.key, k.height]));
  const changed = (source: 'typed' | 'reset' | 'api' | 'tick') => ctx.bus.emit('furniture', { heights: heights(), source });

  // ---------------------------------------------------------------- deleting and restoring
  let undoStack: UndoEntry[] = [], restoredAll = 0;
  const editListeners: ((e: EditEvent) => void)[] = [];
  // the build replay owns the late objects' visibility while it runs; its closing apply() shows what is back
  const replayRunning = () => { const phase = ctx.replay?.phase; return phase === 'settings' || phase === 'play'; };
  /**
   * The deleted set becomes `want`, closed. Returns the ids whose state changed (`first` first, then the list's order);
   * nothing changed and not 'api': nothing happens. `push`: the change is an undo step.
   */
  function setRemovedIds(want: Iterable<string>, source: EditEvent['source'], o: { push?: boolean; all?: boolean; first?: string } = {}): string[] {
    const to = closed(want), ids: string[] = [];
    for (const p of listed) if (p.removed !== to.has(p.d.id)) { setRemoved(p, !p.removed); ids.push(p.d.id); }
    if (!ids.length && source !== 'api') return ids;
    if (o.first !== undefined && ids.includes(o.first)) { ids.splice(ids.indexOf(o.first), 1); ids.unshift(o.first); }
    const running = replayRunning();
    for (const k of kinds) syncKind(k, stops, running);
    let entry: UndoEntry | null = null;
    if (source === 'api') undoStack = [];                             // remote changes make the inverses ambiguous
    else if (o.push) undoStack.push(entry = { ids: ids.slice(), dir: source, all: o.all === true });
    restoredAll = source === 'restored' && o.push && o.all ? ids.length : 0;
    for (const k of legendKinds) legend.showRow(k, true);
    legend.showKeep(); legend.showRemoved();
    ctx.bus.emit('pieces', { pieceEdits: pieceEdits(), source });
    const event: EditEvent = { source, ids, entry, all: o.all === true };
    for (const fn of editListeners.slice()) fn(event);
    return ids;
  }
  /** The top of a deleted piece's group: its support while that is deleted too (supports never stand on anything: 3 steps at most). */
  const topOf = (p: ItemState): ItemState => {
    let at = p;
    for (let i = 0; i < 3; i++) {
      const s = at.d.on ? itemOf.get(at.d.on) : undefined;
      if (!s || !s.removed) break;
      at = s;
    }
    return at;
  };

  const state: FurnitureState = {
    kinds, kindOf, items, itemOf, inApproach, keepDoorways: () => keepDoorways, stops,
    editBoxes, legendKinds, liveCount, removedIds,
    groups: () => groupsOf(removedIds(), listed.map(p => p.d)),
    undoTop: () => undoStack.at(-1) ?? null,
    restoredAll: () => restoredAll,
    onEdit: fn => { editListeners.push(fn); },
    select: null,
  };
  const actions: LegendActions = {
    setHeight(key, mm, keepText) {
      const k = kindOf.get(key), v = wholeMm(Number(mm));
      if (!k || !k.items.length || !(v >= MIN_H && v <= MAX_H)) return false;
      k.height = v;
      placeAll(); persist(); legend.showRow(k, keepText); changed('typed');
      return true;
    },
    setVisible(key, on) {
      const k = kindOf.get(key);
      if (!k || !k.items.length) return false;
      k.visible = !!on; sync(k); legend.showRow(k, true); changed('tick');
      return true;
    },
    setBlocks(key, on) {
      const k = kindOf.get(key);
      if (!k || !k.items.length) return false;
      k.blocks = !!on; sync(k); legend.showRow(k, true); changed('tick');
      return true;
    },
    setAllVisible(on) {
      for (const k of kinds) { k.visible = !!on; sync(k); legend.showRow(k, true); }
      changed('tick');
    },
    setKeepDoorways(on) {
      keepDoorways = !!on; kinds.forEach(sync); legend.showKeep(); persist(); changed('tick');
      return true;
    },
    reset() {                                                       // the heights only: the ticks stay as they are
      // the staff app ('host'): the model's heights (then saved); the offline file ('local'): the heights the file
      // carries, the model's with the saved ones over them, so a client's Reset never throws the owner's heights away
      // (fix step, review finding "adversarial" 7; with no saved heights both are the model's, as the prototypes')
      for (const k of kinds) k.height = mode === 'local' ? baseline[k.key]! : k.defaultHeight;
      placeAll(); persist(); for (const k of kinds) legend.showRow(k); changed('reset');
    },
    saveCsv() {
      const text = csv();
      if (ctx.options.noDownload) return text;
      // UTF-8 with a byte-order mark: Excel then reads Thai text right
      const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), text], { type: 'text/csv;charset=utf-8' });
      ctx.options.download(blob, csvFileName(model.photoName));
      return text;
    },
    removePiece(id) {                                               // the box and what stands on it
      const p = itemOf.get(id);
      if (!p || p.removed) return [];
      return setRemovedIds([...removedIds(), id], 'removed', { push: true, first: id });
    },
    restorePiece(id) {                                              // the box's group: its top and every deleted piece on it
      const p = itemOf.get(id);
      if (!p || !p.removed) return [];
      const top = topOf(p), group = closeRemoved([top.d.id], standing), now = removedIds();
      return setRemovedIds([...now].filter(x => !group.has(x)), 'restored', { push: true, first: top.d.id });
    },
    restoreAll() { setRemovedIds([], 'restored', { push: true, all: true }); },
    undo() {                                                        // the inverse of the last step, then the map closed again
      const step = undoStack.pop();
      if (!step) return false;
      const now = removedIds();
      if (step.dir === 'removed') for (const id of step.ids) now.delete(id); else for (const id of step.ids) now.add(id);
      setRemovedIds(now, step.dir === 'removed' ? 'restored' : 'removed', { all: step.all, first: step.ids[0] });
      return true;
    },
  };
  const csv = () => furnitureCsv(model, Object.fromEntries(kinds.map(k => [k.key, k.height])), removedIds());

  ctx.ui.addStyle(FURNITURE_CSS);
  const legend = makeLegend(ctx, state, actions);
  ctx.panel.slot('furniture').append(legend.el);
  const picker = makePicker(ctx, state);
  const hover = installHover(ctx, state, picker);
  if (editBoxes) installSelect(ctx, state, actions, picker, hover);

  placeAll(); kinds.forEach(sync); for (const k of kinds) legend.showRow(k); legend.showKeep(); legend.showRemoved();

  const api: FurnitureApi = {
    // visible / blocks are the kind's ticks; blocking is what Walk does now (the box is in its floor's colliders)
    pieces: () => items.map((p): FurniturePieceView => ({
      ...p.d, approach: p.approach.slice(), z0: p.z0mm / 1000, z1: (p.z0mm + p.kind.height) / 1000,
      visible: p.kind.visible && !p.removed, blocks: p.kind.blocks, blocking: stops(p),
      ...(p.removed ? { removed: true as const } : {}),              // only on a deleted box
    })),
    kinds: () => kinds.map((k): FurnitureKindView => ({
      key: k.key, label: k.label, colour: k.colour, height: k.height, defaultHeight: k.defaultHeight, count: liveCount(k),
      visible: k.visible, blocks: k.blocks,
    })),
    setHeight: (key, mm) => actions.setHeight(key, Number(mm)),
    setVisible: (key, on) => actions.setVisible(key, on),
    setBlocks: (key, on) => actions.setBlocks(key, on),
    setKeepDoorways: on => actions.setKeepDoorways(on),
    keepDoorways: () => keepDoorways,
    reset: () => actions.reset(),
    csv,
    saveCsv: () => actions.saveCsv(),
    meshOf: id => itemOf.get(id)?.mesh ?? null,
    apply: () => { kinds.forEach(sync); kinds.forEach(restoreLook); },
    heights,
    setHeights(h) {                                                 // the map replaces the typed set; missing kinds go back to the model's
      const given = h ?? {};
      for (const k of kinds) {
        const v = hasOwn(given, k.key) ? heightFromData(given[k.key]) : null;
        k.height = v ?? k.defaultHeight;
      }
      placeAll(); persist(); for (const k of kinds) legend.showRow(k); changed('api');
    },
    pieceEdits,
    setPieceEdits(e) { setRemovedIds(removedIdsOf(e), 'api'); },    // the map replaces the deleted set; odd values and unknown ids ignored
    removePiece: id => actions.removePiece(id),
    restorePiece: id => actions.restorePiece(id),
    restoreAll: () => actions.restoreAll(),
  };
  return api;
};

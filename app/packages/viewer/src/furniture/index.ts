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
import type { FurnitureApi, FurnitureKindView, FurniturePieceView, HeightMap, InstallFurniture } from '../contracts';
import { makeBoxes, placeBox, syncKind } from './boxes';
import { FURNITURE_CSS } from './css';
import { installHover } from './hover';
import { makeLegend } from './legend';
import { MAX_H, MIN_H, csvFileName, furnitureCsv, heightFromData, stopsWalk, undersideOf, wholeMm } from './logic';
import { loadStored, readStoredState, saveStored, writeStoredState } from './storage';
import type { FurnitureState, ItemState, KindState, LegendActions, PieceDraft } from './types';

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
  const stops = (p: ItemState) => stopsWalk(p.kind, p.approach, keepDoorways);
  const sync = (k: KindState) => syncKind(k, stops);

  // ---------------------------------------------------------------- what changed goes out on the bus
  const heights = (): HeightMap => Object.fromEntries(kinds.filter(k => k.height !== k.defaultHeight).map(k => [k.key, k.height]));
  const changed = (source: 'typed' | 'reset' | 'api' | 'tick') => ctx.bus.emit('furniture', { heights: heights(), source });

  const state: FurnitureState = { kinds, kindOf, items, itemOf, inApproach, keepDoorways: () => keepDoorways, stops };
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
  };
  const csv = () => furnitureCsv(model, Object.fromEntries(kinds.map(k => [k.key, k.height])));

  ctx.ui.addStyle(FURNITURE_CSS);
  const legend = makeLegend(ctx, state, actions);
  ctx.panel.slot('furniture').append(legend.el);
  installHover(ctx, state);

  placeAll(); kinds.forEach(sync); for (const k of kinds) legend.showRow(k); legend.showKeep();

  const api: FurnitureApi = {
    // visible / blocks are the kind's ticks; blocking is what Walk does now (the box is in its floor's colliders)
    pieces: () => items.map((p): FurniturePieceView => ({
      ...p.d, approach: p.approach.slice(), z0: p.z0mm / 1000, z1: (p.z0mm + p.kind.height) / 1000, visible: p.kind.visible,
      blocks: p.kind.blocks, blocking: stops(p),
    })),
    kinds: () => kinds.map((k): FurnitureKindView => ({
      key: k.key, label: k.label, colour: k.colour, height: k.height, defaultHeight: k.defaultHeight, count: k.items.length,
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
    apply: () => { kinds.forEach(sync); },
    heights,
    setHeights(h) {                                                 // the map replaces the typed set; missing kinds go back to the model's
      const given = h ?? {};
      for (const k of kinds) {
        const v = hasOwn(given, k.key) ? heightFromData(given[k.key]) : null;
        k.height = v ?? k.defaultHeight;
      }
      placeAll(); persist(); for (const k of kinds) legend.showRow(k); changed('api');
    },
  };
  return api;
};

// The plan canvas module (docs/upload/DESIGN.md U-12.1, U-14.2; WORK_BREAKDOWN U6 / U7). The exported signatures were
// written by the scaffold U0 and are FINAL: U6 imports from '@/plan'; U7 wrote the bodies, in private files:
//   decode.ts      the PlanGeometry decoded once into typed arrays, in local quanta from `origin`; keys, subtrees, blocks
//   paths.ts       one path per (layer, type), built once, in local quanta
//   view.ts        pan / zoom at the pointer / fit; the canvas transform (quanta -> device pixels)
//   hit.ts         the 2 m grid index; nearest item; box inside / touching; the pick modes item, block, layer-in-box
//   colours.ts     colours per role (`other`, `ignore` faint), per part kind, opening kind, flag severity
//   overlay.ts     the overlay, flags and diff converted to the local frame once when they arrive
//   draw.ts        one frame; controller.ts the canvas, caches, input, hover tooltip, redraw on demand
//   areas.ts       proposeAreas; near.ts nearLayers; PlanCanvas.tsx the React component
// Drawing text (layer names, keys, room names, flag titles) is untrusted: text nodes and canvas fillText only, never HTML.
//
// How the canvas behaves (U-12.1), for the screens that use it:
// * tools: 'pan' (drag pans; a click on an opening or a flag reports it), 'select' (click = the nearest item within 6 px,
//   shift adds, ctrl / cmd toggles; a drag box selects the items wholly inside, alt: touched; openings and flags are
//   clicked first), 'pick-point' (a click reports the point, snapped to a drawn vertex within 6 px; a drag pans),
//   'draw-box' (a drag reports the box, sheet m). Every tool: the wheel zooms at the pointer, the middle button pans.
// * pick modes: 'item'; 'block' (the innermost INSERT anchor holding the clicked item, by key prefix; clicking inside an
//   already selected block climbs one level; a view or xref block holding a quarter of the sheet or more is never picked,
//   so a block pick cannot select the whole drawing; an item in no block selects itself); 'layer-in-box' (a click picks
//   an item and remembers its layer, shown highlighted; a box then selects every item of that layer inside it; a box
//   started on an item takes that item's layer).
// * keys (the canvas takes focus on a press): arrows pan (shift: more), + / - zoom, F / 0 / Home fit, Esc clears the
//   selection. Delete is left to the page (it bubbles): PlanCanvasProps has no set-aside callback (U7.md).
// * `selected` / `setAside` keys: an INSERT anchor's key covers its subtree (key + '/...'), drawn with it; set-asides are
//   crossed in red, the overlay's built set-asides in grey. `flags` and `diff`: the overlay's floor's (all with no
//   overlay). `area`: a box is lit, the rest dimmed. `focus`: the view fits it whenever its value changes.
// * onHover reports the item under the pointer (null when none); the tooltip shows the layer, type and key.
import { createElement, type JSX } from 'react';
import type { Vec2 } from '@walkthrough/viewer';
import type { Bbox, DiffBody, Flag, FloorArea, LayerRole, OverlayFloor, PlanGeometry, Sha1, Units } from '@/upload/contracts';
import { proposeAreasIn } from './areas';
import { decode, planData } from './decode';
import { nearLayersIn } from './near';
import { PlanCanvasView } from './PlanCanvas';

export interface DecodedPlan {                        // fields U6 may read; U7 may add private ones
  source: Sha1; units: Units; origin: Vec2; quantum: number;
  layers: string[];                                   // index -> layer name
  extents: Bbox;                                      // sheet m
  count: number;                                      // entries
  keyAt(i: number): string; layerAt(i: number): number; typeAt(i: number): number;
  refOf(key: string): { sig: string; rsig: string; elementId: string | null; layer: string } | null;   // for ItemRef
}
export type PickMode = 'item' | 'block' | 'layer-in-box';
export interface PlanCanvasProps {
  plan: DecodedPlan;                                  // decodePlan(PlanGeometry)
  roleOf: (layerIndex: number) => LayerRole;
  highlightLayer?: number | null;
  area?: FloorArea | null;                            // lit; the rest dimmed
  overlay?: OverlayFloor | null;
  flags?: Flag[];
  selected: ReadonlySet<string>;                      // item keys
  setAside: ReadonlySet<string>;
  diff?: DiffBody | null;
  tool: 'pan' | 'select' | 'pick-point' | 'draw-box';
  pick?: PickMode;                                    // default 'item' (U-12.1)
  focus?: Bbox | null;                                // zoom to it when it changes
  onSelect?(keys: string[], mode: 'replace' | 'add' | 'toggle'): void;
  onPick?(p: Vec2): void;
  onBox?(bbox: Bbox): void;
  onOpening?(id: string): void;
  onFlag?(id: string): void;
  onHover?(info: { layer: string; type: number; key: string } | null): void;
}

/** The plan canvas (U-12.1): see the notes at the top of this file. */
export function PlanCanvas(props: PlanCanvasProps): JSX.Element {
  return createElement(PlanCanvasView, props);
}

/** Decodes a PlanGeometry (U-7.5) once into typed arrays: entry i's key, layer index, type, first point and point count;
 *  its sig / rsig / element id for the ItemRefs the check screen writes (never derived in the browser). Throws on a
 *  malformed file (parallel arrays of other lengths, points out of range, a layer or type out of range). `extents` is the
 *  box of every point. */
export function decodePlan(json: PlanGeometry): DecodedPlan {
  return decode(json);
}

/** U-14.3: area proposals clustered on the given layers only (the clustering of U-7.3 with a layer filter): sheet-metre
 *  boxes over 25 m2, top edge first, then left edge. */
export function proposeAreas(plan: DecodedPlan, layers: ReadonlySet<number>): Bbox[] {
  return proposeAreasIn(planData(plan), layers);
}

/** For each layer index not in `wallLayers`: how many of its items lie within `dist` m of a wall-layer segment.
 *  An item is one key (a hatch's loops count once), drawn items only; layers with none are left out of the map. */
export function nearLayers(plan: DecodedPlan, wallLayers: ReadonlySet<number>, dist: number): Map<number, number> {
  return nearLayersIn(planData(plan), wallLayers, dist);
}

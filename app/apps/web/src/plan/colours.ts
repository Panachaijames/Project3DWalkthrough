// Colours on the plan canvas (docs/upload/DESIGN.md U-12.1: "the cached paths with the role's colour, `other` and
// `ignore` faint"; the overlay's parts by kind, openings by kind, flags as rings). Owner U7.
// Widths are screen pixels (the canvas divides them by the scale). Every colour is #rrggbb; faintness is an alpha. The
// drawing's own lines are at most 1 px wide: Chromium draws those as hairlines, three times faster than 1.4 px (measured on
// the house sheet: 11 ms against 28 ms a frame), so walls stand out by their colour, not their width.
import type { PartKind } from '@walkthrough/viewer';
import type { LayerRole } from '@/upload/contracts';

export interface Stroke { colour: string; alpha: number; width: number }

export const ROLES: readonly LayerRole[] = [
  'wall', 'column', 'glass', 'window', 'door', 'screen', 'stair', 'stair-above', 'railing', 'furniture', 'room-name',
  'room-outline', 'level', 'grid', 'light', 'other', 'ignore',
];

/** Per role: what is built is drawn strong, what is read only is lighter, `other` and `ignore` faint. */
export const ROLE_STROKE: Readonly<Record<LayerRole, Stroke>> = {
  wall: { colour: '#1f2328', alpha: 1, width: 1 },
  column: { colour: '#7a4a1e', alpha: 1, width: 1 },
  glass: { colour: '#0a7fb8', alpha: 1, width: 1 },
  window: { colour: '#33a6d6', alpha: 1, width: 1 },
  door: { colour: '#d4500f', alpha: 1, width: 1 },
  screen: { colour: '#8a3fb0', alpha: 1, width: 1 },
  stair: { colour: '#2e7d32', alpha: 1, width: 1 },
  'stair-above': { colour: '#6fae72', alpha: 0.9, width: 1 },
  railing: { colour: '#5d4b8a', alpha: 1, width: 1 },
  furniture: { colour: '#b07d12', alpha: 0.95, width: 1 },
  'room-name': { colour: '#1d5fb8', alpha: 0.9, width: 1 },
  'room-outline': { colour: '#00897b', alpha: 0.9, width: 1 },
  level: { colour: '#b0306a', alpha: 0.9, width: 1 },
  grid: { colour: '#7d8590', alpha: 0.8, width: 0.8 },
  light: { colour: '#c9a400', alpha: 0.9, width: 1 },
  other: { colour: '#8c959f', alpha: 0.35, width: 0.8 },
  ignore: { colour: '#afb8c1', alpha: 0.18, width: 0.7 },
};

/** Solid fills (hatch type 2) are filled with the role's colour at this share of its alpha. */
export const FILL_ALPHA = 0.28;
/** Pattern fill outlines (hatch type 3) are drawn at this share of the role's alpha. */
export const PATTERN_ALPHA = 0.5;

export const BACKGROUND = '#ffffff';
/** The highlighted layer: drawn on top, wider, over a veil that pales the rest. */
export const HIGHLIGHT: Stroke = { colour: '#ff2d92', alpha: 1, width: 1.8 };
export const HIGHLIGHT_VEIL = 'rgba(255,255,255,0.62)';
/** Outside the floor's area. */
export const DIM_VEIL = 'rgba(244,246,248,0.72)';
export const AREA_EDGE: Stroke = { colour: '#0b6bcb', alpha: 0.9, width: 1.5 };
export const SELECTED: Stroke = { colour: '#0060df', alpha: 1, width: 2.6 };
export const SET_ASIDE: Stroke = { colour: '#d1242f', alpha: 0.95, width: 1.6 };
/** Items the last build set aside (overlay.setAside): crossed in grey. */
export const BUILT_ASIDE: Stroke = { colour: '#6e7781', alpha: 0.9, width: 1.4 };
export const RUBBER_BAND = { stroke: '#0060df', fill: 'rgba(0,96,223,0.08)' };
export const PICK_MARK = '#d1242f';

/** The overlay's parts, filled by kind (the viewer's palette, D-5.4, where it has one). */
export const PART_FILL: Readonly<Record<PartKind, string>> = {
  wall: '#8a7f70', column: '#6b5d4f', lintel: '#b3a796', sill: '#b3a796', parapet: '#9c8f7d', glass: '#5fa8cf',
  mullion: '#5d6b74', railing: '#6f6a75', single: '#e0a458', step: '#8fa889', slab: '#d4d8d2', pane: '#7cc0e0',
  balustrade: '#6f6a75', low: '#a39a8c', builtin: '#a3876a', deck: '#b59a76', post: '#5d6b74',
  // BuiltModel v2 kinds: placeholders of the rooms scaffold (R0); R6 draws stairs and ceilings its own way
  tread: '#7d9a78', landing: '#9bb394', ceiling: '#e9e7e0',
};
export const PART_ALPHA = 0.5;
export const SLAB_EDGE: Stroke = { colour: '#4d7c5b', alpha: 0.9, width: 1.2 };

export const OPENING_COLOUR: Readonly<Record<'door' | 'window' | 'passage', string>> = {
  door: '#e8590c', window: '#1c7ed6', passage: '#2f9e44',
};
export const OPENING_WIDTH = 5;
export const FURNITURE: Stroke = { colour: '#9c6b00', alpha: 0.95, width: 1.2 };
export const FURNITURE_FILL = 'rgba(240,190,60,0.22)';
export const FLAG_COLOUR: Readonly<Record<'check' | 'info', string>> = { check: '#d1242f', info: '#0969da' };
/** Flag rings: radius in screen pixels. */
export const FLAG_RADIUS = 9;
export const DIFF_ADDED = '#2da44e';
export const DIFF_REMOVED = '#cf222e';
export const LABEL = { font: '11px system-ui, sans-serif', colour: '#24292f', halo: 'rgba(255,255,255,0.9)' };

// ---- the rooms milestone (docs/rooms/DESIGN.md R-6.4, R-12.6; R6): rooms, the plate's holes, unfloored areas, stairs,
// closings and the fixes waiting for a Rebuild. Hatches are screen-pixel spaced lines clipped to their area.
/** Rooms: tinted, outlined. */
export const ROOM_FILL = '#3d7be0';
export const ROOM_ALPHA = 0.13;
export const ROOM_EDGE: Stroke = { colour: '#2f6fd6', alpha: 0.85, width: 1.2 };
/** A hole of the plate (stair well, shaft, void, "no floor"): hatched grey. */
export const HOLE_HATCH: Stroke = { colour: '#57606a', alpha: 0.75, width: 1 };
/** An unfloored area: hatched orange, its mouth dashed. */
export const UNFLOORED_HATCH: Stroke = { colour: '#f08c00', alpha: 0.7, width: 1 };
export const MOUTH: Stroke = { colour: '#f08c00', alpha: 1, width: 2.5 };
/** An area answered "it is outdoors" (built, or waiting): hatched grey-blue. */
export const OUTDOORS_HATCH: Stroke = { colour: '#8c959f', alpha: 0.8, width: 1 };
export const HATCH_PX = 8;
/** Stairs: the outline, the walking line and the arrow at the bottom; a stair kept as lines is dashed. */
export const STAIR_OUTLINE: Stroke = { colour: '#1a7f37', alpha: 0.9, width: 1.2 };
export const STAIR_WALK: Stroke = { colour: '#1a7f37', alpha: 1, width: 2.5 };
/** The app's closings (bridges, doorway closings): short dashed lines; a staff closing line: solid. */
export const CLOSING_APP: Stroke = { colour: '#9a6700', alpha: 1, width: 2.5 };
export const CLOSING_STAFF: Stroke = { colour: '#fd7e14', alpha: 1, width: 2.5 };
/** A fix waiting for a Rebuild: dashed orange; a removed closing struck through in red. */
export const WAITING: Stroke = { colour: '#f76707', alpha: 1, width: 2.5 };
export const STRUCK: Stroke = { colour: '#cf222e', alpha: 1, width: 2 };
/** RR (S13): the room or stair open in the Check step's panel: a strong outline and a light tint. */
export const PICKED: Stroke = { colour: '#c2255c', alpha: 1, width: 3 };
export const PICKED_ALPHA = 0.16;
/** RR (S13): the floor plate's faint tint (under the dashed outline), so the Floor plate tick shows a change. */
export const SLAB_FILL = '#4d7c5b';
export const SLAB_ALPHA = 0.07;
/** The first end of a line being drawn and the line to the pointer. */
export const LINE_DRAFT: Stroke = { colour: '#f76707', alpha: 0.9, width: 1.5 };

/** The stroke of a layer whose role is `role` (an unknown value is drawn as `other`). */
export function roleStroke(role: LayerRole | string): Stroke {
  return ROLE_STROKE[role as LayerRole] ?? ROLE_STROKE.other;
}

/** '#rrggbb' + alpha -> 'rgba(r,g,b,a)'. */
export function rgba(colour: string, alpha: number): string {
  const m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(colour);
  if (!m) return colour;
  return `rgba(${parseInt(m[1]!, 16)},${parseInt(m[2]!, 16)},${parseInt(m[3]!, 16)},${Math.round(alpha * 1000) / 1000})`;
}

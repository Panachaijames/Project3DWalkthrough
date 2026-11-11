// DEFAULT_PART_STYLES: one style per part kind (DESIGN.md 5.4); presentation.partStyles overrides them per project.
// Owner: builder A. Scaffold: the values of the 5.4 table. Unset fields take the builder's defaults ("standard" material:
// roughness 0.85, DoubleSide; collider true; renderOrder 0; edges opacity 0.45 for glass, else 0.6).
import type { PartKind, PartStyle } from '../contracts';

const WALL = { color: '#e3ddd3', edge: '#7f786e' } as const;
const GLASS = { color: '#9cc3d5', edge: '#5f8fa6', glass: true, opacity: 0.3, roughness: 0.15, metalness: 0, renderOrder: 3, edgeOpacity: 0.45 } as const;

export const DEFAULT_PART_STYLES: Record<PartKind, PartStyle> = {
  wall: { ...WALL, mesh: 'solid' },
  column: { ...WALL, mesh: 'solid' },
  lintel: { ...WALL, mesh: 'solid' },
  sill: { ...WALL, mesh: 'sill' },
  parapet: { ...WALL, mesh: 'parapet' },
  glass: { ...GLASS, mesh: 'glass' },
  pane: { ...GLASS, mesh: 'pane' },
  mullion: { color: '#5d6b74', edge: '#3d474e', mesh: 'mullion' },
  railing: { color: '#6f6a75', edge: '#4a4550', mesh: 'railing', see: 0.5, roughness: 0.6, metalness: 0.2, renderOrder: 2 },
  balustrade: { ...GLASS, mesh: 'balustrade' },
  single: { color: '#e0a458', edge: '#a86f2c', mesh: 'single', single: true },
  step: { color: '#b9c7b4', edge: '#6f8a6a', mesh: 'step' },
  low: { color: '#d2c6b2', edge: '#8d8170', mesh: 'low' },
  builtin: { color: '#c9a77f', edge: '#8a6d4b', mesh: 'builtin' },
  deck: { color: '#b08a5c', edge: '#8a6a44', mesh: 'deck', collider: false },
  post: { color: '#6f6153', edge: '#4a4038', mesh: 'post' },
  // Slabs: one mesh per slab part, their own material (roughness 0.95, polygonOffset -1 / -1, FrontSide), no edges drawn,
  // walkable rather than a collider.
  slab: { color: '#d4d8d2', edge: '#d4d8d2', mesh: 'slab', roughness: 0.95, collider: false },
  // BuiltModel v2 (rooms/DESIGN.md R-9.2, R-9.7). PLACEHOLDERS of the rooms scaffold (R0), so that every kind has a style:
  // treads and landings are walked on, never colliders; ceilings are no colliders either. R4 gives them their meshes
  // (the surfaces, the per-floor ceiling mesh shown in Walk and Ghost only).
  tread: { color: '#cdc6b8', edge: '#8d8474', mesh: 'tread', collider: false },
  landing: { color: '#cdc6b8', edge: '#8d8474', mesh: 'landing', collider: false },
  ceiling: { color: '#f4f3ef', edge: '#f4f3ef', mesh: 'ceiling', roughness: 0.95, collider: false },
};

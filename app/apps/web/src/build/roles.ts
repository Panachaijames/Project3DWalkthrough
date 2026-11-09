// The layer roles staff choose on the Layers step (docs/upload/DESIGN.md U-8.1): the select shows the labels, the
// settings keep the role names. Pure data: the tests and the e2e specs import it too.
import type { LayerRole } from '@/upload/contracts';

export interface RoleInfo { role: LayerRole; label: string; help: string }

/** In the order the select lists them (U-8.1's table). */
export const ROLES: readonly RoleInfo[] = [
  { role: 'wall', label: 'Walls', help: 'built as walls; doors and windows are cut into them' },
  { role: 'column', label: 'Columns', help: 'built as solid columns' },
  { role: 'glass', label: 'Glass walls', help: 'curtain walls and glass partitions, built full height' },
  { role: 'window', label: 'Windows', help: 'windows in walls; a sill and a head are built round them' },
  { role: 'door', label: 'Doors', help: 'door swings and leaves: where doors are cut' },
  { role: 'screen', label: 'Screens', help: 'grilles and louvres: see-through, never cut' },
  { role: 'stair', label: 'Stairs', help: 'stair treads on this floor' },
  { role: 'stair-above', label: 'Stairs above', help: 'the stair of the floor above, drawn dashed' },
  { role: 'railing', label: 'Railings', help: 'balustrades and handrails, built 1.10 m high' },
  { role: 'furniture', label: 'Furniture', help: 'one coloured box per piece' },
  { role: 'room-name', label: 'Room names', help: 'texts that name rooms' },
  { role: 'room-outline', label: 'Room outlines', help: 'room boundaries; can suggest missing walls' },
  { role: 'level', label: 'Levels', help: 'level marks such as +0.90' },
  { role: 'grid', label: 'Grid', help: 'grid lines and their bubbles: used to line floors up' },
  { role: 'light', label: 'Lights', help: 'light fittings: kept for later, not built now' },
  { role: 'other', label: 'Not built (kept as context)', help: 'not built, but still read when finding doors and windows' },
  { role: 'ignore', label: 'Ignore', help: 'dropped everywhere, also from finding doors and windows' },
];

const BY_ROLE = new Map(ROLES.map(r => [r.role, r]));
export const roleLabel = (role: LayerRole): string => BY_ROLE.get(role)?.label ?? role;
export const roleHelp = (role: LayerRole): string => BY_ROLE.get(role)?.help ?? '';
export const isRole = (v: string): v is LayerRole => BY_ROLE.has(v as LayerRole);

/** The roles whose lines count as walls for the "close to walls" check (U-8.1, U-14.3). */
export const WALL_ROLES: ReadonlySet<LayerRole> = new Set<LayerRole>(['wall', 'column']);
/** The chip on an `ignore` row with items within 1 m of wall-role lines (U-8.1). */
export const CLOSE_TO_WALLS = 'close to walls: ignoring it can change which doors and windows are found';
/** How near (m) counts as close (U-8.1). */
export const CLOSE_TO_WALLS_M = 1.0;

/** Where a suggestion came from (U-8.3), as the Layers step says it. */
export const SUGGESTION_FROM: Record<'office' | 'office-similar' | 'name' | 'contents' | 'default', string> = {
  office: 'the office remembers this layer',
  'office-similar': 'the office remembers a layer of this name',
  name: 'by its name',
  contents: 'by what is drawn on it',
  default: 'nothing known: kept as context',
};

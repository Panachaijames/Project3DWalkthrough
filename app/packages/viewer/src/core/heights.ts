// Build settings: levels, wall heights, fit, plinths (DESIGN.md 5.5). Owner: builder A.
// HeightsApi.apply does, per floor, everything a Build settings change does to the model (the replay never scales geometry
// itself), from the prototypes: build_replay.js applySettings (the floor group's home position, the wall scale about the
// floor level), each page's applySettings (the Walk level) and the house page's (the plinth that keeps its foot on the
// ground, fitPieces: lintel heads that stay where they are, panes and sills cut at the wall top). Then bus 'settings'.
// BuiltModel v2 (rooms/DESIGN.md R-9.6; rooms step R4): fit 'storey' (treads, landings, the wall pieces cut under a stair)
// scales about its floor's level by the storey ratio S = (L(to) - L(from)) / (L0(to) - L0(from)) of its stairway's two
// floors, so a changed level keeps the stair climbable and the cut walls under it. Ceilings are in the floor's group and
// in no rise list: they keep their height above their floor's level (the `fixed` rule).
import type { BufferGeometry, Mesh } from 'three';
import type { CreateHeights, FloorRecord, FloorSettings, HeightsApi, SettingsMap } from '../contracts';
import { fitDataOf } from './build';

const EPS = 1e-6;

/**
 * Refits one fitted geometry (mesh or edges) to the wall height H (m above the floor level), from its base positions:
 * fit 'top': z0 stays and z1 becomes H (z' = z0 + (z - z0)(H - z0)/(z1 - z0)); fit 'clip': z' = min(z, H); either way a
 * part whose bottom is not below H (H <= z0 + 1e-6) collapses to its centre at H and vanishes.
 */
export function refitGeometry(g: BufferGeometry, H: number): boolean {
  const d = fitDataOf(g);
  if (!d) return false;
  const pos = g.getAttribute('position');
  const a = pos.array as Float32Array;
  const n = d.base.length / 3;
  for (let i = 0; i < n; i++) {
    const z0 = d.z0[i]!, z1 = d.z1[i]!;
    let x = d.base[3 * i]!, z = d.base[3 * i + 2]!;
    const rel = d.base[3 * i + 1]! - d.level;
    let y: number;
    if (H <= z0 + EPS) { y = H; x = d.cx[i]!; z = d.cz[i]!; }
    else if (d.fit === 'top') y = z0 + (rel - z0) * (H - z0) / ((z1 - z0) || 1);
    else y = Math.min(rel, H);
    a[3 * i] = x; a[3 * i + 1] = d.level + y; a[3 * i + 2] = z;
  }
  pos.needsUpdate = true;
  g.computeBoundingBox();
  g.computeBoundingSphere();
  g.boundsTree?.refit();
  return true;
}

export const createHeights: CreateHeights = ctx => {
  const settings: SettingsMap = {};
  for (const f of ctx.floors) settings[f.key] = { level: f.modelLevel, height: f.wallHeight };
  const plinthsOf = (f: FloorRecord): Mesh[] => ctx.built.plinths.filter(m => m.parent === f.group || m.userData.floor === f.key);
  /**
   * The height each fitted mesh was last refitted to (skip the work when it did not change). Nothing at first: the first
   * apply refits every fitted mesh, at the model's height too, as the house page's fitPieces ran at every start-up.
   */
  const fittedAt = new Map<Mesh, number>();

  const apply = (next: SettingsMap): void => {
    for (const f of ctx.floors) {
      const s: FloorSettings | undefined = next[f.key];
      if (!s) continue;
      const L0 = f.modelLevel, H0 = f.wallHeight;
      const L = Number.isFinite(s.level) ? s.level : settings[f.key]!.level;
      const H = Number.isFinite(s.height) && s.height > 0 ? s.height : settings[f.key]!.height;
      settings[f.key] = { level: L, height: H };
      f.level = L;                                             // Walk's level
      f.group.position.set(0, L - L0, 0);                      // the floor's home position
      const k = H / H0;
      for (const r of f.rise) {                                // walls (fit scale) scale about the floor level
        const sc = r.scales ? k : 1;
        for (const obj of [r.mesh, r.edges]) if (obj) { obj.scale.y = sc; obj.position.y = L0 * (1 - sc); }
      }
      for (const mesh of ctx.built.fitted[f.key] ?? []) {      // fit top / clip: heads stay, panes and sills cut at the top
        if (fittedAt.get(mesh) === H) continue;                // already at H: nothing to do
        fittedAt.set(mesh, H);
        refitGeometry(mesh.geometry, H);
        const edges = f.rise.find(r => r.mesh === mesh)?.edges;
        if (edges) refitGeometry(edges.geometry, H);
      }
      if (L0 > 0) {                                            // a plinth keeps its foot on the ground (y = 0)
        for (const m of plinthsOf(f)) { m.scale.y = Math.max(0.01, L / L0); m.position.y = L0 - L; }
      }
      for (const sheet of ctx.pictures?.sheets ?? []) {        // the plan picture lies on its floor
        if (sheet.userData.key === f.key) sheet.position.y = L - L0;
      }
    }
    // fit 'storey', once every level is known (the upper floor of a stairway may come later in the list)
    for (const f of ctx.floors) {
      for (const r of f.rise) {
        if (r.fit !== 'storey') continue;
        const to = ctx.floorByKey.get(String(r.mesh.userData.stairTo));
        const span = to ? to.modelLevel - f.modelLevel : 0;
        const S = to && span > EPS ? Math.max(0.01, (settings[to.key]!.level - settings[f.key]!.level) / span) : 1;
        for (const obj of [r.mesh, r.edges]) if (obj) { obj.scale.y = S; obj.position.y = f.modelLevel * (1 - S); }
      }
    }
    ctx.bus.emit('settings', { settings: JSON.parse(JSON.stringify(settings)) as SettingsMap });
  };

  const api: HeightsApi = {
    apply,
    get settings() { return settings; },
  };
  return api;
};

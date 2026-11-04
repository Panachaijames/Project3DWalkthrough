// The page-side helpers of the prototype tests, ported once (DESIGN.md 17.4; WORK_BREAKDOWN S.9). Scaffold.
// Sources: hotel_test/test_hotel.mjs (doorWalks, glassWalks, wallWalks, pageHelpers: the most complete versions; the
// bank's and the suite's differ only in diagnostics, the start-spot list and the random seed, which are parameters
// here) and cad_test/test_house_openings.mjs (the house's floorAt / cross / walkThrough). Every function runs INSIDE the
// page (page.evaluate) and reads only window globals: __viewer, __host (v1 shapes: on the prototype pages through
// lib/prototype-shim.ts) and __walkthrough.THREE (instead of the prototypes' `await import('three')`).
// Model metres; plan (x, y) is three.js (x, z = -y).
import type { Page } from '@playwright/test';

/* eslint-disable @typescript-eslint/no-explicit-any */

export interface DoorWalk { id: string; kind: string; exterior: boolean; fwd: number | 'no start'; back: number | 'no start'; ok: boolean; [k: string]: unknown }
export interface GlassWalk { id: string; what: string; side: number; stoppedAt: number | null; ahead: string | null; ok: boolean; tries: unknown[] }
export interface WallWalks { floor: string; tried: number; wentThrough: number; endedInsideWall: number; skippedInABox?: number }
export interface HouseWalk { floorPos: boolean; floorNeg: boolean; fwd?: number | string; back?: number | string }

/**
 * Walk through every door and passage of the floor you are on: from in front of each (0.9 m, or nearer: `backs`), walk
 * straight through its middle; you should come out at least 0.3 m on the other side. Exterior ones only have to be
 * reachable from inside (you get to the door line). why: also say what is in the way (needs installPageHelpers).
 * The suite's prototype test used backs [0.9, 0.7, 0.55].
 */
export function doorWalks(page: Page, opts: { why?: boolean; backs?: number[] } = {}): Promise<DoorWalk[]> {
  return page.evaluate(({ why, backs }) => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), out: any[] = [];
    const num = (x: unknown) => typeof x === 'number';
    for (const d of w.__host.openings) {
      if (d.floor !== s.floor.key || (d.kind !== 'door' && d.kind !== 'passage')) continue;
      const r: any = { id: d.id, kind: d.kind, exterior: !!d.exterior };
      for (const sign of [1, -1]) {
        const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
        let along: number | null = null; const tries: any[] = [];
        for (const back of backs) {                                  // a start spot on the floor, clear of walls
          s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
          const onFloor = v.probe.onFloor(), clr = v.probe.clearance();
          if (!onFloor || clr < 0.25) { tries.push({ back, onFloor, clearance: Math.round(Math.min(9, clr) * 100) / 100, ...(why ? { near: w.__t.near(d.floor, s.pos.x, s.pos.z, 0.3) } : {}) }); continue; }
          v.probe.walk(deg, back * 2);
          along = (s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny;      // metres past the opening's line
          if (why) tries.push({ back, along: Math.round(along * 100) / 100, stoppedBy: w.__t.stoppedBy(d.floor, s.pos.x, s.pos.z, deg) });
          break;
        }
        r[sign > 0 ? 'fwd' : 'back'] = along === null ? 'no start' : Math.round(along * 100) / 100;
        if (why || along === null) r[sign > 0 ? 'fwdTries' : 'backTries'] = tries;
      }
      r.ok = d.exterior ? [r.fwd, r.back].some(x => num(x) && x > -0.15) : num(r.fwd) && num(r.back) && r.fwd > 0.3 && r.back > 0.3;
      out.push(r);
    }
    s.pos.copy(keep); return out;
  }, { why: !!opts.why, backs: opts.backs ?? [0.9, 0.7, 0.55, 0.45, 0.4] });
}

/**
 * Walk straight at every glass probe of the floor you are on from in front of it (1.0 m, or nearer), as far as you get:
 * how short of the glass you stop (ok between 0.1 and 0.6 m), and what is straight ahead of you then.
 */
export function glassWalks(page: Page, opts: { why?: boolean } = {}): Promise<GlassWalk[]> {
  return page.evaluate(({ why }) => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone(), out: any[] = [];
    for (const g of w.__host.probes) {
      if (g.floor !== s.floor.key) continue;
      for (const side of g.inside) {
        const nx = g.nx * side, ny = g.ny * side, deg = Math.atan2(nx, -ny) * 180 / Math.PI;   // facing the glass
        let res: number | null = null, ahead: string | null = null; const tries: any[] = [];
        for (const back of [1.0, 0.8, 0.6]) {
          s.pos.x = g.x + nx * back; s.pos.z = -(g.y + ny * back);
          const onFloor = v.probe.onFloor(), clr = v.probe.clearance();
          if (!onFloor || clr < 0.25) { tries.push({ back, onFloor, clearance: Math.round(Math.min(9, clr) * 100) / 100, ...(why ? { near: w.__t.near(g.floor, s.pos.x, s.pos.z, 0.3) } : {}) }); continue; }
          v.probe.walk(deg, 2.0);
          res = Math.round(((s.pos.x - g.x) * nx + (-s.pos.z - g.y) * ny) * 100) / 100;   // metres short of the glass
          const h = w.__host.rayHit(g.floor, s.pos.x, -s.pos.z, 1.2, -nx, -ny, 1.5);
          ahead = h ? h.name + ' at ' + h.d.toFixed(2) + ' m' : 'nothing';
          if (why) tries.push({ back, res, stoppedBy: w.__t.stoppedBy(g.floor, s.pos.x, s.pos.z, deg) });
          break;
        }
        out.push({ id: g.id, what: g.what, side, stoppedAt: res, ahead, ok: res !== null && res > 0.1 && res < 0.6, tries });
      }
    }
    s.pos.copy(keep); return out;
  }, { why: !!opts.why });
}

/**
 * Walk into the nearest wall from 40 random spots of the floor you are on: never end up on the other side or inside it.
 * seed: 7 (bank, hotel), 3 (suite). outsideBoxes (boxes shown): a spot inside a box that stops you is skipped and counted
 * (needs installPageHelpers). maxTries: 8000 (bank, hotel), 6000 (suite).
 */
export function wallWalks(page: Page, opts: { seed?: number; outsideBoxes?: boolean; maxTries?: number } = {}): Promise<WallWalks> {
  return page.evaluate(({ seed0, outsideBoxes, maxTries }) => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone();
    let seed = seed0, n = 0, through = 0, stuck = 0, tries = 0, inBox = 0;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (const o of s.floor.group.children) {
      if (!o.geometry) continue; o.geometry.computeBoundingBox(); const g = o.geometry.boundingBox;
      x0 = Math.min(x0, g.min.x); x1 = Math.max(x1, g.max.x); z0 = Math.min(z0, g.min.z); z1 = Math.max(z1, g.max.z);
    }
    while (n < 40 && tries++ < maxTries) {
      s.pos.x = x0 + rnd() * (x1 - x0); s.pos.z = z0 + rnd() * (z1 - z0);
      if (!v.probe.onFloor() || v.probe.clearance() < 0.6) continue;
      if (outsideBoxes && w.__t.holding().length) { inBox++; continue; }
      const d = [...Array(72)].map((_, i) => v.probe.open(i * 5)); let k = 0; d.forEach((x: number, j: number) => { if (x < d[k]) k = j; });
      if (d[k] > 2.5) continue;
      const a = s.pos.clone(); v.probe.walk(k * 5, d[k] + 1);
      n++; if (v.probe.crosses(a.x, a.z, s.pos.x, s.pos.z)) through++; if (v.probe.clearance() < 0.15) stuck++;
    }
    s.pos.copy(keep);
    return Object.assign({ floor: s.floor.key, tried: n, wentThrough: through, endedInsideWall: stuck }, outsideBoxes ? { skippedInABox: inBox } : {});
  }, { seed0: opts.seed ?? 7, outsideBoxes: !!opts.outsideBoxes, maxTries: opts.maxTries ?? 8000 });
}

/**
 * The house's walk across an opening line (cad_test/test_house_openings.mjs HELPERS), for each record of `list`
 * (an opening, or { x, y, nx, ny, a, b, width }): floorPos / floorNeg = floor 0.9 m either side; fwd (from -n) and back
 * (from +n) = metres past the line, or why there was no start ('no floor', 'tight', 'no start').
 */
export function walkThrough(page: Page, list: Record<string, unknown>[]): Promise<(HouseWalk & Record<string, unknown>)[]> {
  return page.evaluate(items => {
    const w = window as any, v = w.__viewer, s = v.state, keep = s.pos.clone();
    const floorAt = (d: any, k: number) => { s.pos.x = d.x + d.nx * k; s.pos.z = -(d.y + d.ny * k); return v.probe.onFloor(); };
    const cross = (d: any, sign: number) => {
      const nx = d.nx * sign, ny = d.ny * sign, deg = Math.atan2(-nx, ny) * 180 / Math.PI;
      let why = 'no start';
      for (const back of [0.9, 0.7, 0.55, 0.45]) {
        s.pos.x = d.x - nx * back; s.pos.z = -(d.y - ny * back);
        if (!v.probe.onFloor()) { why = 'no floor'; continue; }
        if (v.probe.clearance() < 0.25) { why = 'tight'; continue; }
        v.probe.walk(deg, back * 2);
        return Math.round(((s.pos.x - d.x) * nx + (-s.pos.z - d.y) * ny) * 100) / 100;
      }
      return why;
    };
    const one = (d: any) => {
      const r: any = { floorPos: floorAt(d, 0.9), floorNeg: floorAt(d, -0.9) };
      if (r.floorNeg) r.fwd = cross(d, 1);                      // from the -n side through to the +n side
      if (r.floorPos) r.back = cross(d, -1);
      return r;
    };
    const out = items.map(d => ({ ...d, ...one(d) }));
    s.pos.copy(keep); return out;
  }, list);
}

/** The house test's verdict on a walkThrough result: 'both ways', 'from the floor side', 'blocked' or 'skipped'. */
export function judgeHouseWalk(r: HouseWalk): 'both ways' | 'from the floor side' | 'blocked' | 'skipped' {
  const num = (x: unknown): x is number => typeof x === 'number';
  if (r.floorPos && r.floorNeg) return num(r.fwd) && num(r.back) && r.fwd > 0.3 && r.back > 0.3 ? 'both ways' : 'blocked';
  if (r.floorPos || r.floorNeg) return [r.fwd, r.back].some(x => num(x) && x > -0.15) ? 'from the floor side' : 'blocked';
  return 'skipped';
}

/**
 * Installs window.__t: the furniture and picture read-outs of the prototype tests' pageHelpers (lanes at the boxes'
 * faces, walks, targets, crossable, near, stoppedBy, topSpots, reach, span, hoverSpots, along, walkTo, holding, leave,
 * only, verdict, spawn, standIn, and the plan-picture lumAt, wallCorners, lineUp, faceSpots, faceLineUp). Call after the
 * viewer is ready; the doorWalks / glassWalks `why` option and wallWalks `outsideBoxes` use it. Read it in a spec with
 * page.evaluate(() => (window as any).__t.targets()).
 */
export function installPageHelpers(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const w = window as any;
    const THREE = w.__walkthrough.THREE;
    const F = w.__host.furniture, v = w.__viewer, s = v.state, V3 = THREE.Vector3, RADIUS = 0.3, KNEE = 0.35, CHEST = 1.2;
    const ray = new THREE.Raycaster(); ray.firstHitOnly = true;
    const levelOf = (key: string) => w.__host.floors.find((f: any) => f.key === key).level;
    const frame = (p: any) => { const r = p.rot * Math.PI / 180; return { c: new V3(p.x, 0, -p.y), ax: new V3(Math.cos(r), 0, -Math.sin(r)), az: new V3(Math.sin(r), 0, Math.cos(r)) }; };
    const pieceOf = (name: string) => (name && name.startsWith('furn:') ? F.pieces().find((p: any) => p.id === name.split(':')[2]) : null);
    const brief = (p: any) => ({ id: p.id, kind: p.kind, family: p.family });
    const spans = (p: any) => (p.z0 < KNEE - 0.02 && p.z1 > KNEE + 0.02) || (p.z0 < CHEST - 0.02 && p.z1 > CHEST + 0.02);
    const colliders = (floor: string, skipKind?: string) => w.__host.FL[floor].colliders.filter((m: any) => m.visible && !(skipKind && m.name.startsWith('furn:' + skipKind + ':')));
    function ahead(floor: string, x: number, z: number, dir: any, far: number, cols: any[]) {
      const lv = levelOf(floor), side = new V3(-dir.z, 0, dir.x), out: any[] = [];
      for (const h of [KNEE, CHEST]) for (const k of [0, -0.25, 0.25, -0.5, 0.5, -0.75, 0.75, -0.95, 0.95]) {
        ray.set(new V3(x, lv + h, z).addScaledVector(side, k * RADIUS), dir); ray.far = far;
        const hit = ray.intersectObjects(cols, false)[0];
        if (hit) out.push({ h, k, d: hit.distance, name: hit.object.name });
      }
      return out;
    }
    const hasFloor = (floor: string, x: number, z: number) => { if (s.floor.key !== floor) v.goToFloor(floor); const keep = s.pos.clone(); s.pos.x = x; s.pos.z = z; const ok = v.probe.onFloor(); s.pos.copy(keep); return ok; };
    function lane(p: any, side: number, back: number, through?: boolean, kind?: string) {
      const { c, ax, az } = frame(p), n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side], half = side < 2 ? p.w / 2 : p.d / 2;
      const start = c.clone().addScaledVector(n, half + back), dir = n.clone().negate(), metres = through ? back + 2 * half + 0.6 : back + 0.5;
      const target = F.meshOf(p.id), r: any = { id: p.id, side, back, half, metres, n: n.toArray(), start: [start.x, start.z], free: false, why: '' };
      for (let t = 0; t <= back + (through ? 2 * half + 0.6 : 0); t += 0.25) {
        if (!hasFloor(p.floor, start.x + dir.x * t, start.z + dir.z * t)) { r.why = 'no floor at ' + t.toFixed(2) + ' m'; return r; }
      }
      const cols = colliders(p.floor, kind).filter((m: any) => !through || m !== target);
      const hits = ahead(p.floor, start.x, start.z, dir, (through ? metres : back + 0.4) + RADIUS, cols);
      if (through) { if (hits.length) { r.why = 'meets ' + hits[0].name + ' at ' + hits[0].d.toFixed(2) + ' m'; return r; } r.free = true; return r; }
      const mine = hits.filter((h: any) => h.name === target.name), other = hits.filter((h: any) => h.name !== target.name && h.d < back + 0.2);
      if (other.length) { r.why = 'meets ' + other[0].name + ' at ' + other[0].d.toFixed(2) + ' m'; return r; }
      const mid = mine.find((h: any) => h.k === 0 && h.h === KNEE) || mine.find((h: any) => h.k === 0 && h.h === CHEST);
      if (!mid || Math.abs(mid.d - back) > 0.02) { r.why = 'the box is not met straight ahead at ' + back + ' m'; return r; }
      r.free = true;
      return r;
    }
    function walk(p: any, side: number, back: number, through?: boolean, kind?: string) {
      const L = lane(p, side, back, through, kind);
      if (!L.free) return { id: p.id, side, start: false, why: L.why };
      if (s.floor.key !== p.floor) v.goToFloor(p.floor);
      s.pos.x = L.start[0]; s.pos.z = L.start[1];
      const n = new V3(...L.n), { c, ax, az } = frame(p);
      s.yaw = Math.atan2(n.x, n.z); s.pitch = -0.1;
      const moved = v.probe.walk(Math.atan2(n.x, n.z) * 180 / Math.PI, L.metres);
      const rel = new V3(s.pos.x - c.x, 0, s.pos.z - c.z);
      return { id: p.id, side, start: true, back, metres: L.metres, moved, gap: rel.dot(n) - L.half, inside: Math.abs(rel.dot(ax)) < p.w / 2 && Math.abs(rel.dot(az)) < p.d / 2 };
    }
    function targets() {
      const out: any[] = [];
      for (const p of F.pieces()) {
        if (!p.blocking || !spans(p)) continue;
        let L: any = null, why = '';
        for (const back of [1.0, 0.8, 0.65, 0.5]) {
          for (const side of [2, 3, 0, 1]) { const t = lane(p, side, back, false); if (t.free) { L = t; break; } if (!why) why = t.why; }
          if (L) break;
        }
        out.push({ ...brief(p), floor: p.floor, kind: p.kind, side: L ? L.side : null, back: L ? L.back : null, why: L ? '' : why });
      }
      return out;
    }
    function crossable(kind: string, max: number) {
      const per: Record<string, any[]> = {};
      for (const p of F.pieces().filter((q: any) => q.kind === kind && q.blocking)) {
        let pick: any = null;
        for (const back of [1.0, 0.8, 0.65]) {
          for (const side of [2, 3, 0, 1]) if (!pick && lane(p, side, back, false).free && lane(p, side, back, true, kind).free) pick = { id: p.id, floor: p.floor, side, back };
          if (pick) break;
        }
        if (pick) (per[p.floor] = per[p.floor] || []).push(pick);
      }
      const lists = Object.values(per), out: any[] = [];
      for (let i = 0; out.length < max && lists.some(l => l[i]); i++) lists.forEach(l => { if (l[i] && out.length < max) out.push(l[i]); });
      return out;
    }
    function near(floor: string, x: number, z: number, r: number) {
      const out: any[] = [];
      for (const p of F.pieces()) {
        if (p.floor !== floor || !p.blocking || !((p.z0 < KNEE && p.z1 > KNEE) || (p.z0 < CHEST && p.z1 > CHEST))) continue;
        const { c, ax, az } = frame(p), rel = new V3(x - c.x, 0, z - c.z), d = Math.hypot(Math.max(Math.abs(rel.dot(ax)) - p.w / 2, 0), Math.max(Math.abs(rel.dot(az)) - p.d / 2, 0));
        if (d < r) out.push({ ...brief(p), d: Math.round(d * 100) / 100 });
      }
      return out.sort((a, b) => a.d - b.d);
    }
    function stoppedBy(floor: string, x: number, z: number, deg: number, far = 0.45) {
      const dir = new V3(-Math.sin(deg * Math.PI / 180), 0, -Math.cos(deg * Math.PI / 180)), seen = new Map();
      for (const h of ahead(floor, x, z, dir, far, colliders(floor))) { const p = pieceOf(h.name); if (p && !seen.has(p.id)) seen.set(p.id, { ...brief(p), d: Math.round(h.d * 100) / 100 }); }
      return [...seen.values()];
    }
    function topSpots(kind: string) {
      return F.pieces().filter((p: any) => p.kind === kind).map((p: any) => {
        const r = p.rot * Math.PI / 180, ax = [Math.cos(r), Math.sin(r)], az = [-Math.sin(r), Math.cos(r)];
        const spot = [[0, 0], [p.w / 4, 0], [-p.w / 4, 0], [0, p.d / 4], [0, -p.d / 4]].map(([a, b]) => [p.x + ax[0]! * a! + az[0]! * b!, p.y + ax[1]! * a! + az[1]! * b!])
          .find(([x, y]) => Math.abs((w.__host.downHit(p.floor, x, y, 2.5) ?? -1) - p.z1) < 0.005);
        return { id: p.id, floor: p.floor, spot: spot || null };
      });
    }
    function reach(floor: string, x: number, y: number, h: number, dx: number, dy: number, far: number, drawnOnly?: boolean) {
      const cols = w.__host.FL[floor].colliders.filter((m: any) => m.visible && (!drawnOnly || m.material.visible !== false)), n = Math.hypot(dx, dy);
      ray.set(new V3(x, levelOf(floor) + h, -y), new V3(dx / n, 0, -dy / n)); ray.far = far;
      const hit = ray.intersectObjects(cols, false)[0];
      return hit ? { d: Math.round(hit.distance * 1000) / 1000, name: hit.object.name } : null;
    }
    function span(d: any, h: number, drawnOnly?: boolean) {
      const side = (ux: number, uy: number) => [-0.4, -0.2, 0, 0.2, 0.4].map(t => reach(d.floor, d.x + d.nx * t * d.wallThickness, d.y + d.ny * t * d.wallThickness, h, ux, uy, 3, drawnOnly))
        .filter(Boolean).sort((p: any, q: any) => p.d - q.d)[0] || null;
      const a = side(d.ny, -d.nx), b = side(-d.ny, d.nx);
      return a && b ? { width: Math.round((a.d + b.d) * 1000) / 1000, jambs: [a.d, b.d], what: [a.name, b.name] } : null;
    }
    function hoverSpots(floor: string, max: number) {
      const cam = w.__host.camera, seen = new Set(), out: any[] = [], want = new THREE.Vector2();
      const showing = (o: any) => { for (let n = o; n; n = n.parent) if (!n.visible) return false; return true; };
      const hides = Object.values(w.__host.FL).flatMap((f: any) => f.colliders.concat(f.walkables)).filter((m: any) => showing(m) && !m.name.startsWith('furn:'));
      const boxes = F.pieces().map((b: any) => F.meshOf(b.id)).filter(showing);
      const mine = F.pieces().filter((p: any) => p.floor === floor && p.visible).sort((a: any, b: any) => b.w * b.d - a.w * a.d);
      for (const p of mine) {
        if (seen.has(p.kind)) continue;
        const m = F.meshOf(p.id), q = new V3(p.x, levelOf(floor) + p.z1, -p.y).project(cam);
        const x = (q.x + 1) / 2 * innerWidth, y = (1 - q.y) / 2 * innerHeight;
        if (q.z > 1 || x < 400 || x > innerWidth - 20 || y < 50 || y > innerHeight - 70) continue;
        ray.setFromCamera(want.set(q.x, q.y), cam); ray.far = Infinity;
        const hit = ray.intersectObjects(hides.concat(boxes), false)[0];
        if (hit && hit.object === m) { seen.add(p.kind); out.push({ ...brief(p), floor, x, y, size: `${p.w.toFixed(2)} × ${p.d.toFixed(2)} × ${(p.z1 - p.z0).toFixed(2)} m` }); }
        if (out.length >= max) break;
      }
      return out;
    }
    function along(id: string, side: number) {
      const p = F.pieces().find((q: any) => q.id === id), { c, ax, az } = frame(p), n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side];
      return { rel: (s.pos.x - c.x) * n.x + (s.pos.z - c.z) * n.z, half: side < 2 ? p.w / 2 : p.d / 2, y: s.pos.y - levelOf(p.floor), z0: p.z0, z1: p.z1 };
    }
    function walkTo(p: any, side: number, back: number, metres: number) {
      const { c, ax, az } = frame(p), n = [ax.clone(), ax.clone().negate(), az.clone(), az.clone().negate()][side], half = side < 2 ? p.w / 2 : p.d / 2, start = c.clone().addScaledVector(n, half + back);
      if (s.floor.key !== p.floor) v.goToFloor(p.floor);
      s.pos.x = start.x; s.pos.z = start.z; s.yaw = Math.atan2(n.x, n.z); s.pitch = -0.1;
      const moved = v.probe.walk(Math.atan2(n.x, n.z) * 180 / Math.PI, metres), rel = new V3(s.pos.x - c.x, 0, s.pos.z - c.z);
      return { id: p.id, side, back, metres, moved, gap: rel.dot(n) - half };
    }
    const holds = (q: any, x: number, z: number) => { const { c, ax, az } = frame(q), dx = x - c.x, dz = z - c.z; return Math.abs(dx * ax.x + dz * ax.z) < q.w / 2 && Math.abs(dx * az.x + dz * az.z) < q.d / 2; };
    const holding = () => F.pieces().filter((q: any) => q.blocking && q.floor === s.floor.key && spans(q) && holds(q, s.pos.x, s.pos.z)).map((q: any) => q.id);
    function leave() {
      const x0 = s.pos.x, z0 = s.pos.z; let best = 0;
      for (let deg = 0; deg < 360; deg += 45) { s.pos.x = x0; s.pos.z = z0; best = Math.max(best, v.probe.walk(deg, 1.5)); }
      s.pos.x = x0; s.pos.z = z0;
      return best;
    }
    function only(ids: string[], fn: () => number) {
      const col = w.__host.FL[s.floor.key].colliders, keep = col.slice();
      col.length = 0; col.push(...keep.filter((m: any) => !m.name.startsWith('furn:') || ids.includes(m.userData.id)));
      try { return fn(); } finally { col.length = 0; col.push(...keep); }
    }
    function verdict() {
      const inside = holding();
      if (!inside.length) return { class: 'A', inside };
      const best = leave();
      if (best >= 1.0) return { class: 'A', inside, best };
      const base = only([], leave), alone = only(inside, leave);
      return { class: alone + 0.3 < Math.min(1.0, base) ? 'C' : 'B', inside, best, alone, base };
    }
    function spawn(id: string) {
      const p = F.pieces().find((q: any) => q.id === id), f = w.__host.floors.find((x: any) => x.key === p.floor);
      v.setMode('orbit'); v.setMode('walk', { floor: f, point: new V3(p.x, 0, -p.y) });
      return p;
    }
    function standIn(id: string) { const p = spawn(id); s.pos.x = p.x; s.pos.z = -p.y; return p; }
    // ---- the plan pictures (hotel)
    const pic = (key: string) => w.__host.pictures.objs.find((o: any) => o.userData.key === key);
    function pixels(m: any) {
      if (!m.userData.pixels) {
        const img = m.material.map.image, c = document.createElement('canvas');
        c.width = img.naturalWidth; c.height = img.naturalHeight;
        const g = c.getContext('2d')!; g.drawImage(img, 0, 0);
        m.userData.pixels = g.getImageData(0, 0, c.width, c.height).data;
      }
      return m.userData.pixels;
    }
    function lumAt(key: string, x: number, y: number) {
      const m = pic(key), [W, H] = m.userData.size;
      ray.set(new V3(x, levelOf(key) + 1, -y), new V3(0, -1, 0)); ray.far = 2;
      const hit = ray.intersectObject(m, false)[0];
      if (!hit || !hit.uv) return null;
      const px = Math.min(W - 1, Math.floor(hit.uv.x * W)), py = Math.min(H - 1, Math.floor((1 - hit.uv.y) * H)), d = pixels(m), i = (py * W + px) * 4;
      return 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    }
    function wallCorners(key: string) {
      const out: any[] = [];
      for (const p of w.__host.model.parts) {
        if (p.floor !== key || p.kind !== 'wall') continue;
        [p.o, ...p.h].forEach((ring: any[], ri: number) => {
          const n = ring.length; let area = 0;
          for (let i = 0; i < n; i++) { const a = ring[i], b = ring[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
          for (let i = 0; i < n; i++) {
            const a = ring[(i - 1 + n) % n], b = ring[i], c = ring[(i + 1) % n];
            const e1 = [b[0] - a[0], b[1] - a[1]], e2 = [c[0] - b[0], c[1] - b[1]], l1 = Math.hypot(e1[0]!, e1[1]!), l2 = Math.hypot(e2[0]!, e2[1]!);
            if (l1 < 0.15 || l2 < 0.15) continue;
            let convex = (e1[0]! * e2[1]! - e1[1]! * e2[0]! > 0) === (area > 0);
            if (ri > 0) convex = !convex;
            const ang = Math.acos(Math.max(-1, Math.min(1, -(e1[0]! * e2[0]! + e1[1]! * e2[1]!) / (l1 * l2)))) * 180 / Math.PI;
            if (!convex || ang < 60 || ang > 120) continue;
            const bx = -e1[0]! / l1 + e2[0]! / l2, by = -e1[1]! / l1 + e2[1]! / l2; const bl = Math.hypot(bx, by);
            out.push({ at: b, into: [bx / bl, by / bl] });
          }
        });
      }
      return out;
    }
    function lineUp(key: string, dx = 0, dy = 0) {
      const out: any = { n: 0, ok: 0, misses: [] };
      for (const c of wallCorners(key)) {
        const [x, y] = c.at, [bx, by] = c.into;
        const a = lumAt(key, x + bx * 0.06 + dx, y + by * 0.06 + dy), b = lumAt(key, x - bx * 0.15 + dx, y - by * 0.15 + dy);
        if (a === null || b === null) continue;
        out.n++;
        if (a <= b - 30) out.ok++; else if (!dx && !dy) out.misses.push({ at: [Math.round(x * 100) / 100, Math.round(y * 100) / 100], wall: Math.round(a), beside: Math.round(b) });
      }
      out.share = out.n ? Math.round(out.ok / out.n * 1000) / 1000 : 0;
      return out;
    }
    const wallCache: Record<string, any[]> = {}, spotCache: Record<string, number[][]> = {};
    const wallsOf = (key: string) => wallCache[key] || (wallCache[key] = w.__host.model.parts.filter((p: any) => p.floor === key && p.kind === 'wall').map((p: any) => {
      const xs = p.o.map((q: number[]) => q[0]), ys = p.o.map((q: number[]) => q[1]);
      return { rings: [p.o, ...p.h], box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] }; }));
    function inWall(key: string, x: number, y: number) {
      for (const wl of wallsOf(key)) {
        if (x < wl.box[0] || x > wl.box[2] || y < wl.box[1] || y > wl.box[3]) continue;
        let c = false;
        for (const ring of wl.rings) for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const [xi, yi] = ring[i], [xj, yj] = ring[j]; if ((yi > y) !== (yj > y) && x < xi + (y - yi) * (xj - xi) / (yj - yi)) c = !c; }
        if (c) return true;
      }
      return false;
    }
    function faceSpots(key: string) {
      if (spotCache[key]) return spotCache[key]!;
      const out: number[][] = [];
      for (const wl of wallsOf(key)) for (const ring of wl.rings) for (let i = 0; i < ring.length; i++) {
        const a = ring[i], b = ring[(i + 1) % ring.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (L < 0.1) continue;
        const ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L, nx = -uy, ny = ux;
        for (let k = 1; k * 0.05 < L - 0.02; k++) {
          const t = k * 0.05, qx = a[0] + ux * t, qy = a[1] + uy * t;
          const l = inWall(key, qx + nx * 0.04, qy + ny * 0.04), r = inWall(key, qx - nx * 0.04, qy - ny * 0.04);
          if (l === r) continue;
          const sx = l ? nx : -nx, sy = l ? ny : -ny;
          if (inWall(key, qx - sx * 0.12, qy - sy * 0.12)) continue;
          out.push([qx + sx * 0.04, qy + sy * 0.04, qx - sx * 0.12, qy - sy * 0.12]);
        }
      }
      return (spotCache[key] = out);
    }
    function faceLineUp(key: string, dx = 0, dy = 0) {
      let n = 0, sum = 0, dark = 0;
      for (const [ix, iy, ox, oy] of faceSpots(key)) {
        const a = lumAt(key, ix! + dx, iy! + dy), b = lumAt(key, ox! + dx, oy! + dy);
        if (a === null || b === null) continue;
        n++; sum += b - a; if (a <= b - 30) dark++;
      }
      return { by: [dx, dy], n, contrast: n ? Math.round(sum / n * 10) / 10 : 0, share: n ? Math.round(dark / n * 1000) / 1000 : 0 };
    }
    w.__t = { THREE, frame, lane, walk, walkTo, targets, crossable, near, stoppedBy, topSpots, reach, span, hoverSpots, along, levelOf, holding, leave, only, verdict, spawn, standIn, lumAt, wallCorners, lineUp, faceSpots, faceLineUp };
    return true;
  });
}

// Prototype adapter (DESIGN.md 17.4; WORK_BREAKDOWN S.9), installed after load on the prototype pages only:
// * window.__walkthrough = { THREE (the TestHookThree subset, from the page's import map), viewer: null, version, live,
//   created, gpu } so ported checks use __walkthrough.THREE on both targets;
// * __host.openings and __host.probes in the v1 shapes: the suite's `doors` / `glassWestX, glassWestY` and the house's
//   per-floor openings become flat v1 records (DESIGN.md 6.3, 6.4);
// * __host.FL for a page that lacks it (built from __host.floors, model levels).
// Idempotent. Scaffold; read-only for builders.
import type { Page } from '@playwright/test';

export async function installPrototypeShim(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const w = window as unknown as Record<string, any>;
    if (w.__walkthrough && w.__walkthrough.shim) return;
    const T: any = await import(/* @vite-ignore */ 'three' as string);
    w.__walkthrough = {
      shim: true,
      THREE: { Vector2: T.Vector2, Vector3: T.Vector3, Raycaster: T.Raycaster, Box3: T.Box3, Plane: T.Plane, Matrix4: T.Matrix4,
        Quaternion: T.Quaternion, Euler: T.Euler, MathUtils: T.MathUtils, Color: T.Color },
      viewer: null,
      version: 'prototype',
      live: () => 1,
      created: () => 1,
      gpu: () => ({ geometries: -1, textures: -1, programs: -1 }),
    };
    const h = w.__host;
    if (!h) return;

    // the suite (presidential_test): doors -> v1 openings, the west glass -> a v1 probe (DESIGN.md 6.3)
    if (Array.isArray(h.doors) && !Array.isArray(h.openings)) {
      h.openings = h.doors.map((d: any) => {
        const o: Record<string, unknown> = { id: d.id, floor: 'suite', kind: String(d.id).startsWith('D') ? 'door' : 'passage', label: d.name,
          x: d.x, y: d.y, nx: d.nx, ny: d.ny, width: d.width };
        if (d.exterior) o.exterior = true;
        return o;
      });
    }
    if (typeof h.glassWestX === 'number' && !Array.isArray(h.probes)) {
      h.probes = [{ floor: 'suite', id: 'suite-glass-west', what: 'glass facade', x: h.glassWestX, y: h.glassWestY, nx: 1, ny: 0, inside: [1],
        label: "the living room's west glass (its room-side face)" }];
    }

    // the house (cad_test): openings per floor -> flat v1 records, lintel true/false -> 'lintel' / null (DESIGN.md 6.4)
    if (h.openings && !Array.isArray(h.openings) && typeof h.openings === 'object') {
      const perFloor = h.openings as Record<string, any[]>;
      h.openingsByFloor = perFloor;
      const order: string[] = Array.isArray(h.floors) ? h.floors.map((f: any) => f.key) : Object.keys(perFloor);
      h.openings = order.flatMap(k => (perFloor[k] || []).map((o: any) => {
        const { id, lintel, ...rest } = o;
        return { id, floor: k, ...rest, lintel: lintel ? 'lintel' : null };
      }));
    }
    if (!Array.isArray(h.probes)) h.probes = [];

    // __host.FL (model levels) for a page without it
    if (!h.FL && Array.isArray(h.floors)) {
      h.FL = Object.fromEntries(h.floors.map((f: any) => [f.key, { key: f.key, name: f.name, level: f.level, group: f.group,
        colliders: f.colliders, walkables: f.walkables, late: f.late || [], rise: f.rise || [] }]));
    }
  });
}

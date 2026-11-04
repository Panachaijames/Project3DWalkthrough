import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'fs';
const D = JSON.parse(fs.readFileSync('srisawan3d_merged.json', 'utf8'));
let problems = 0;
for (const [key, rings] of Object.entries(D.solids)) {
  if (!rings.length) continue;
  const [floor, kind] = key.split(':');
  const z0 = D.levels[floor], h = D.heights[floor];
  const parts = rings.map(r => {
    const shape = new THREE.Shape(r.o.map(([x, y]) => new THREE.Vector2(x, y)));
    for (const hole of r.h) shape.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
    const g = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: false, curveSegments: 1 });
    g.rotateX(-Math.PI / 2); g.translate(0, z0, 0); return g;
  });
  const m = mergeGeometries(parts, false);
  if (!m) { console.log(key, 'MERGE FAILED'); problems++; continue; }
  const e = new THREE.EdgesGeometry(m, 20);
  m.computeBoundingBox();
  const b = m.boundingBox, pos = m.attributes.position.array;
  const nan = pos.some(v => !Number.isFinite(v));
  const tris = pos.length / 9;
  const okY = Math.abs(b.min.y - z0) < 1e-4 && Math.abs(b.max.y - (z0 + h)) < 1e-4;
  if (nan || !okY || tris === 0) problems++;
  console.log(`${key.padEnd(12)} solids ${String(rings.length).padStart(3)}  triangles ${String(tris).padStart(6)}  edges ${String(e.attributes.position.count / 2).padStart(5)}  y ${b.min.y.toFixed(2)}..${b.max.y.toFixed(2)}  x ${b.min.x.toFixed(1)}..${b.max.x.toFixed(1)}  z ${b.min.z.toFixed(1)}..${b.max.z.toFixed(1)}${nan ? '  NaN!' : ''}${okY ? '' : '  HEIGHT WRONG'}`);
}
for (const [floor, sl] of Object.entries(D.slabs)) {
  const shape = new THREE.Shape(sl.outer.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of sl.holes) shape.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(shape, { depth: 0.25, bevelEnabled: false });
  g.rotateX(-Math.PI / 2); g.translate(0, sl.z, 0); g.computeBoundingBox();
  console.log(`slab ${floor}: triangles ${g.attributes.position.count / 3}, holes ${sl.holes.length}, y ${g.boundingBox.min.y.toFixed(2)}..${g.boundingBox.max.y.toFixed(2)}`);
}
console.log(problems ? `PROBLEMS: ${problems}` : 'ALL GEOMETRY BUILT OK');

import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'fs';
const D = JSON.parse(fs.readFileSync('house3d_merged.json', 'utf8'));
let bad = 0;
for (const [key, rings] of Object.entries(D.solids)) {
  if (!rings.length) continue;
  const [floor, kind] = key.split(':');
  const z0 = D.levels[floor], top = D.tops[floor];
  const h = kind === 'single' ? 1.0 : kind === 'glass' ? (top - z0) - 0.6 : (top - z0);
  const parts = rings.map(r => { const s = new THREE.Shape(r.o.map(([x, y]) => new THREE.Vector2(x, y)));
    for (const hole of r.h) s.holes.push(new THREE.Path(hole.map(([x, y]) => new THREE.Vector2(x, y))));
    const g = new THREE.ExtrudeGeometry(s, { depth: h, bevelEnabled: false, curveSegments: 1 }); g.rotateX(-Math.PI / 2); g.translate(0, z0, 0); return g; });
  const m = mergeGeometries(parts, false); if (!m) { bad++; console.log(key, 'merge failed'); continue; }
  m.computeBoundingBox(); const b = m.boundingBox; const nan = m.attributes.position.array.some(v => !Number.isFinite(v));
  if (nan) bad++;
  console.log(`${key.padEnd(14)} solids ${String(rings.length).padStart(3)}  y ${b.min.y.toFixed(2)}..${b.max.y.toFixed(2)}${nan ? '  NaN!' : ''}`);
}
console.log(bad ? 'PROBLEMS ' + bad : 'ALL CAD GEOMETRY BUILT OK');

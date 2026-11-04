import * as THREE from 'three';
import { mergeGeometries, toCreasedNormals } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import fs from 'fs';
function build(file, edgeAngle, crease) {
  const D = JSON.parse(fs.readFileSync(file, 'utf8')); let edges = 0, tris = 0, bad = 0;
  for (const [key, rings] of Object.entries(D.solids)) {
    if (!rings.length || !key.startsWith('L2')) continue;
    const [floor] = key.split(':');
    const parts = rings.map(r => { const s = new THREE.Shape(r.o.map(([x, y]) => new THREE.Vector2(x, y)));
      for (const h of r.h) s.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
      const g = new THREE.ExtrudeGeometry(s, { depth: D.heights[floor], bevelEnabled: false, curveSegments: 1 });
      g.rotateX(-Math.PI / 2); g.translate(0, D.levels[floor], 0); return g; });
    const m = mergeGeometries(parts, false);
    const shaded = crease ? toCreasedNormals(m, THREE.MathUtils.degToRad(40)) : m;
    if (shaded.attributes.normal.array.some(v => !Number.isFinite(v))) bad++;
    const ep = new THREE.EdgesGeometry(m, edgeAngle).attributes.position.array;
    for (let i = 0; i < ep.length; i += 6) if (Math.abs(ep[i + 1] - ep[i + 4]) > 0.5) edges++;
    tris += shaded.attributes.position.count / 3;
  }
  return { edges, tris, bad };
}
const before = build('srisawan3d_merged_before_smooth.json', 20, false), after = build('srisawan3d_merged.json', 40, true);
console.log('floor 2 before: vertical edge lines', before.edges, '| triangles', before.tris);
console.log('floor 2 after : vertical edge lines', after.edges, '| triangles', after.tris, '| bad normals', after.bad);
console.log(after.bad ? 'PROBLEM' : 'SMOOTH SHADING BUILT OK');

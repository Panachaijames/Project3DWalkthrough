// ---------------------------------------------------------------------------
// The chair, as both pages here use it (pasted into chair_test.html and chair_compare.html by make_chair_test.mjs).
// Needs in scope: THREE, GLTFLoader, mergeVertices, toCreasedNormals, and the embedded GLB_B64 (Chair.glb) and SLIM
// (chair_slim.json from slim_chair.mjs).
//   loadFullChair()      Chair.glb through three's GLTFLoader, put at the origin (below); its parts with their matrices
//   slimChairGeometry()  the slimmed chair: positions + indices, its normals worked out again
// ---------------------------------------------------------------------------
const bytesOf = s => { const bin = atob(s), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; };

// The export kept the chair where it stood in its Max scene: every root node has the same matrix, a uniform 0.38 scale, the
// Z-up -> Y-up turn, a turn of about 60 degrees about the vertical and a position about 26 m from the origin. Here the turn about
// the vertical and the position are undone (the Z-up -> Y-up turn and the scale stay), then the footprint is centred on the
// origin and the base put at y = 0. The chair then faces +z (its seat front; plan -y), real size in metres.
async function loadFullChair() {
  const gltf = await new GLTFLoader().parseAsync(bytesOf(GLB_B64).buffer, '');
  const root = gltf.scene, UP = new THREE.Vector3(0, 1, 0), undone = [];
  for (const node of root.children) {
    const ex = new THREE.Vector3(1, 0, 0).applyQuaternion(node.quaternion);     // the model's own x axis: level once Z-up is Y-up
    const yaw = Math.atan2(-ex.z, ex.x);
    undone.push({ turnDeg: yaw * 180 / Math.PI, position: node.position.toArray() });
    node.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(UP, -yaw));
    node.position.set(0, 0, 0);
  }
  root.updateMatrixWorld(true);
  const bb = new THREE.Box3().setFromObject(root, true);
  const shift = new THREE.Matrix4().makeTranslation(-(bb.min.x + bb.max.x) / 2, -bb.min.y, -(bb.min.z + bb.max.z) / 2);
  const parts = [];
  root.traverse(o => {
    if (!o.isMesh) return;
    const g = o.geometry, triangles = (g.index ? g.index.count : g.attributes.position.count) / 3;
    g.computeBoundingSphere();
    parts.push({ name: o.name, geometry: g, matrix: shift.clone().multiply(o.matrixWorld), triangles, exportMaterial: o.material });
  });
  return {
    parts, undone, size: bb.getSize(new THREE.Vector3()),
    triangles: parts.reduce((a, p) => a + p.triangles, 0),
    vertices: parts.reduce((a, p) => a + p.geometry.attributes.position.count, 0),
    attributes: [...new Set(parts.flatMap(p => Object.keys(p.geometry.attributes)))],
    materials: [...new Set(parts.map(p => p.exportMaterial))].map(m => ({ name: m.name, colour: '#' + m.color.getHexString() })),
  };
}

// The slimmed chair (made at the origin by slim_chair.mjs). Its normals are worked out here: smooth across edges flatter than
// `crease` degrees, sharp across the others. three's toCreasedNormals matches corners to 1/100 of a unit, so it runs in mm.
function slimChairGeometry(crease = 40) {
  const s = SLIM.slim, g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bytesOf(s.positions).buffer), 3));
  g.setIndex(new THREE.BufferAttribute(s.indexType === 'uint16' ? new Uint16Array(bytesOf(s.indices).buffer) : new Uint32Array(bytesOf(s.indices).buffer), 1));
  g.scale(1000, 1000, 1000);
  const flat = toCreasedNormals(g, crease * Math.PI / 180);
  flat.scale(0.001, 0.001, 0.001);
  const out = mergeVertices(flat);                               // indexed again: a corner is shared unless its normals differ
  out.computeBoundingSphere(); out.computeBoundingBox();
  g.dispose(); flat.dispose();
  return out;
}

// Per-mesh three-mesh-bvh, no prototype patching (DESIGN.md 18.16). Owner: builder A.
// The pages set THREE.BufferGeometry.prototype.computeBoundsTree and THREE.Mesh.prototype.raycast for the whole page; the
// viewer gives each collider, walkable and box its own BVH and raycast instead, so a host page's own three.js objects are
// left alone. (MeshBVH adds an index to a non-indexed geometry; the positions keep their order.)
import { MeshBVH, acceleratedRaycast } from 'three-mesh-bvh';
import type { WithBvh } from '../contracts';

export const withBvh: WithBvh = mesh => {
  mesh.geometry.boundsTree = new MeshBVH(mesh.geometry);
  mesh.raycast = acceleratedRaycast;
  return mesh;
};

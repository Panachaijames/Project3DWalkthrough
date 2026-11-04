// Scaffold smoke page: three.js and three-mesh-bvh, bundled from npm (no CDN), draw one red box into a WebGL canvas and
// read the middle pixel back; a BVH raycast hits the box. The result goes to window.__smoke for webgl.spec.ts.
import { BoxGeometry, Mesh, MeshBasicMaterial, PerspectiveCamera, Raycaster, REVISION, Scene, Vector3, WebGLRenderer } from 'three';
import { MeshBVH, acceleratedRaycast } from 'three-mesh-bvh';

interface SmokeResult {
  revision: string;
  pixel: [number, number, number, number];
  clear: [number, number, number, number];
  bvhHit: number | null;
  renderer: string;
}
declare global { interface Window { __smoke?: SmokeResult | { error: string } } }

try {
  const host = document.getElementById('app')!;
  const renderer = new WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(host.clientWidth, host.clientHeight);
  renderer.setClearColor(0xeef0f2, 1);
  host.append(renderer.domElement);

  const scene = new Scene();
  const camera = new PerspectiveCamera(40, host.clientWidth / host.clientHeight, 0.1, 100);
  camera.position.set(0, 0, 5);
  camera.lookAt(0, 0, 0);
  const geometry = new BoxGeometry(2, 2, 2);
  const mesh = new Mesh(geometry, new MeshBasicMaterial({ color: 0xff0000 }));
  scene.add(mesh);
  renderer.render(scene, camera);

  const gl = renderer.getContext();
  const read = (x: number, y: number): [number, number, number, number] => {
    const px = new Uint8Array(4);
    gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    return [px[0]!, px[1]!, px[2]!, px[3]!];
  };
  const w = gl.drawingBufferWidth;
  const h = gl.drawingBufferHeight;

  geometry.boundsTree = new MeshBVH(geometry);
  mesh.raycast = acceleratedRaycast;
  const ray = new Raycaster(new Vector3(0, 0, 5), new Vector3(0, 0, -1));
  const hit = ray.intersectObject(mesh)[0];

  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  window.__smoke = {
    revision: REVISION,
    pixel: read(Math.floor(w / 2), Math.floor(h / 2)),
    clear: read(2, 2),
    bvhHit: hit ? hit.distance : null,
    renderer: String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)),
  };
} catch (err) {
  window.__smoke = { error: String(err) };
}

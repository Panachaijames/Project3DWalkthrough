// Plan pictures (DESIGN.md 5.7): the hotel page's sheets (hotel_test/src/make_html.py rules 1 - 3). Owner: builder A.
// Each floor with a pictureFrame and a picture URL gets one flat sheet, 0.005 m above its floor level, the whole picture at
// the model's scale and position, unlit (the drawing's own colours) and drawn in front of the slab. The sheets live in a
// scene-level group 'plan pictures', not in the floor groups, so Walk, the boxes, the double-click and the room names never
// see them; a sheet shows while the Picture tick is on and its floor group shows (sync, every frame), and lies at its floor's
// level setting (its y follows the floor group's). Image loads are aborted on dispose (a late onload does nothing).
import { Group, Mesh, MeshBasicMaterial, PlaneGeometry, SRGBColorSpace, Texture } from 'three';
import type { CreatePictures, PicturesApi } from '../contracts';

export const PICTURE_LIFT = 0.005;

/** An http(s) URL (absolute, or relative to the page): loaded with crossOrigin 'anonymous'. data: and blob: URLs are not. */
export function needsCors(url: string): boolean {
  return !/^(data|blob):/i.test(url.trim());
}

export const createPictures: CreatePictures = ctx => {
  const { model } = ctx;
  const urls = ctx.project.pictures ?? {};
  const frames = model.pictureFrame ?? {};
  const todo = ctx.floors.filter(f => frames[f.key] && urls[f.key]);
  if (!todo.length) return null;

  const layer = new Group();
  layer.name = 'plan pictures';
  ctx.scene.add(layer);
  const sheets: Mesh[] = [];
  const src: Partial<Record<string, string>> = {};
  const loads: Promise<boolean>[] = [];
  let maxAniso = 1;
  try { maxAniso = ctx.renderer.capabilities.getMaxAnisotropy(); } catch { /* a stub renderer */ }

  for (const f of todo) {
    const pf = frames[f.key]!, url = urls[f.key]!;
    const [W, H] = pf.size, kx = pf.pxPerMetreX, ky = pf.pxPerMetreY, [ox, oy] = pf.originPx;
    // the sheet's middle in plan: pixel (W / 2, H / 2) through the frame; its size: the picture's pixels at the floor's scale, per axis
    const w = W / kx, h = H / ky, cx = (W / 2 - ox) / kx - model.offset[0], cy = -(H / 2 - oy) / ky - model.offset[1];
    const g = new PlaneGeometry(w, h);                  // uv (0, 1) = the picture's top left, which lies to the north-west
    g.rotateX(-Math.PI / 2);
    g.translate(cx, f.modelLevel + PICTURE_LIFT, -cy);
    const tex = ctx.disposer.track(new Texture());
    tex.colorSpace = SRGBColorSpace;
    tex.anisotropy = maxAniso;
    const mesh = new Mesh(g, new MeshBasicMaterial({ map: tex, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
    mesh.name = `${f.key} plan picture`;
    mesh.userData = { key: f.key, size: [W, H], metres: [w, h], centre: [cx, cy] };
    mesh.visible = false;
    mesh.position.y = f.group.position.y;
    layer.add(mesh);
    sheets.push(mesh);
    src[f.key] = url;
    loads.push(new Promise<boolean>(resolve => {
      if (typeof Image === 'undefined') { resolve(false); return; }
      const img = new Image();
      let settled = false;
      const done = (ok: boolean) => { if (settled) return; settled = true; img.onload = null; img.onerror = null; resolve(ok); };
      img.onload = () => {
        if (ctx.disposer.disposed) { done(false); return; }
        tex.image = img;
        tex.needsUpdate = true;
        done(true);
      };
      img.onerror = () => {
        if (!ctx.disposer.disposed) console.error(`plan picture ${f.key} could not be read`);
        done(false);
      };
      ctx.disposer.add(() => { if (!settled) { done(false); img.removeAttribute('src'); } });
      // A picture on another origin (VITE_API_BASE elsewhere, a signed object-store URL later) must be loaded in CORS mode:
      // WebGL refuses an image loaded without it even when the server allows every origin, and the sheet stayed empty
      // while `ready` said true. In CORS mode a server that does not allow us fails the load (onerror: ready false).
      // Same-origin and data: URLs load as before (fix step, review finding "code" 8).
      if (needsCors(url)) img.crossOrigin = 'anonymous';
      img.src = url;
    }));
  }

  const toggles = () => ctx.visibility.toggles;
  const api: PicturesApi = {
    sheets,
    ready: Promise.all(loads),
    src,
    sync() {
      const on = toggles().picture;
      for (const m of sheets) {
        const f = ctx.floorByKey.get(m.userData.key as string);
        if (!f) continue;
        m.visible = on && f.group.visible;
        m.position.y = f.group.position.y;
      }
    },
  };
  return api;
};

// Photos (DESIGN.md 12 "Photos", 13 "Photos"): port of viewer_modes.js "photos". The picture is drawn in screen-sized
// tiles at pixel ratio 1 and stitched on a 2D canvas, so even a 4K photo needs no more graphics memory than the screen;
// a flash, a thumbnail (the newest 12), the `photo` event, and the download through ctx.options.download unless
// nodownload. Owner: builder B.
import type { ModesState, PhotoName, PhotoResult, ViewerContext } from '../contracts';
import { el } from '../ui/dom';
import { outSize } from './camera';
import { FLASH_FROM, FLASH_MS, THUMBNAILS } from './state';

const pad = (n: number) => String(n).padStart(2, '0');

/** `<photoName>_<Orbit|Walk|Ghost>_<overview|floor name>_<lens>mm_<YYYY-MM-DD_HH-MM-SS>.png`, `[^\w.-]+` -> `-`. */
export const photoName: PhotoName = (project, mode, where, lensMm, now) => {
  const m = mode === 'orbit' ? 'Orbit' : mode === 'walk' ? 'Walk' : 'Ghost';
  const stamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
  return `${project}_${m}_${where}_${Math.round(lensMm)}mm_${stamp}.png`.replace(/[^\w.-]+/g, '-');
};

export interface PhotoDeps {
  /** The photo frame now (root-relative CSS px). */
  frameRect(): { x: number; y: number; w: number; h: number };
  /** The straight-verticals shift now (CSS px). */
  shift(): number;
  applyProjection(): void;
  applyCamera(): void;
  /** 'overview' in Orbit, else the name of the floor you are on (Ghost: the 0.3 m rule). */
  where(): string;
  drawFrame(): void;
  flash: HTMLElement;
  photos: HTMLElement;
}

export interface Photos {
  takePhoto(): Promise<PhotoResult | null>;
}

export function createPhotos(ctx: ViewerContext, s: ModesState, deps: PhotoDeps): Photos {
  const saved = new WeakMap<Element, { blob: Blob; name: string }>();
  const download = (blob: Blob, name: string) => ctx.options.download(blob, name);

  // A thumbnail's click saves it again (one listener for all of them).
  ctx.disposer.listen(deps.photos, 'click', e => {
    const img = e.target instanceof Element ? e.target.closest('img') : null;
    const item = img ? saved.get(img) : undefined;
    if (!item) return;
    try { download(item.blob, item.name); } catch (err) { ctx.reportError(err); }
  });

  /** A failure while drawing comes back as a rejected promise, never as a throw. */
  function takePhoto(): Promise<PhotoResult | null> {
    try {
      return shoot();
    } catch (err) {
      return Promise.reject(err);
    }
  }

  function shoot(): Promise<PhotoResult | null> {
    const { width: cw, height: ch } = ctx.size();
    if (s.locked || !cw || !ch) return Promise.resolve(null);
    // What you see is what you get: the frame only applies while the Camera panel (and so the frame) is showing.
    const r = s.camOpen ? deps.frameRect() : { x: 0, y: 0, w: cw, h: ch }, size = outSize(r, s.size);
    if (s.mode === 'orbit') ctx.controls.update(); else deps.applyCamera();
    deps.applyProjection();
    const camera = ctx.camera, renderer = ctx.renderer, canvas = ctx.canvas;
    const out = document.createElement('canvas');
    out.width = size.w; out.height = size.h;
    const g = out.getContext('2d');
    if (!g) throw new Error('the photo could not be made (no 2D canvas)');
    const k = size.w / r.w, shift = deps.shift(), pr = renderer.getPixelRatio();
    renderer.setPixelRatio(1);                 // the drawing buffer becomes cw x ch: one tile
    try {
      for (let ty = 0; ty < size.h; ty += ch) {
        for (let tx = 0; tx < size.w; tx += cw) {
          const w = Math.min(cw, size.w - tx), h = Math.min(ch, size.h - ty);
          camera.setViewOffset(cw * k, ch * k, r.x * k + tx, (r.y + shift) * k + ty, w, h);
          camera.updateProjectionMatrix();
          renderer.setViewport(0, ch - h, w, h);
          renderer.render(ctx.scene, camera);
          g.drawImage(canvas, 0, 0, w, h, tx, ty, w, h);
        }
      }
    } finally {
      renderer.setPixelRatio(pr);              // back to the screen's own buffer (this also resets the viewport)
      deps.applyProjection();
    }
    renderer.render(ctx.scene, camera);
    if (typeof deps.flash.animate === 'function') {
      deps.flash.animate([{ opacity: FLASH_FROM }, { opacity: 0 }], { duration: FLASH_MS, easing: 'ease-out' });
    }
    const name = photoName(ctx.model.photoName, s.mode, deps.where(), s.mode === 'orbit' ? s.orbitLens : s.lens, new Date());
    return new Promise<Blob>((res, rej) => out.toBlob(b => (b ? res(b) : rej(new Error('the photo could not be saved'))), 'image/png')).then(blob => {
      const result: PhotoResult = { name, width: size.w, height: size.h };
      if (ctx.disposer.disposed) return result;
      const u = ctx.disposer.objectUrl(URL.createObjectURL(blob));
      const img = el('img', { title: `${name} (${size.w} x ${size.h}) - click to save again`, attrs: { src: u } });
      saved.set(img, { blob, name });
      deps.photos.prepend(img);
      while (deps.photos.children.length > THUMBNAILS) {
        const old = deps.photos.lastElementChild as HTMLImageElement;
        URL.revokeObjectURL(old.src);
        old.remove();
      }
      deps.drawFrame();                        // the panel may have grown
      if (!s.noDownload && !ctx.options.noDownload) download(blob, name);
      try { ctx.events.emit('photo', result); } catch (err) { ctx.reportError(err); }
      return result;
    });
  }

  return { takePhoto };
}

// The modes' DOM (DESIGN.md 11.6, 12 "Mode buttons row, HUD, cross, photo frame, flash, stick, Up/Down, Camera panel",
// "updateHud", "Camera panel sync, frame drawing, setLens, openCam"): port of viewer_modes.js "UI" and "camera panel".
// Plain DOM through ui/dom.ts el() (text only, CSSOM styles): the modes row goes into the panel's slot `modes`, the
// overlays are absolute children of the root; body classes become root flags (ctx.ui.setFlag); active buttons carry
// aria-pressed="true"; the selectors are D-11.6's; the texts are the prototype's, word for word. Screen maths is
// root-relative (ctx.size(), ctx.rectOf()). Owner: builder B.
import type { FloorRecord, ModesState, PhotoFrame, ViewerContext, ViewMode } from '../contracts';
import { clear, el } from '../ui/dom';
import { frameRect, outSize, type Projection } from './camera';
import { MODES_CSS } from './css';
import { CROWDED_PANELS, CROWDED_SHARE, D2R, LENS_MAX, LENS_MIN, LENS_PRESETS } from './state';

/** The Frame list: value, text. */
export const FRAME_OPTIONS: [PhotoFrame, string][] = [
  ['screen', 'Whole screen'], ['16:9', '16:9'], ['3:2', '3:2'], ['4:3', '4:3'], ['1:1', '1:1'], ['4:5', '4:5'], ['9:16', '9:16'],
];

/** The hint line's four texts (Orbit / first person, mouse / touch). */
export const HINTS = {
  orbit: 'Drag to orbit · right-drag to pan · scroll to zoom · double-click a floor to walk there · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo',
  orbitTouch: 'Drag to orbit · pinch to zoom · Walk or Ghost to look around inside',
  first: 'Click to capture the mouse (Esc frees it, Esc again returns to Orbit) · 1 / 2 / 3: Orbit / Walk / Ghost · P: photo',
  firstTouch: 'Drag to look · stick to move · Exit (top) returns to Orbit',
} as const;

export interface ModesUi {
  label: HTMLDivElement;
  row: HTMLDivElement;
  modeButtons: Record<ViewMode, HTMLButtonElement>;
  camBtn: HTMLButtonElement;
  hud: HTMLDivElement;
  hudT: HTMLSpanElement;
  hudCam: HTMLButtonElement;
  exit: HTMLButtonElement;
  cross: HTMLDivElement;
  frame: HTMLDivElement;
  frameLines: HTMLElement[];
  flash: HTMLDivElement;
  stick: HTMLDivElement;
  knob: HTMLElement;
  ud: HTMLDivElement;
  snap: HTMLButtonElement;
  up: HTMLButtonElement;
  down: HTMLButtonElement;
  cam: HTMLDivElement;
  camClose: HTMLButtonElement;
  lens: HTMLInputElement;
  lensV: HTMLSpanElement;
  presets: HTMLButtonElement[];
  first: HTMLDivElement;
  eye: HTMLInputElement;
  eyeV: HTMLSpanElement;
  tilt: HTMLInputElement;
  tiltV: HTMLSpanElement;
  straight: HTMLInputElement;
  firstNote: HTMLDivElement;
  frameSel: HTMLSelectElement;
  size: HTMLSelectElement;
  px: HTMLSpanElement;
  grid: HTMLInputElement;
  shot: HTMLButtonElement;
  photos: HTMLDivElement;
}

const button = (text: string, wt?: string, attrs: Record<string, string> = {}) =>
  el('button', { wt, text, attrs: { type: 'button', ...attrs } });
const range = (wt: string, min: string, max: string, step: string) =>
  el('input', { wt, attrs: { type: 'range', min, max, step } });

/** Builds the modes' markup: the row into the panel's slot `modes`, the overlays into the root; adds the CSS chunk. */
export function buildUi(ctx: ViewerContext, s: ModesState): ModesUi {
  ctx.ui.addStyle(MODES_CSS);

  const label = el('div', { cls: 'vm-label', text: 'Look around' });
  const modeButtons: Record<ViewMode, HTMLButtonElement> = {
    orbit: button('Orbit', undefined, { 'data-mode': 'orbit', 'aria-pressed': 'true' }),
    walk: button('Walk', undefined, { 'data-mode': 'walk', 'aria-pressed': 'false' }),
    ghost: button('Ghost', undefined, { 'data-mode': 'ghost', 'aria-pressed': 'false' }),
  };
  const camBtn = button('Camera', 'camera-btn', { 'aria-pressed': 'false' });
  const row = el('div', { cls: 'vm-row', wt: 'modes' }, [modeButtons.orbit, modeButtons.walk, modeButtons.ghost, camBtn]);
  ctx.panel.slot('modes').append(label, row);

  const hudT = el('span', { wt: 'hud-text' });
  const hudCam = el('button', { wt: 'hud-camera', cls: 'vm-narrow', text: 'Camera', attrs: { type: 'button' } });
  const exit = button('Exit', 'exit');
  const hud = el('div', { wt: 'hud' }, [hudT, hudCam, exit]);
  const cross = el('div', { wt: 'cross' });
  const frameLines = [
    el('i', { style: { left: '33.33%', top: '0', bottom: '0', width: '1px' } }),
    el('i', { style: { left: '66.66%', top: '0', bottom: '0', width: '1px' } }),
    el('i', { style: { top: '33.33%', left: '0', right: '0', height: '1px' } }),
    el('i', { style: { top: '66.66%', left: '0', right: '0', height: '1px' } }),
  ];
  const frame = el('div', { wt: 'frame' }, frameLines);
  const flash = el('div', { wt: 'flash' });
  const knob = el('b');
  const stick = el('div', { wt: 'stick' }, [knob]);
  const snap = el('button', { wt: 'snap', text: 'Photo', attrs: { type: 'button' }, style: { display: 'none' } });
  const up = button('', 'up');
  const down = button('', 'down');
  const ud = el('div', { wt: 'updown' }, [snap, up, down]);

  const camClose = el('button', { wt: 'camera-close', text: '×', title: 'Close', attrs: { type: 'button' } });
  const lensV = el('span', { wt: 'lens-value' });
  const lens = range('lens', '12', '85', '1');
  const presets = LENS_PRESETS.map(mm => button(String(mm), 'lens-preset', { 'data-mm': String(mm) }));
  const eyeV = el('span', { wt: 'eye-value' });
  const eye = range('eye', '0.8', '2.2', '0.05');
  const tiltV = el('span', { wt: 'tilt-value' });
  const tilt = range('tilt', '-60', '60', '1');
  const straight = el('input', { wt: 'straight', attrs: { type: 'checkbox' } });
  const first = el('div', { wt: 'first' }, [
    el('div', { cls: 'vm-f' }, [el('div', {}, [el('span', { text: 'Eye height' }), eyeV]), eye]),
    el('div', { cls: 'vm-f' }, [el('div', {}, [el('span', { text: 'Tilt' }), tiltV]), tilt]),
    el('label', {}, [straight, ' Straight verticals']),
  ]);
  const firstNote = el('div', { cls: 'vm-note', wt: 'first-note', text: 'Height and tilt work in Walk and Ghost. In Orbit, drag to set the angle.' });
  const px = el('span', { wt: 'px' });
  const frameSel = el('select', { wt: 'frame-select' }, FRAME_OPTIONS.map(([value, text]) => el('option', { text, attrs: { value } })));
  const size = el('select', { wt: 'size-select' }, [el('option', { text: 'HD', attrs: { value: '1920' } }), el('option', { text: '4K', attrs: { value: '3840' } })]);
  const grid = el('input', { wt: 'grid', attrs: { type: 'checkbox' } });
  const shot = button('Take photo (P)', 'shot');
  const photos = el('div', { wt: 'photos' });
  const cam = el('div', { wt: 'camera-panel' }, [
    el('h2', {}, ['Camera ', camClose]),
    el('div', { cls: 'vm-f' }, [
      el('div', {}, [el('span', { text: 'Lens' }), lensV]),
      lens,
      el('div', { cls: 'vm-row', style: { marginTop: '4px' } }, presets),
    ]),
    first,
    firstNote,
    el('div', { cls: 'vm-f' }, [el('div', {}, [el('span', { text: 'Frame and size' }), px]), el('div', { cls: 'vm-row' }, [frameSel, size])]),
    el('label', {}, [grid, ' Thirds grid']),
    shot,
    photos,
  ]);
  ctx.ui.root.append(hud, cross, frame, flash, stick, ud, cam);

  frameSel.value = s.frame;
  size.value = String(s.size);
  grid.checked = s.grid;
  return {
    label, row, modeButtons, camBtn, hud, hudT, hudCam, exit, cross, frame, frameLines, flash, stick, knob, ud, snap, up, down,
    cam, camClose, lens, lensV, presets, first, eye, eyeV, tilt, tiltV, straight, firstNote, frameSel, size, px, grid, shot, photos,
  };
}

export interface Hud {
  /** Root flags, HUD and hint texts, touch buttons; then bus `mode` (every call, as the prototype's onChange). */
  updateHud(): void;
  syncCamPanel(): void;
  drawFrame(): void;
  /** The photo frame now (root-relative CSS px). */
  frameRect(): { x: number; y: number; w: number; h: number };
  setLens(mm: number | string): void;
  /** Waits for the replay: while modes are locked, open only records camWanted. */
  openCam(open: boolean): void;
  /** aria-pressed on the mode buttons. */
  markModes(): void;
  resetStick(): void;
  /** The tilt read-out while looking around with the Camera panel open. */
  showTilt(): void;
}

export function createHud(ctx: ViewerContext, s: ModesState, ui: ModesUi, proj: Projection, deps: { stackOf(f: FloorRecord): FloorRecord[] }): Hud {
  const hasTouch = () => s.touch || (typeof navigator !== 'undefined' && (navigator.maxTouchPoints ?? 0) > 0);

  const hudText = (title: string, rest: string, more: string) => {
    clear(ui.hudT);
    ui.hudT.append(el('b', { text: title }), rest, el('span', { cls: 'vm-more', text: ` · ${more}` }));
  };

  const frameRectNow = () => frameRect({
    frame: s.frame, camOpen: s.camOpen, mode: s.mode, touch: hasTouch(), narrow: proj.narrow(),
    canvas: ctx.size(),
    camPanel: s.camOpen ? ctx.rectOf(ui.cam) : null,
    sidePanel: s.camOpen ? ctx.rectOf(ctx.panel.el) : null,
  });

  const hud: Hud = {
    updateHud() {
      const fp = s.mode !== 'orbit';
      const width = ctx.size().width;
      ctx.ui.setFlag('fp', fp);
      ctx.ui.setFlag('camopen', s.camOpen);
      // Not enough room for the side panel, the Camera panel and a photo frame between them: hide the side panel.
      ctx.ui.setFlag('crowded', s.camOpen && !proj.narrow() && width - CROWDED_PANELS < width * CROWDED_SHARE);
      ui.hud.style.display = fp ? 'flex' : 'none';
      ui.cross.style.display = fp && !s.camOpen ? 'block' : 'none';
      if (s.mode === 'walk') {
        const more = s.touch ? 'drag to look · stick to move'
          : `drag or click to look · W A S D to move, Shift to run, Space to jump · PgUp / PgDn: other floor · wheel: lens ${Math.round(s.lens)} mm · Esc`;
        hudText('Walk', ` · ${s.floor.name}`, more);
      } else if (s.mode === 'ghost') {
        const more = s.touch ? 'drag to look · stick to fly'
          : `W A S D · Space up, C down · Shift fast · wheel: speed ${s.ghostSpeed.toFixed(1)} m/s · Esc`;
        hudText('Ghost', ' · through walls', more);
      }
      // Touch controls: a stick to move; Upstairs / Downstairs in Walk, hold Up / Down in Ghost.
      const touchOn = fp && s.touch;
      ctx.ui.setFlag('touchui', touchOn);
      ui.stick.style.display = touchOn ? 'block' : 'none';
      ui.ud.style.display = touchOn ? 'flex' : 'none';
      ui.snap.style.display = touchOn && s.camOpen ? 'block' : 'none';     // a shutter button by your thumb while framing
      if (touchOn) {
        const list = deps.stackOf(s.floor), i = list.indexOf(s.floor);
        ui.up.textContent = s.mode === 'walk' ? 'Upstairs' : 'Up';
        ui.down.textContent = s.mode === 'walk' ? 'Downstairs' : 'Down';
        ui.up.classList.toggle('vm-off', s.mode === 'walk' && i >= list.length - 1);
        ui.down.classList.toggle('vm-off', s.mode === 'walk' && i <= 0);
      }
      ctx.ui.hint.textContent = !fp
        ? (s.touch ? HINTS.orbitTouch : HINTS.orbit)
        : (s.touch ? HINTS.firstTouch : HINTS.first);
      try { ctx.bus.emit('mode', { mode: s.mode, floor: s.floor.key }); } catch (err) { ctx.reportError(err); }
    },

    syncCamPanel() {
      const first = s.mode !== 'orbit';
      const lens = first ? s.lens : s.orbitLens;
      ui.lens.value = String(lens);
      ui.lensV.textContent = `${Math.round(lens)} mm · ${Math.round(proj.wideAngle(lens))}° wide`;
      ui.first.classList.toggle('vm-off', !first);
      ui.firstNote.style.display = first ? 'none' : 'block';
      ui.eye.parentElement?.classList.toggle('vm-off', s.mode !== 'walk');
      ui.eye.value = String(s.eye);
      ui.eyeV.textContent = s.eye.toFixed(2) + ' m';
      ui.tilt.value = String(Math.round(s.pitch / D2R));
      ui.tiltV.textContent = Math.round(s.pitch / D2R) + '°';
      ui.straight.checked = s.straight;
      hud.drawFrame();
    },

    drawFrame() {
      if (!s.camOpen) { ui.frame.style.display = 'none'; return; }
      const r = frameRectNow(), crop = s.frame !== 'screen', px = outSize(r, s.size);
      ui.px.textContent = `${px.w} × ${px.h} px`;
      Object.assign(ui.frame.style, { display: crop || s.grid ? 'block' : 'none', left: r.x + 'px', top: r.y + 'px', width: r.w + 'px', height: r.h + 'px' });
      ui.frame.classList.toggle('vm-crop', crop);
      for (const i of ui.frameLines) i.style.display = s.grid ? 'block' : 'none';
    },

    frameRect: frameRectNow,

    setLens(mm) {
      const v = Math.max(LENS_MIN, Math.min(LENS_MAX, Number(mm)));
      if (s.mode === 'orbit') s.orbitLens = v; else s.lens = v;
      proj.applyProjection(); hud.syncCamPanel(); hud.updateHud();
    },

    openCam(open) {
      if (open && s.locked) { s.camWanted = true; return; }   // the build replay is on: open it when the replay ends
      s.camOpen = open;
      ui.cam.style.display = open ? 'block' : 'none';
      ui.camBtn.setAttribute('aria-pressed', String(open));
      hud.updateHud(); hud.syncCamPanel();
    },

    markModes() {
      for (const m of ['orbit', 'walk', 'ghost'] as const) ui.modeButtons[m].setAttribute('aria-pressed', String(m === s.mode));
    },

    resetStick() {
      s.stick = { id: null, x: 0, y: 0 };
      ui.knob.style.transform = '';
    },

    showTilt() {
      if (!s.camOpen) return;
      ui.tilt.value = String(Math.round(s.pitch / D2R));
      ui.tiltV.textContent = Math.round(s.pitch / D2R) + '°';
    },
  };
  return hud;
}

// Selecting a furniture box and deleting it (docs/boxes/DESIGN.md 2.2 - 2.6). Owner: builder C. editBoxes only: without
// the option this module is not installed (no marker, no card, no listener).
//   Orbit      a click on a box (left button, not touch, less than 4 px from where the button went down, the replay not
//              running, the Camera panel closed) selects it; a click on anything else, a second click (detail >= 2: the
//              double-click to walk follows) and Esc clear the selection.
//   Walk,      the box under the crosshair, at most 6 m from the eye, is aimed at (looked for 10 times a second and again
//   Ghost      on the key press itself); Delete removes it, a line at the bottom says so. After such a delete nothing new is
//              aimed at until the view moves (the eye 2 cm, its direction 1°) or AIM_HOLD_MS has passed: a quick second
//              Delete, meant for the same box, never takes the box behind it (review of 17 Nov).
//   Marker     one Group 'furniture-selection' in the scene, never in a floor group or a 'late' list (the replay's fade
//              never reaches it): the unit box 2 cm larger on each side than the selected box, a translucent magenta fill
//              and an outline drawn over everything. It copies the selected mesh's world matrix on select, on every
//              change that moves or resizes the box, and before each frame it is drawn in (onBeforeRender: modules
//              register no frame hooks of their own). It is the viewer's, not the model's: no photo shows it (below).
//   Card       [data-wt=box-card] at the top right (the Camera panel's place; never both): the box's kind, family, size,
//              floor, builder note and id, what stands on it, Delete box (Del) and × ("(Del)" only while the key is armed:
//              below); after a delete "Deleted: ..." with Undo; after a restore of a box that is not showing, where it is.
//              A restored box under a shown floor above it in its stack (pick.ts coverOf: a Level 1 box in Both floors) counts
//              as not showing: no marker drawn through that floor's plate, the card says which floor hides it.
//   Keys       Delete (armed only while the last pointerdown was on the canvas or the card), Ctrl+Z (undo), Esc; never
//              while typing or for another part of the page (modes/input.ts typing(), ours()).
// Every drawing text goes in with textContent (ui/dom.ts el()).
import { BoxGeometry, EdgesGeometry, Group, LineBasicMaterial, LineSegments, Matrix4, Mesh, MeshBasicMaterial, Vector3 } from 'three';
import type { FloorRecord, ViewerContext } from '../contracts';
import { ours, typing } from '../modes/input';
import { clear, el } from '../ui/dom';
import type { HoverApi } from './hover';
import { showing, type Picker } from './pick';
import type { EditEvent, FurnitureState, ItemState, LegendActions, UndoEntry } from './types';

/** The marker's colour: no furniture kind uses it (select.test.ts checks the kinds tables). */
export const MARKER_COLOUR = '#ff2bd6';
/** The marker is this much larger than the box on each side (m). */
export const MARKER_GROW = 0.02;
/** A click selects only when the pointer moved less than this between down and up (px). */
export const CLICK_SLOP = 4;
/** Walk / Ghost: the aimed box is at most this far from the eye (m). */
export const AIM_REACH = 6;
/** Walk / Ghost: the aim is looked for this often (ms). */
export const AIM_MS = 100;
/** Walk / Ghost: after a delete nothing new is aimed at for this long (ms), unless the view moves first. */
export const AIM_HOLD_MS = 500;
/** ... the view has moved: the eye by this much (m), or its direction by this angle (rad). */
export const HOLD_MOVE = 0.02, HOLD_TURN = Math.PI / 180;
/** The card's Delete button: "(Del)" only while the Delete key is armed. */
export const DELETE_ARMED = 'Delete box (Del)', DELETE_DISARMED = 'Delete box';
/** The line at the bottom stays this long (ms), or until the next delete, restore or undo. */
export const TOAST_MS = 6000;

export interface SelectApi {
  /** The id of the selected (Orbit) or aimed (Walk, Ghost) box, or null. */
  selected(): string | null;
  readonly marker: Group;
}

export function installSelect(ctx: ViewerContext, st: FurnitureState, act: LegendActions, pick: Picker, hover: HoverApi): SelectApi {
  const root = ctx.ui.root, canvas = ctx.canvas, modes = () => ctx.modes;
  /** A click may select and a card may show: Orbit, the replay not running, the Camera panel closed. */
  const orbiting = () => modes().mode === 'orbit' && !modes().state.locked && !modes().state.camOpen;
  /** The crosshair aims: Walk or Ghost, the replay not running, the Camera panel closed. */
  const aiming = () => modes().mode !== 'orbit' && !modes().state.locked && !modes().state.camOpen;

  // ---------------------------------------------------------------- the marker
  const unit = ctx.disposer.track(new BoxGeometry(1, 1, 1).translate(0, 0.5, 0));
  const fillMat = ctx.disposer.track(new MeshBasicMaterial({ color: MARKER_COLOUR, transparent: true, opacity: 0.35, depthWrite: false }));
  const lineMat = ctx.disposer.track(new LineBasicMaterial({ color: MARKER_COLOUR, depthTest: false }));
  const fill = new Mesh(unit, fillMat), outline = new LineSegments(ctx.disposer.track(new EdgesGeometry(unit)), lineMat);
  const marker = new Group();
  marker.name = 'furniture-selection';
  marker.visible = false;
  marker.matrixAutoUpdate = false;
  outline.renderOrder = 10;
  for (const part of [fill, outline]) {
    part.frustumCulled = false;                                      // its matrix is set late (below): never culled by an old one
    part.raycast = () => {};                                         // no ray ever meets the marker
    part.onBeforeRender = () => follow(false);
  }
  marker.add(fill, outline);
  ctx.scene.add(marker);
  ctx.disposer.add(() => { ctx.scene.remove(marker); });

  let sel: ItemState | null = null;
  // No photo shows the marker. A photo (modes/photo.ts, whatever started it: P, the shutter, the API, ?shot=1) draws the
  // scene itself, tile by tile, and first sets the drawing buffer's pixel ratio; nothing else does but a resize. So the
  // marker hides from that call until the next turn of the event loop (the photo is drawn within the call that takes it),
  // and the next frame shows it again.
  let hush = false, hushTimer = 0;
  const renderer = ctx.renderer, setPixelRatio = renderer.setPixelRatio;
  renderer.setPixelRatio = (value: number) => {
    hush = true;
    marker.visible = false;
    if (!hushTimer) hushTimer = ctx.disposer.timeout(() => { hushTimer = 0; hush = false; marker.visible = !!sel; }, 0);
    setPixelRatio.call(renderer, value);
  };
  ctx.disposer.add(() => { renderer.setPixelRatio = setPixelRatio; });
  const grow = new Matrix4();
  /** The marker on the selected box: its world matrix, 2 cm larger on each side. `fresh`: the box may just have moved. */
  function follow(fresh: boolean): void {
    const p = sel;
    if (!p) return;
    const m = p.mesh, s = m.scale;
    if (fresh) m.updateWorldMatrix(true, false);
    const sx = s.x > 0 ? 1 + 2 * MARKER_GROW / s.x : 1, sy = s.y > 0 ? 1 + 2 * MARKER_GROW / s.y : 1, sz = s.z > 0 ? 1 + 2 * MARKER_GROW / s.z : 1;
    grow.makeScale(sx, sy, sz).setPosition(0, 0.5 - 0.5 * sy, 0);     // the unit box stands on y = 0: grown about its middle
    marker.matrix.multiplyMatrices(m.matrixWorld, grow);
    marker.matrixWorld.copy(marker.matrix);
    fill.matrixWorld.copy(marker.matrix);
    outline.matrixWorld.copy(marker.matrix);
    marker.matrixWorldNeedsUpdate = true;
  }
  function mark(p: ItemState | null): void {
    sel = p && showing(p.mesh) ? p : null;
    marker.visible = !!sel && !hush;
    if (sel) follow(true);
  }

  // ---------------------------------------------------------------- the card and the line at the bottom
  const card = el('div', { wt: 'box-card', attrs: { role: 'status' }, style: { display: 'none' } });
  const toast = el('div', { wt: 'box-toast', attrs: { role: 'status' }, style: { display: 'none' } });
  root.append(card, toast);
  ctx.disposer.add(() => { card.remove(); toast.remove(); });
  /** What the card shows: a selected box, a delete just made (with its undo step), or where a restored box is. */
  let shown: 'piece' | 'deleted' | 'back' | null = null, shownEntry: UndoEntry | null = null;
  // Delete is armed only while the last pointerdown was on the canvas or the card (the listener below)
  let armed = false;
  /** The card's Delete button says "(Del)" only while the key would act; the button itself always works. */
  function showArmed(): void {
    const b = card.querySelector<HTMLElement>('[data-wt=box-delete]');
    if (b) b.textContent = armed ? DELETE_ARMED : DELETE_DISARMED;
  }
  const closeBtn = () => el('button', { wt: 'box-close', attrs: { type: 'button', 'aria-label': 'Close' }, text: '×' });
  const floorName = (p: ItemState) => p.fl.name || p.d.floor;
  function showCard(what: typeof shown, lines: (Node | null)[]): void {
    shown = what;
    clear(card);
    for (const line of lines) if (line) card.append(line);
    card.style.display = 'block';
    hover.hide();                                                    // no label under a card
  }
  function hideCard(): void {
    shown = null; shownEntry = null;
    card.style.display = 'none';
  }
  function pieceCard(p: ItemState): void {
    const d = p.d, h = p.kind.height / 1000, z0 = p.z0mm / 1000;
    const on = st.items.filter(q => q.d.on === d.id && !q.removed && q !== p);
    const kinds = [...new Set(on.map(q => q.kind.label))];
    showCard('piece', [
      el('div', { wt: 'box-kind', text: p.kind.label }),
      el('div', { wt: 'box-family', text: d.family }),
      el('div', { wt: 'box-size', text: `${d.w.toFixed(2)} × ${d.d.toFixed(2)} × ${h.toFixed(2)} m · ${floorName(p)}${z0 > 0 ? ', from ' + z0.toFixed(2) + ' m' : ''}` }),
      d.note ? el('div', { wt: 'box-note', text: d.note }) : null,
      el('div', { wt: 'box-id', text: d.id }),
      on.length ? el('div', {
        wt: 'box-cascade',
        text: `${on.length === 1 ? '1 piece stands' : `${on.length} pieces stand`} on it (${kinds.join(', ')}): ${on.length === 1 ? 'it is' : 'they are'} deleted with it.`,
      }) : null,
      el('div', { wt: 'box-buttons' }, [el('button', { wt: 'box-delete', attrs: { type: 'button' }, text: armed ? DELETE_ARMED : DELETE_DISARMED })]),
      closeBtn(),
    ]);
  }
  function deletedCard(text: string, entry: UndoEntry | null): void {
    showCard('deleted', [
      el('div', { wt: 'box-kind', text }),
      el('div', { wt: 'box-buttons' }, [el('button', { wt: 'box-undo', attrs: { type: 'button' }, text: 'Undo' })]),
      closeBtn(),
    ]);
    shownEntry = entry;
    showUndo();
  }
  /** The card's Undo is there only while its step is the top of the undo stack. */
  function showUndo(): void {
    const b = card.querySelector<HTMLElement>('[data-wt=box-undo]');
    if (b) b.style.display = shownEntry && st.undoTop() === shownEntry ? '' : 'none';
  }
  /** `under`: the shown floor above that hides the box (pick.ts coverOf), or null. */
  function backCard(p: ItemState, under: FloorRecord | null): void {
    const floor = floorName(p);
    const where = !showing(p.fl.group) ? ` (not shown: press ${floor})` : under ? ` (under ${under.name || under.key}: press ${floor} to see it)` : '';
    showCard('back', [
      el('div', { wt: 'box-kind', text: p.kind.label }),
      el('div', { wt: 'box-back', text: `Back on ${floor}${where}` }),
      p.kind.visible ? null : el('div', { wt: 'box-back-kind', text: `(${p.kind.label} is hidden: tick it to see it)` }),
      closeBtn(),
    ]);
  }
  let toastTimer = 0;
  function hideToast(): void {
    if (toastTimer) { ctx.disposer.clearTimeout(toastTimer); toastTimer = 0; }
    toast.style.display = 'none';
  }
  function showToast(text: string): void {
    hideToast();
    toast.textContent = text;
    toast.style.display = 'block';
    toastTimer = ctx.disposer.timeout(() => { toastTimer = 0; toast.style.display = 'none'; }, TOAST_MS);
  }

  // ---------------------------------------------------------------- selecting
  function select(p: ItemState): void {
    mark(p);
    if (sel) pieceCard(sel); else hideCard();
  }
  /** Nothing selected, no card. */
  function clearAll(): void {
    mark(null);
    hideCard();
  }
  /** The selection goes; a card about something else (a delete, a restored box) stays. */
  function dropSelection(): void {
    mark(null);
    if (shown === 'piece') hideCard();
  }

  // a click: the pointer's own track, because OrbitControls captures the pointer and the modes track no drag in Orbit
  let press: { x: number; y: number; touch: boolean; moved: boolean } | null = null;
  const far = (e: PointerEvent) => !!press && Math.hypot(e.clientX - press.x, e.clientY - press.y) >= CLICK_SLOP;
  ctx.disposer.listen(canvas, 'pointerdown', e => { press = { x: e.clientX, y: e.clientY, touch: e.pointerType === 'touch', moved: false }; });
  ctx.disposer.listen(canvas, 'pointermove', e => { if (press && e.buttons && far(e)) press.moved = true; });
  ctx.disposer.listen(canvas, 'pointerup', e => { if (press && far(e)) press.moved = true; });
  ctx.disposer.listen(canvas, 'click', e => {
    const was = press;
    press = null;
    if (e.detail >= 2) { clearAll(); return; }                       // the double-click to walk follows
    if (e.button !== 0 || was?.touch || was?.moved || (e as PointerEvent).pointerType === 'touch' || !orbiting()) return;
    const p = pick.atClient(e.clientX, e.clientY);
    if (p) select(p); else clearAll();
  });

  // ---------------------------------------------------------------- Walk and Ghost: the box at the crosshair
  let aimTimer = 0, aimed = false;
  // After a delete here the aim re-picked at once, so a second Delete 0.1 s later took the box behind the deleted one too
  // (and the line named only that one). Now nothing new is aimed at until the view moves or AIM_HOLD_MS has passed.
  let hold: { eye: Vector3; dir: Vector3 } | null = null, holdTimer = 0;
  const eyeNow = new Vector3(), dirNow = new Vector3();
  function endHold(): void {
    if (holdTimer) { ctx.disposer.clearTimeout(holdTimer); holdTimer = 0; }
    hold = null;
  }
  function startHold(): void {
    endHold();
    hold = { eye: ctx.camera.getWorldPosition(new Vector3()), dir: ctx.camera.getWorldDirection(new Vector3()) };
    holdTimer = ctx.disposer.timeout(() => { holdTimer = 0; hold = null; }, AIM_HOLD_MS);
  }
  /** Still holding: no time-out yet and the view has not moved (a move ends the hold). */
  function held(): boolean {
    if (hold && (ctx.camera.getWorldPosition(eyeNow).distanceTo(hold.eye) >= HOLD_MOVE
      || ctx.camera.getWorldDirection(dirNow).angleTo(hold.dir) >= HOLD_TURN)) endHold();
    return hold !== null;
  }
  function aim(): void {
    aimed = true;
    mark(held() ? null : pick.atCentre(AIM_REACH));
  }
  function aimLoop(): void {
    aimTimer = 0;
    if (!aiming()) { if (aimed) { aimed = false; mark(null); } return; }
    aim();
    aimTimer = ctx.disposer.timeout(aimLoop, AIM_MS);
  }

  // ---------------------------------------------------------------- deleting, undoing, the keys
  function remove(p: ItemState | null): void {
    if (p) act.removePiece(p.d.id);                                  // what is shown next: onEdit below
  }
  // Delete is armed only while the last pointerdown was on the canvas or the card: a press in the side panel (a height box
  // just typed in, whose Enter blurs to the body) or anywhere else on the page disarms it. The card's button follows.
  ctx.disposer.listen(window, 'pointerdown', e => {
    const t = (typeof e.composedPath === 'function' ? e.composedPath()[0] : null) ?? e.target;
    armed = t === canvas || (t instanceof Node && card.contains(t));
    showArmed();
  }, true);
  ctx.disposer.listen(window, 'keydown', e => {
    if (typing(e) || !ours(e, root)) return;
    const mod = e.ctrlKey || e.metaKey;
    if (e.code === 'Delete' && !mod && !e.altKey) {
      if (!armed || e.repeat) return;
      if (orbiting()) { if (sel) { e.preventDefault(); remove(sel); } }
      else if (aiming()) { aim(); if (sel) { e.preventDefault(); remove(sel); startHold(); } }
    } else if (e.code === 'KeyZ' && mod && !e.shiftKey && !e.altKey) {
      if (!modes().state.locked && act.undo()) e.preventDefault();
    } else if (e.code === 'Escape' && !mod) {
      if (modes().mode === 'orbit' && (sel || shown)) clearAll();
    }
  });
  ctx.disposer.listen(card, 'click', e => {
    const wt = e.target instanceof Element ? e.target.closest('button')?.getAttribute('data-wt') : null;
    if (wt === 'box-delete') remove(sel);
    else if (wt === 'box-undo') { if (shownEntry && st.undoTop() === shownEntry) act.undo(); }
    else if (wt === 'box-close') clearAll();
  });

  // ---------------------------------------------------------------- what a delete, a restore or an undo shows
  st.onEdit((e: EditEvent) => {
    hideToast();
    if (e.source === 'api') { showUndo(); return; }                  // the stack is gone: a card's Undo with it
    if (e.source === 'restored') endHold();                          // Ctrl+Z in Walk: the box is back, aimed at again at once
    const first = st.itemOf.get(e.ids[0] ?? '');
    if (!first) return;
    const more = e.ids.length - 1;
    if (e.source === 'removed') {
      const text = e.all ? `Deleted: ${e.ids.length} boxes` : `Deleted: ${first.kind.label}${more ? ` (+${more} on it)` : ''}`;
      if (orbiting()) { mark(null); deletedCard(text, e.entry); }
      else showToast(e.entry ? `${text} · Ctrl+Z to undo` : text);
    } else if (e.all) clearAll();                                    // Restore all: the legend line says it
    else if (orbiting()) {
      // under a shown floor above it (Both floors): not shown, or the marker would draw through that floor's plate
      const under = showing(first.fl.group) ? pick.coverOf(first) : null;
      if (showing(first.mesh) && !under) select(first); else { mark(null); backCard(first, under); }
    }
    else showToast(`Back: ${first.kind.label} on ${floorName(first)}`);
  });

  // ---------------------------------------------------------------- when the selection clears
  ctx.disposer.add(ctx.bus.on('mode', () => {
    if (!orbiting() && (shown || (sel && !aimed))) clearAll();       // Walk, Ghost, the Camera panel: no selection, no card
    if (aiming()) { if (!aimTimer) aimTimer = ctx.disposer.timeout(aimLoop, 0); }
    else { endHold(); if (aimed) { aimed = false; mark(null); } }
  }));
  const stillShowing = () => { if (sel && !showing(sel.mesh)) dropSelection(); };
  ctx.disposer.add(ctx.bus.on('floorMode', stillShowing));
  ctx.disposer.add(ctx.bus.on('toggles', stillShowing));
  ctx.disposer.add(ctx.bus.on('furniture', ({ source }) => {
    if (source === 'tick') { stillShowing(); return; }
    if (!sel) return;
    follow(true);                                                    // a typed height resized the box
    if (shown === 'piece') pieceCard(sel);
  }));
  ctx.disposer.add(ctx.bus.on('settings', () => { if (sel) follow(true); }));
  ctx.disposer.add(ctx.bus.on('pieces', () => { if (sel && sel.removed) dropSelection(); }));
  ctx.disposer.add(ctx.bus.on('replayPhase', ({ phase }) => { if (phase === 'settings' || phase === 'play') { clearAll(); hideToast(); } }));

  st.select = { cardOpen: () => shown !== null, selectable: orbiting };
  return { selected: () => sel?.d.id ?? null, marker };
}

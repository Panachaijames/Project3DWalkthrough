// Floor mode and ticks (DESIGN.md 11.5): the pages' floorMode / applyFloor / applyChecks. Owner: builder A.
// VisibilityApi owns group.visible outside Walk (setFloorMode, applyFloor) and the ticks' objects. Modes set group.visible
// for the walked stack in Walk and call applyFloor() when they leave it (the prototypes' restoreVisibility); the replay
// shows every floor while it plays and calls applyFloor() and applyToggles() when it ends (the prototypes' restore).
// Room names (labels.place) and the plan pictures (pictures.sync) read the ticks every frame.
// Ceilings (v2; rooms/DESIGN.md R-9.7; rooms step R4): each floor's `<key> ceilings` mesh (userData.ceiling) shows when the
// Ceilings tick is on AND the mode is Walk or Ghost; never in Orbit (the building stays open from above). They follow
// the mode through bus 'mode'.
import type { Object3D } from 'three';
import type { CreateVisibility, ToggleName, VisibilityApi, ViewMode } from '../contracts';

export const createVisibility: CreateVisibility = ctx => {
  let floorMode: 'all' | string = 'all';
  const toggles: Record<ToggleName, boolean> = { ...ctx.presentation.toggles };
  const picture = ctx.options.address.picture;
  if (picture !== undefined) toggles.picture = picture;          // ?picture=1 / ?picture=0 (the hotel page's address option)

  const applyFloor = (): void => {
    for (const f of ctx.floors) f.group.visible = floorMode === 'all' || floorMode === f.key;
  };
  const ceilings: Object3D[] = ctx.floors.flatMap(f => f.group.children.filter(o => o.userData.ceiling === true));
  let mode: ViewMode = 'orbit';
  const applyCeilings = (): void => {
    const show = !!toggles.ceilings && mode !== 'orbit';
    for (const obj of ceilings) obj.visible = show;
  };
  const applyToggles = (): void => {
    for (const name of ['plates', 'glass', 'single'] as const) {
      for (const obj of ctx.built.toggleObjects[name]) obj.visible = toggles[name];
    }
    mode = ctx.modes?.mode ?? mode;                              // (the modes are installed after this module)
    applyCeilings();
    ctx.pictures?.sync();
  };
  if (ceilings.length) {
    ctx.disposer.add(ctx.bus.on('mode', state => {
      if (state.mode === mode) return;
      mode = state.mode;
      applyCeilings();
    }));
  }

  const api: VisibilityApi = {
    get floorMode() { return floorMode; },
    setFloorMode(mode) {
      floorMode = mode === 'all' || ctx.floorByKey.has(mode) ? mode : 'all';
      applyFloor();
      ctx.bus.emit('floorMode', { floorMode });
    },
    applyFloor,
    get toggles() { return toggles; },
    setToggle(name, on) {
      if (!(name in toggles)) return;
      toggles[name] = !!on;
      applyToggles();
      ctx.bus.emit('toggles', { toggles: { ...toggles } });
    },
    applyToggles,
    // DESIGN.md 8: Floor plates and Glass always; Room names when the model has rooms; Single-line items when it has
    // single parts; Plan picture when a floor has a picture.
    has(name) {
      switch (name) {
        case 'plates': case 'glass': return true;
        case 'rooms': return ctx.model.rooms.length > 0;
        case 'single': return ctx.built.toggleObjects.single.length > 0;
        case 'picture': return (ctx.pictures?.sheets.length ?? 0) > 0;
        case 'ceilings': return ceilings.length > 0;
        default: return false;
      }
    },
  };
  return api;
};

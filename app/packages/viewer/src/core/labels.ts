// Room labels with the declutter (DESIGN.md 13 "Labels", 18.12): the bank and hotel pages' placeLabels, for every project.
// Owner: builder A. A label per room (drawing text, textContent only) over its room at the floor's level + 1.4 m, shown when
// the Room names tick is on, the mode is Orbit and the build replay is absent or done, on the top visible floor only, within
// |NDC| < 1.1 and in front of the camera. Bigger rooms first: a label that would overlap one already placed moves to the
// nearest free row (0, +1, -1, +2, -2 rows of its height + 2 px; 2 px gap across, 1 px down) or is hidden. Positions are
// root-relative (ctx.size()); the labels are absolute children of the root.
import { Vector3 } from 'three';
import type { CreateLabels, LabelBox, LabelsApi, LayoutLabels, RoomLabel } from '../contracts';
import { el } from '../ui/dom';

export const LABEL_LIFT = 1.4;
const ROWS = [0, 1, -1, 2, -2];

export const LABELS_CSS = `
.wtv [data-wt=room] { position:absolute; left:0; top:0; transform:translate(-50%, -50%); font-size:11.5px; background:#ffffffd9;
  color:#1d2329; padding:1px 6px; border-radius:5px; border:1px solid #d5dade; pointer-events:none; white-space:nowrap; z-index:2;
  display:none; }
`;

/** The declutter rule on screen boxes (x, y = the label's centre), in priority order: dy per label, or null (hidden). */
export const layoutLabels: LayoutLabels = items => {
  const placed: LabelBox[] = [];
  const free = (b: LabelBox) => placed.every(q => b.r + 2 <= q.l || b.l >= q.r + 2 || b.b + 1 <= q.t || b.t >= q.b + 1);
  return items.map(({ x, y, w, h }) => {
    const box = (dy: number): LabelBox => ({ l: x - w / 2, r: x + w / 2, t: y + dy - h / 2, b: y + dy + h / 2 });
    const dy = ROWS.map(k => k * (h + 2)).find(d => free(box(d)));
    if (dy === undefined) return null;
    placed.push(box(dy));
    return dy;
  });
};

export const createLabels: CreateLabels = ctx => {
  ctx.ui.addStyle(LABELS_CSS);
  const labels: RoomLabel[] = ctx.model.rooms.map(r => {
    const node = el('div', { wt: 'room', text: r.label });
    ctx.ui.root.append(node);
    return { el: node, floor: r.floor, area: r.area || 0, p: new Vector3(r.x, 0, -r.y) };
  });
  // bigger rooms first: they keep their spot (a stable sort: equal areas as listed)
  const byArea = [...labels].sort((a, b) => b.area - a.area);
  const v = new Vector3();

  const place = (): void => {
    if (!labels.length) return;
    const replay = ctx.replay;
    const show = ctx.visibility.toggles.rooms && ctx.modes.mode === 'orbit' && (replay === null || replay.phase === 'done');
    // only the top floor that is showing: the ones below are under its floor plate
    const top = show ? ctx.floors.filter(f => f.group.visible).sort((a, b) => b.level - a.level)[0] : undefined;
    const { width, height } = show ? ctx.size() : { width: 0, height: 0 };
    const candidates: { L: RoomLabel; x: number; y: number }[] = [];
    for (const L of byArea) {
      let on = !!top && L.floor === top.key;
      if (on) {
        v.copy(L.p);
        v.y = (ctx.floorByKey.get(L.floor)?.level ?? 0) + LABEL_LIFT;
        v.project(ctx.camera);
        on = v.z < 1 && Math.abs(v.x) < 1.1 && Math.abs(v.y) < 1.1;
      }
      if (on) {
        if (!L.w) { L.el.style.display = 'block'; L.w = L.el.offsetWidth; L.h = L.el.offsetHeight; }
        candidates.push({ L, x: (v.x + 1) / 2 * width, y: (1 - v.y) / 2 * height });
      } else if (L.el.style.display !== 'none') L.el.style.display = 'none';
    }
    const dys = layoutLabels(candidates.map(c => ({ x: c.x, y: c.y, w: c.L.w ?? 0, h: c.L.h ?? 0 })));
    candidates.forEach((c, i) => {
      const dy = dys[i];
      if (dy === null || dy === undefined) { c.L.el.style.display = 'none'; return; }
      c.L.dy = dy;
      c.L.el.style.left = `${c.x}px`;
      c.L.el.style.top = `${c.y + dy}px`;
      c.L.el.style.display = 'block';
    });
  };

  ctx.disposer.add(() => { for (const L of labels) L.el.remove(); });
  const api: LabelsApi = { labels, place };
  return api;
};

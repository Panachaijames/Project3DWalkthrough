// parsePresentation / resolvePresentation (DESIGN.md 8) and the replay's default texts (7.2). Owner: builder A.
//
// parsePresentation checks a Presentation v1 (the version sidecar's `presentation`: the API serves it as a plain JSON object,
// so the viewer owns its type and checks it here) and fills the defaults that need no model: accent #2f6f8f, creaseAngle 25,
// groundPlane null. resolvePresentation applies the rest with the model: floor button labels = the floors' names, the tick
// labels, camera far 600, every part kind's style (DEFAULT_PART_STYLES with presentation.partStyles over it) and the ticks'
// starting states (all on, the plan picture off). Both are idempotent: a resolved presentation passes through unchanged.
// Unknown fields are ignored (a newer writer may add some); a known field of the wrong type is a ModelError.
import type {
  CameraStart, ModelIssue, ParsePresentation, PartKind, PartStyle, Presentation, ResolvePresentationFn, ResolvedPresentation,
  StepKey, ToggleName,
} from '../contracts';
import { ModelError, PART_KINDS, ptr } from './parse';
import { DEFAULT_PART_STYLES } from './styles';

/** Defaults for the optional ReplayData texts. introTitle has no constant: source.files.join(' + '), else source.file, else ''. */
export interface ReplayTexts {
  layersTitle: string;
  stepTitles: Record<StepKey, string>;
  /** Line categories plus the replay's own ink, faint, piece, pieceEdge, run, runEdge. */
  colors: Record<string, string>;
}

/** DESIGN.md 7.2: the bank page's values (the bank is the first model built with no drawing-specific rules). */
export const DEFAULT_REPLAY_TEXTS: ReplayTexts = {
  layersTitle: 'How the drawing was read',
  stepTitles: {
    read: 'Read the drawing',
    sort: 'Sort the layers',
    align: 'Line up the levels',
    pair: 'Find the wall faces',
    merge: 'Merge, cut the openings',
    raise: 'Raise the walls',
    finish: 'Floors, stairs, room names',
  },
  colors: {
    wall: '#7a6650',
    glass: '#2f86a8',
    door: '#c0702a',
    stair: '#2e8b47',
    railing: '#9b3fa0',
    ink: '#3b4148',
    faint: '#a4acb4',
    piece: '#cfc2b0',
    pieceEdge: '#8a7a66',
    run: '#e3ddd3',
    runEdge: '#6f675d',
  },
};

/** DESIGN.md 8 "labels" defaults (the tick labels and the Plan picture tick's tooltip). */
export const DEFAULT_TICK_LABELS: Record<ToggleName, string> & { pictureTitle: string } = {
  plates: 'Floor plates',
  glass: 'Glass',
  rooms: 'Room names',
  single: 'Single-line items',
  picture: 'Plan picture',
  ceilings: 'Ceilings',
  pictureTitle: "Each floor's source picture, laid on its floor plate at the model's scale and position",
};
export const DEFAULT_ACCENT = '#2f6f8f';
export const DEFAULT_CREASE_ANGLE = 25;
export const DEFAULT_CAMERA_FAR = 600;
export const DEFAULT_FLOOR_BUTTON_ALL = 'Both floors';
export const DEFAULT_TOGGLES: Record<ToggleName, boolean> = { plates: true, glass: true, rooms: true, single: true, picture: false, ceilings: true };
const TOGGLES: readonly ToggleName[] = ['plates', 'glass', 'rooms', 'single', 'picture', 'ceilings'];

// ------------------------------------------------------------------------------------------------------------- checks
type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => v !== null && typeof v === 'object' && !Array.isArray(v);
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const COLOUR = /^#[0-9a-fA-F]{6}$/;

function vec(v: unknown, n: number, path: string, out: ModelIssue[]): void {
  if (!Array.isArray(v) || v.length !== n || !v.every(isNum)) out.push({ path, message: `must be ${n} numbers` });
}

function checkPresentation(p: unknown): ModelIssue[] {
  const out: ModelIssue[] = [];
  const bad = (path: string, message: string) => { out.push({ path, message }); };
  if (!isObj(p)) { bad('', 'must be object'); return out; }
  for (const key of ['documentTitle', 'heading'] as const) {
    if (!(key in p)) bad('', `must have required property '${key}'`);
    else if (typeof p[key] !== 'string') bad(ptr('', key), 'must be string');
  }
  if (!('intro' in p)) bad('', "must have required property 'intro'");
  else if (!Array.isArray(p.intro)) bad('/intro', 'must be array');
  else p.intro.forEach((run, i) => {
    if (!isObj(run) || typeof run.text !== 'string') bad(`/intro/${i}`, 'must be { text, bold? }');
    else if ('bold' in run && typeof run.bold !== 'boolean') bad(`/intro/${i}/bold`, 'must be boolean');
  });
  if ('accent' in p && (typeof p.accent !== 'string' || !COLOUR.test(p.accent))) bad('/accent', 'must be #rrggbb');
  if (!('legend' in p)) bad('', "must have required property 'legend'");
  else if (!isObj(p.legend)) bad('/legend', 'must be object');
  else {
    const lg = p.legend;
    if (lg.layout !== 'inline' && lg.layout !== 'lines') bad('/legend/layout', "must be 'inline' or 'lines'");
    if (!Array.isArray(lg.items)) bad('/legend/items', 'must be array');
    else lg.items.forEach((it, i) => {
      if (!isObj(it) || typeof it.colour !== 'string' || typeof it.text !== 'string') bad(`/legend/items/${i}`, 'must be { colour, text }');
      // a swatch's colour goes into style.background: only #rrggbb, never url(...) (which would fetch from the network)
      else if (!COLOUR.test(it.colour)) bad(`/legend/items/${i}/colour`, 'must be #rrggbb');
    });
  }
  if ('floorButtons' in p && p.floorButtons !== undefined) {
    const fb = p.floorButtons;
    if (!isObj(fb)) bad('/floorButtons', 'must be object');
    else {
      if ('all' in fb && typeof fb.all !== 'string') bad('/floorButtons/all', 'must be string');
      if ('labels' in fb) {
        if (!isObj(fb.labels)) bad('/floorButtons/labels', 'must be object');
        else for (const [k, v] of Object.entries(fb.labels)) if (typeof v !== 'string') bad(ptr('/floorButtons/labels', k), 'must be string');
      }
    }
  }
  if ('labels' in p && p.labels !== undefined) {
    if (!isObj(p.labels)) bad('/labels', 'must be object');
    else for (const [k, v] of Object.entries(p.labels)) if (typeof v !== 'string') bad(ptr('/labels', k), 'must be string');
  }
  if (!('camera' in p)) bad('', "must have required property 'camera'");
  else if (!isObj(p.camera)) bad('/camera', 'must be object');
  else {
    const c = p.camera;
    if (c.kind === 'fixed') { vec(c.position, 3, '/camera/position', out); vec(c.target, 3, '/camera/target', out); }
    else if (c.kind === 'fitSlabs') {
      vec(c.away, 3, '/camera/away', out);
      if (!isNum(c.targetY)) bad('/camera/targetY', 'must be number');
      if (typeof c.panForPanel !== 'boolean') bad('/camera/panForPanel', 'must be boolean');
    } else bad('/camera/kind', "must be 'fixed' or 'fitSlabs'");
    if ('far' in c && c.far !== undefined && !(isNum(c.far) && c.far > 0)) bad('/camera/far', 'must be a number > 0');
  }
  if ('partStyles' in p && p.partStyles !== undefined) {
    if (!isObj(p.partStyles)) bad('/partStyles', 'must be object');
    else for (const [kind, st] of Object.entries(p.partStyles)) {
      const at = ptr('/partStyles', kind);
      if (!(PART_KINDS as readonly string[]).includes(kind)) { bad(at, `no part kind '${kind}'`); continue; }
      if (!isObj(st)) { bad(at, 'must be object'); continue; }
      for (const key of ['color', 'edge'] as const) if (key in st && (typeof st[key] !== 'string' || !COLOUR.test(st[key] as string))) bad(ptr(at, key), 'must be #rrggbb');
      if ('mesh' in st && (typeof st.mesh !== 'string' || !st.mesh)) bad(ptr(at, 'mesh'), 'must be a name');
      for (const key of ['see', 'renderOrder', 'opacity', 'roughness', 'metalness', 'edgeOpacity'] as const) if (key in st && !isNum(st[key])) bad(ptr(at, key), 'must be number');
      for (const key of ['glass', 'collider', 'single'] as const) if (key in st && typeof st[key] !== 'boolean') bad(ptr(at, key), 'must be boolean');
    }
  }
  if ('creaseAngle' in p && p.creaseAngle !== undefined && !(isNum(p.creaseAngle) && p.creaseAngle >= 0 && p.creaseAngle <= 180)) {
    bad('/creaseAngle', 'must be degrees, 0 - 180');
  }
  if ('groundPlane' in p && p.groundPlane !== undefined && p.groundPlane !== null) {
    const g = p.groundPlane;
    if (!isObj(g)) bad('/groundPlane', 'must be object or null');
    else {
      if (!Array.isArray(g.size) || g.size.length !== 2 || !g.size.every(v => isNum(v) && v > 0)) bad('/groundPlane/size', 'must be [w, d] > 0');
      if (typeof g.colour !== 'string' || !COLOUR.test(g.colour)) bad('/groundPlane/colour', 'must be #rrggbb');
    }
  }
  if ('toggles' in p && p.toggles !== undefined) {
    if (!isObj(p.toggles)) bad('/toggles', 'must be object');
    else for (const [k, v] of Object.entries(p.toggles)) {
      if (!(TOGGLES as readonly string[]).includes(k)) bad(ptr('/toggles', k), `no tick '${k}'`);
      else if (typeof v !== 'boolean') bad(ptr('/toggles', k), 'must be boolean');
    }
  }
  return out;
}

export const parsePresentation: ParsePresentation = json => {
  const issues = checkPresentation(json);
  if (issues.length) {
    throw new ModelError(issues, `[viewer] presentation: ${issues.length} issue(s): ` + issues.slice(0, 3).map(i => `${i.path}: ${i.message}`).join('; '));
  }
  const p = json as Presentation;
  return {
    ...p,
    accent: p.accent ?? DEFAULT_ACCENT,
    creaseAngle: p.creaseAngle ?? DEFAULT_CREASE_ANGLE,
    groundPlane: p.groundPlane ?? null,
  };
};

export const resolvePresentation: ResolvePresentationFn = (p, model) => {
  const partStyles = {} as Record<PartKind, PartStyle>;
  for (const kind of PART_KINDS) partStyles[kind] = { ...DEFAULT_PART_STYLES[kind], ...(p.partStyles?.[kind] ?? {}) };
  const labels: Partial<Record<string, string>> = {};
  for (const f of model.floors) labels[f.key] = f.name;
  Object.assign(labels, p.floorButtons?.labels ?? {});
  const camera = { ...p.camera, far: p.camera.far ?? DEFAULT_CAMERA_FAR } as CameraStart & { far: number };
  const resolved: ResolvedPresentation = {
    documentTitle: p.documentTitle,
    heading: p.heading,
    intro: p.intro.map(run => ({ ...run })),
    accent: p.accent ?? DEFAULT_ACCENT,
    legend: { layout: p.legend.layout, items: p.legend.items.map(it => ({ ...it })) },
    floorButtons: { all: p.floorButtons?.all ?? DEFAULT_FLOOR_BUTTON_ALL, labels },
    labels: { ...DEFAULT_TICK_LABELS, ...(p.labels ?? {}) },
    camera,
    partStyles,
    creaseAngle: p.creaseAngle ?? DEFAULT_CREASE_ANGLE,
    groundPlane: p.groundPlane ? { size: [p.groundPlane.size[0], p.groundPlane.size[1]], colour: p.groundPlane.colour } : null,
    toggles: { ...DEFAULT_TOGGLES, ...(p.toggles ?? {}) },
  };
  return resolved;
};

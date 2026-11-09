// The mock API's reading of a DXF upload (docs/upload/ACCEPTANCE A-7's second test): a small synthetic drawing whose layer,
// block and text names are the hostile ones of tools/upload/make-test-dxf.py (HOSTILE), so the web app's steps show
// drawing text that would run as HTML if it were ever parsed as HTML. Written by hand to the contracts' shapes
// (DrawingRead, PlanGeometry, ConversionReport); not a reading of the uploaded bytes (the mock reads nothing).
import type * as C from '../../src/upload/contracts';

export const HOSTILE = {
  wall: 'A-WALL<img src=x onerror=alert(1)>',
  door: 'A-DOOR</script><script>alert(2)</script>',
  furn: "I-FURN $' $& &amp",
  glaz: "A-GLAZ $' &amp; $&",
  desk: 'Desk<img src=x onerror=alert(3)> 1600x800',
  chair: "Chair</script>$'-1234567-Level 1",
  room1: '<img src=x onerror=alert(4)>LOBBY',
  room2: "OFFICE</script>$'&amp;",
} as const;

const LAYERS = [HOSTILE.wall, 'A-WALL-PATT', HOSTILE.glaz, HOSTILE.door, 'A-FLOR-HRAL', HOSTILE.furn, 'A-AREA-IDEN', '0'];

interface Entry { key: string; layer: number; type: number; pts: [number, number][] }

/** The plan's entries (cm from the origin [0, 0]). */
function entries(): Entry[] {
  const L = (name: string) => LAYERS.indexOf(name);
  const out: Entry[] = [];
  // the room: 10 x 8 m, walls on the hostile wall layer
  out.push({ key: '1A', layer: L(HOSTILE.wall), type: 1, pts: [[0, 0], [1000, 0], [1000, 800], [0, 800]] });
  out.push({ key: '1B', layer: L(HOSTILE.wall), type: 1, pts: [[20, 20], [980, 20], [980, 780], [20, 780]] });
  out.push({ key: '1C', layer: L('A-WALL-PATT'), type: 2, pts: [[0, 0], [1000, 0], [1000, 20], [0, 20]] });
  out.push({ key: '1D', layer: L(HOSTILE.glaz), type: 0, pts: [[300, 800], [700, 800]] });
  out.push({ key: '1E', layer: L(HOSTILE.door), type: 0, pts: [[0, 300], [90, 300]] });
  out.push({ key: '1F', layer: L(HOSTILE.door), type: 0, pts: [[90, 300], [64, 364], [0, 390]] });
  out.push({ key: '20', layer: L('A-FLOR-HRAL'), type: 0, pts: [[600, 100], [900, 100]] });
  // a desk block with its lines, and a chair inside it (nested key)
  out.push({ key: '30', layer: L(HOSTILE.furn), type: 5, pts: [[400, 400]] });
  out.push({ key: '30/31', layer: L(HOSTILE.furn), type: 1, pts: [[320, 360], [480, 360], [480, 440], [320, 440]] });
  out.push({ key: '30/32', layer: L(HOSTILE.furn), type: 5, pts: [[400, 470]] });
  out.push({ key: '30/32/33', layer: L(HOSTILE.furn), type: 1, pts: [[380, 450], [420, 450], [420, 490], [380, 490]] });
  out.push({ key: '40', layer: L('A-AREA-IDEN'), type: 4, pts: [[200, 600]] });
  out.push({ key: '41', layer: L('A-AREA-IDEN'), type: 4, pts: [[700, 300]] });
  return out;
}

/** 12 hex of a string (a stand-in signature: the mock never re-matches). */
function hex12(s: string): string {
  let h1 = 0x811c9dc5, h2 = 0x01000193;
  for (let i = 0; i < s.length; i++) {
    h1 = Math.imul(h1 ^ s.charCodeAt(i), 16777619) >>> 0;
    h2 = Math.imul(h2 + s.charCodeAt(i), 2246822519) >>> 0;
  }
  return (h1.toString(16).padStart(8, '0') + h2.toString(16).padStart(8, '0')).slice(0, 12);
}

export function syntheticPlan(source: C.Sha1): C.PlanGeometry {
  const es = entries();
  const pts: number[] = [];
  const items: C.PlanGeometry['items'] = { key: [], layer: [], type: [], first: [], count: [], sig: [], rsig: [], eid: [] };
  for (const e of es) {
    items.key.push(e.key);
    items.layer.push(e.layer);
    items.type.push(e.type);
    items.first.push(pts.length / 2);
    items.count.push(e.pts.length);
    items.sig.push(hex12(`${e.key}:${e.layer}`));
    const inChair = e.key.startsWith('30/32');
    items.rsig.push(inChair ? hex12(`r${e.key}`) : '');
    items.eid.push(inChair ? 0 : -1);
    for (const [x, y] of e.pts) pts.push(x, y);
  }
  return { format: 'plan-geometry/1', source, units: 'mm', origin: [0, 0], quantum: 0.01, layers: LAYERS.slice(), items, elementIds: ['1234567'], pts };
}

function layerRead(name: string, es: Entry[]): C.LayerRead {
  const mine = es.filter(e => LAYERS[e.layer] === name);
  const byType: Record<string, number> = {};
  for (const e of mine) {
    const t = ['LWPOLYLINE', 'LWPOLYLINE', 'HATCH', 'HATCH', 'TEXT', 'INSERT'][e.type]!;
    byType[t] = (byType[t] ?? 0) + 1;
  }
  return {
    name,
    normalised: name.toUpperCase().replace(/\s+/g, ' ').trim(),
    state: { on: true, frozen: false, locked: false, plot: true },
    linetype: 'Continuous',
    colour: 7,
    items: mine.length,
    byType,
    inBlocks: mine.filter(e => e.key.includes('/')).length,
    closedShapes: mine.filter(e => e.type === 1).length,
    solidHatches: mine.filter(e => e.type === 2).length,
    hatchPatterns: {},
    length: mine.length * 4,
    doorArcs: name === HOSTILE.door ? 1 : 0,
    doorArcsWithLeaf: name === HOSTILE.door ? 1 : 0,
    texts: mine.filter(e => e.type === 4).length,
    inserts: mine.filter(e => e.type === 5).length,
    topBlocks: name === HOSTILE.furn ? [{ family: HOSTILE.desk, count: 1 }, { family: HOSTILE.chair, count: 1 }] : [],
    linetypes: {},
    pairs: { glassLike: name === HOSTILE.glaz ? 1 : 0, wallLike: name === HOSTILE.wall ? 2 : 0 },
    extents: mine.length ? [0, 0, 10, 8] : null,
  };
}

export function syntheticDrawing(source: { sha1: C.Sha1; name: string }): C.DrawingRead {
  const es = entries();
  return {
    format: 'drawing-read/1',
    source: { sha1: source.sha1, name: source.name },
    reader: { version: 'mock', seconds: 0.1, peakMemoryMB: null },
    dxf: { acadVersion: 'AC1032', insUnits: 4, auditErrors: 0, auditFixes: 0 },
    units: { declared: 'mm', votes: { mm: 1, cm: 0, m: 0, in: 0, ft: 0 }, dimensionMedian: null, used: 'mm', verdict: 'declared-only', note: '' },
    extents: [0, 0, 10, 8],
    counts: { items: es.length, byType: { LWPOLYLINE: 8, HATCH: 1, TEXT: 2, INSERT: 2 }, dimensions: 0 },
    layers: LAYERS.map(n => layerRead(n, es)),
    blocks: [
      { name: HOSTILE.desk, family: HOSTILE.desk, inserts: 1, byLayer: { [HOSTILE.furn]: 2 }, mirrored: 0, maxDepth: 2, attribTags: [] },
      { name: HOSTILE.chair, family: 'Chair</script>$\'', inserts: 1, byLayer: { [HOSTILE.furn]: 1 }, mirrored: 0, maxDepth: 1, attribTags: [] },
    ],
    texts: [
      { layer: 'A-AREA-IDEN', x: 2, y: 6, height: 0.25, text: HOSTILE.room1, kind: 'TEXT', tag: null, block: null },
      { layer: 'A-AREA-IDEN', x: 7, y: 3, height: 0.25, text: HOSTILE.room2, kind: 'MTEXT', tag: null, block: null },
    ],
    levelTags: [{ x: 12, y: 1, value: 0, text: '+0.00', layer: '0', source: 'text', label: HOSTILE.room1 }],
    gridLabels: [],
    areas: [{ id: 'a1', bbox: [-1, -1, 11, 9], items: es.length, wallItems: 3, looks: 'plan' }],
  };
}

export function syntheticConversion(source: { sha1: C.Sha1; name: string; bytes: number }): C.ConversionReport {
  return {
    format: 'conversion-report/1',
    source: { sha1: source.sha1, name: source.name, bytes: source.bytes, kind: 'dxf', formatVersion: 'AC1032' },
    converter: null,
    dxf: { sha1: source.sha1, bytes: source.bytes, acadVersion: 'AC1032', insUnits: 4, auditErrors: 0, auditFixes: 0 },
    seconds: 0,
    peakMemoryMB: null,
    exitCode: null,
    messages: [],
    totals: { dwgEntities: null, dxfEntities: 13, missing: 0, extra: 0, layerChanged: 0, emptyLayer: 0 },
    byLayer: [],
    lostBlocks: [],
    renamedBlocks: [],
    unknownObjects: 0,
    verdict: 'not-converted',
    notes: ['Exported by the drawing\'s own program: no conversion to check'],
  };
}

/** Suggestions for the synthetic layers (by name, as U-8.3's table would). */
export function syntheticSuggestions(): Record<string, C.LayerSuggestion> {
  const role = (n: string): C.LayerRole =>
    n === HOSTILE.wall || n === 'A-WALL-PATT' ? 'wall'
      : n === HOSTILE.glaz ? 'window'
      : n === HOSTILE.door ? 'door'
      : n === 'A-FLOR-HRAL' ? 'railing'
      : n === HOSTILE.furn ? 'furniture'
      : n === 'A-AREA-IDEN' ? 'room-name' : 'other';
  const out: Record<string, C.LayerSuggestion> = {};
  for (const n of LAYERS) {
    const r = role(n);
    out[n] = { role: r, from: r === 'other' ? 'default' : 'name', evidence: [`named like a ${r} layer: ${n}`] };
  }
  return out;
}

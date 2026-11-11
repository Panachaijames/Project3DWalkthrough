// The Build page's pure parts (docs/upload/DESIGN.md U-8.1, U-9, U-12, U-13.3, U-14.3): role labels and help, the settings
// changes, the floor checks, the pre-build checklist, the step rules, the layer rows, the close-to-walls set, the item
// refs (every field from the plan entry), the block climb and Find, the diff rows, the slug and the default label.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { describe, expect, it } from 'vitest';
import { blockOf, findItems, keyIndex } from '@/build/CheckStep';
import { diffRows, sameAs } from '@/build/DiffPanel';
import { closeToWalls, layerRows } from '@/build/LayersStep';
import { CLOSE_TO_WALLS, roleHelp, roleLabel, ROLES } from '@/build/roles';
import { defaultLabel } from '@/build/SaveStep';
import {
  addFloor, addSetAside, boxArea, confirmUnits, defaultWallHeight, floorIssues, itemRef, moveFloor, namingIssues, parseNumber,
  removeFloor, restoreSetAside, roleOf, RULES_EARLIER_TEXT, setFurnitureWord, setOpeningFix, setOutlineEdge, setRoles, setRules,
  setUnits, updateFloor,
} from '@/build/settingsEdit';
import { checklist, errorAdvice, LOSS_WARNING, reachable, rereadText, RULES_ITEM } from '@/build/steps';
import { projectIdProblem, slugify } from '@/lib/slug';
import { decodePlan, type DecodedPlan } from '@/plan';
import type { BuildDetail, BuildSettings, DiffBody, DrawingRead, PlanGeometry } from '@/upload/contracts';
import { FIXTURES_DIR } from '../mock-api/fixtures';

const U = (...p: string[]) => path.join(FIXTURES_DIR, 'upload', ...p);
const BANK = JSON.parse(readFileSync(U('settings', 'bank.json'), 'utf8')) as BuildSettings;
const HOUSE = JSON.parse(readFileSync(U('settings', 'house.json'), 'utf8')) as BuildSettings;
const plan1 = () => JSON.parse(gunzipSync(readFileSync(U('plan', 'bank1.plan.json.gz'))).toString('utf8')) as PlanGeometry;
const drawing1 = JSON.parse(readFileSync(U('drawing', 'bank1.drawing.json'), 'utf8')) as DrawingRead;

describe('roles (U-8.1)', () => {
  it('17 roles, each with its label and one line of help, in the table\'s order', () => {
    expect(ROLES.map(r => r.role)).toEqual(['wall', 'column', 'glass', 'window', 'door', 'screen', 'stair', 'stair-above', 'railing',
      'furniture', 'room-name', 'room-outline', 'level', 'grid', 'light', 'other', 'ignore']);
    expect(roleLabel('glass')).toBe('Glass walls');
    expect(roleHelp('glass')).toBe('curtain walls and glass partitions, built full height');
    expect(roleLabel('other')).toBe('Not built (kept as context)');
    expect(roleHelp('ignore')).toBe('dropped everywhere, also from finding doors and windows');
    expect(roleLabel('screen')).toBe('Screens');
    expect(roleHelp('light')).toBe('light fittings: kept for later, not built now');
    expect(CLOSE_TO_WALLS).toBe('close to walls: ignoring it can change which doors and windows are found');
  });
});

describe('settings changes', () => {
  it('roles: one layer or many; an unlisted layer is other', () => {
    const s = setRoles(['A-WALL', 'NEW'], 'ignore')(BANK);
    expect(s.layers['A-WALL']).toBe('ignore');
    expect(s.layers.NEW).toBe('ignore');
    expect(BANK.layers['A-WALL']).toBe('wall');                      // a new object, the old one untouched
    expect(roleOf(BANK, 'NOT-THERE')).toBe('other');
  });

  it('units: a change confirms them; Confirm keeps them', () => {
    const one = { ...BANK, sources: BANK.sources.map(s => ({ ...s, unitsConfirmed: false })) };
    const sha = BANK.sources[0]!.sha1;
    expect(setUnits(sha, 'in')(one).sources[0]).toMatchObject({ units: 'in', unitsConfirmed: true });
    expect(setUnits(sha, 'in')(one).sources[1]).toMatchObject({ units: 'mm', unitsConfirmed: false });
    expect(confirmUnits(sha)(one).sources[0]).toMatchObject({ units: 'mm', unitsConfirmed: true });
  });

  it('floors: add (next key, 3 m above), remove, move, update', () => {
    const s = addFloor()(BANK);
    expect(s.floors.map(f => f.key)).toEqual(['L1', 'L2', 'L3']);
    expect(s.floors[2]).toMatchObject({ name: 'Level 3', level: 7.4, wallHeight: 3.7, area: { kind: 'wholeFile' }, align: { method: 'auto' } });
    expect(moveFloor(2, -1)(s).floors.map(f => f.key)).toEqual(['L1', 'L3', 'L2']);
    expect(moveFloor(0, -1)(s)).toBe(s);
    expect(removeFloor(1)(s).floors.map(f => f.key)).toEqual(['L1', 'L3']);
    expect(updateFloor(0, { level: 0.9 })(s).floors[0]!.level).toBe(0.9);
  });

  it('a box area: ordered corners, pad 0.5 and match all by default', () => {
    expect(boxArea([10, 5, 0, -5])).toEqual({ kind: 'box', bbox: [0, -5, 10, 5], pad: 0.5, match: 'all' });
    expect(boxArea([0, 0, 1, 1], 0, 'any')).toEqual({ kind: 'box', bbox: [0, 0, 1, 1], pad: 0, match: 'any' });
  });

  it('wall height default: next level - this level; none for the top floor', () => {
    expect(defaultWallHeight(HOUSE.floors, 0)).toBe(3.9);
    expect(defaultWallHeight(HOUSE.floors, 1)).toBeNull();
  });

  it('floor checks: keys, levels rising, a wall height, a source, a box with size', () => {
    expect(floorIssues(BANK)).toEqual([]);
    const bad: BuildSettings = {
      ...BANK,
      floors: [
        { ...BANK.floors[0]!, key: 'L 1' },
        { ...BANK.floors[1]!, level: -1, wallHeight: 0, source: 'f'.repeat(40), area: { kind: 'box', bbox: [1, 1, 1, 2], pad: 0.5, match: 'all' } },
      ],
    };
    const paths = floorIssues(bad).map(i => i.path);
    expect(paths).toEqual(expect.arrayContaining(['floors/0/key', 'floors/1/level', 'floors/1/wallHeight', 'floors/1/source', 'floors/1/area']));
    const twice = { ...BANK, floors: [BANK.floors[0]!, { ...BANK.floors[1]!, key: 'L1' }] };
    expect(floorIssues(twice).map(i => i.message)).toContain('the key L1 is used twice');
    expect(namingIssues({ ...BANK, project: { ...BANK.project, maxPrefix: 'bb', maxFileName: 'x.txt' } }).map(i => i.path)).toEqual(['project/maxPrefix', 'project/maxFileName']);
  });

  it('typed numbers: a comma as a decimal point, empty and junk are null; 0 stays 0', () => {
    expect(parseNumber('3,7')).toBe(3.7);
    expect(parseNumber(' 0 ')).toBe(0);
    expect(parseNumber('')).toBeNull();
    expect(parseNumber('abc')).toBeNull();
  });
});

describe('fixes (U-12.3, U-10.6)', () => {
  it('an ItemRef takes every field from the plan entry (sig, rsig, element id, layer), never derived', () => {
    const json = plan1();
    const p = decodePlan(json);
    const i = json.items.eid.findIndex(e => e >= 0);
    const key = json.items.key[i]!;
    expect(itemRef(p, 'L1', key)).toEqual({
      floor: 'L1', source: json.source, key, sig: json.items.sig[i], rsig: json.items.rsig[i],
      elementId: json.elementIds[json.items.eid[i]!], layer: json.layers[json.items.layer[i]!],
    });
    const j = json.items.eid.findIndex(e => e < 0);
    expect(itemRef(p, 'L1', json.items.key[j]!)).toMatchObject({ elementId: null, rsig: '' });
    expect(itemRef(p, 'L1', 'nope')).toBeNull();
  });

  it('set aside: refs added once; restore drops a ref by its key or by an item inside its block', () => {
    const ref = { floor: 'L1', source: 'a'.repeat(40), key: 'BA/2C4', sig: '0123456789ab', rsig: '', elementId: null, layer: 'I-FURN' };
    const s1 = addSetAside([ref, ref])(BANK);
    expect(s1.fixes.setAside).toEqual([{ ...ref, note: '' }]);
    expect(addSetAside([ref])(s1)).toBe(s1);
    expect(restoreSetAside('L1', ['BA/2C4/1F3'])(s1).fixes.setAside).toEqual([]);   // an item of the block restores the block
    expect(restoreSetAside('L2', ['BA/2C4'])(s1)).toBe(s1);
  });

  it('opening fixes replace the fix of the same opening (either end order); kind null with no heights drops it', () => {
    const f = { floor: 'L1', a: [0, 0] as [number, number], b: [1, 0] as [number, number], kind: 'window' as const, head: 2.4, sill: null };
    const s1 = setOpeningFix(f)(BANK);
    const s2 = setOpeningFix({ ...f, a: [1, 0], b: [0, 0], kind: 'none', head: null })(s1);
    expect(s2.fixes.openings).toEqual([{ ...f, a: [1, 0], b: [0, 0], kind: 'none', head: null }]);
    expect(setOpeningFix({ ...f, kind: null, head: null, sill: null })(s2).fixes.openings).toEqual([]);
  });

  it('outline edges: accepted or refused, one per edge', () => {
    const e = { floor: 'suite', a: [0, 0] as [number, number], b: [2, 0] as [number, number], as: 'wall' as const };
    const s = setOutlineEdge({ ...e, as: 'glass' })(setOutlineEdge(e)(BANK));
    expect(s.fixes.outlineEdges).toEqual([{ ...e, as: 'glass' }]);
  });

  it('a grey family given a kind leaves any other kind', () => {
    const s = setFurnitureWord('Mystery-Box', 'cabinet')(BANK);
    expect(s.furniture.words.cabinet).toEqual(['Mystery-Box']);
    const t = setFurnitureWord('Fritz-Hansen', 'table')(s);
    expect(t.furniture.words.seat).toBeUndefined();
    expect(t.furniture.words.table).toEqual(['Fritz-Hansen']);
    expect(setFurnitureWord('Mystery-Box', '')(s).furniture.words.cabinet).toBeUndefined();
  });
});

const detailWith = (patch: Partial<BuildDetail>): BuildDetail => ({
  id: '20261104T101500-0a1b2c', projectId: 'p', createdAt: '', updatedAt: '', status: 'open', savedVersion: null, sourceNames: [],
  runStatus: 'done', url: '', sources: [], settings: BANK, settingsRevision: 2, layersReviewedAt: '2026-11-04T00:00:00Z',
  suggestions: {}, run: null, result: null, urls: { settings: '', run: '', cancel: '', save: '' }, ...patch,
});

describe('steps and the pre-build checklist (U-14.3)', () => {
  it('Layers, Floors, Build open once the proposal is in; Check and Save once built', () => {
    const d0 = detailWith({ settingsRevision: 0 });
    expect(reachable('files', d0)).toBe(true);
    expect(reachable('layers', d0)).toBe(false);
    const d1 = detailWith({});
    expect(reachable('floors', d1)).toBe(true);
    expect(reachable('check', d1)).toBe(false);
    expect(reachable('save', detailWith({ result: {} as BuildDetail['result'] }))).toBe(true);
  });

  it('clear for the bank fixture', () => {
    // changed on purpose by the rooms milestone (R6): the fixture names none of the three rule keys, so it is built the
    // earlier way and the checklist says so in its one warning line (R-12.6); with the new rules it is clear
    expect(checklist(detailWith({}), BANK)).toEqual([{ id: RULES_ITEM, step: 'floors', text: RULES_EARLIER_TEXT, level: 'warn' }]);
    expect(checklist(detailWith({}), setRules('new')(BANK))).toEqual([]);
  });

  it('units not confirmed, Layers not seen, a floor with no wall height, no source, an empty area: each blocks and names its step', () => {
    const s: BuildSettings = {
      ...BANK,
      sources: [{ ...BANK.sources[0]!, unitsConfirmed: false }, BANK.sources[1]!],
      floors: [{ ...BANK.floors[0]!, wallHeight: 0 }, { ...BANK.floors[1]!, source: 'e'.repeat(40), area: { kind: 'box', bbox: [0, 0, 0, 0], pad: 0.5, match: 'all' } }],
    };
    const items = checklist(detailWith({ layersReviewedAt: null }), s);
    const by = (id: string) => items.find(i => i.id === id);
    expect(by(`units:${BANK.sources[0]!.sha1}`)).toMatchObject({ step: 'files', level: 'block' });
    expect(by('layers')).toMatchObject({ step: 'layers', level: 'block' });
    expect(by('height:0')).toMatchObject({ step: 'floors', text: 'Level 1 has no wall height' });
    expect(by('source:1')).toMatchObject({ step: 'floors', text: 'Level 2 has no source file' });
    expect(by('area:1')).toMatchObject({ step: 'floors', text: 'Level 2\'s area is empty' });
    expect(checklist(detailWith({ layersReviewedAt: null }), BANK, { reviewPending: true }).find(i => i.id === 'layers')).toBeUndefined();
  });

  it('a conversion loss warns, never blocks; a source read again blocks with "Reading <file> again in <units>..."', () => {
    const sha = BANK.sources[0]!.sha1;
    const src = { sha1: sha, name: 'suite.dwg', bytes: 1, kind: 'dwg' as const, conversion: { verdict: 'loss' as const, notes: [], lostInModelSpace: 8254 }, units: null, urls: null };
    const items = checklist(detailWith({ sources: [src] }), setRules('new')(BANK));     // the new rules: no rules line (R6)
    expect(items).toEqual([{ id: `loss:${sha}`, step: 'files', text: `suite.dwg: ${LOSS_WARNING}`, level: 'warn' }]);
    expect(LOSS_WARNING).toBe('parts of the drawing were lost in conversion; export a DXF from AutoCAD for a complete build');
    const s = setUnits(sha, 'in')(BANK);
    const run = { id: '0003-prepare', kind: 'prepare' as const, status: 'running' as const, step: 'read:0', progress: 0.5, steps: [], messages: [], error: null,
      queuedAt: '', startedAt: '', finishedAt: null, cancelRequested: false, only: [sha] };
    expect(rereadText(detailWith({ run }), s)).toBe('Reading I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg again in inches...');
    expect(checklist(detailWith({ run }), s)[0]).toMatchObject({ id: 'reread', level: 'block' });
  });

  it('before the proposal: one line, "Reading the drawings..."', () => {
    expect(checklist(detailWith({ settingsRevision: 0 }), null)).toEqual([{ id: 'reading', step: 'files', text: 'Reading the drawings...', level: 'block' }]);
  });

  it('a failed run says what to change', () => {
    expect(errorAdvice('align_failed')).toMatch(/grid or two points/);
    expect(errorAdvice('area_empty')).toMatch(/Floors step/);
    expect(errorAdvice('whatever')).toMatch(/Build again/);
  });
});

describe('the Layers step\'s rows and chip', () => {
  it('one row per layer name across the drawings, counts summed, plus names only the settings know', () => {
    const rows = layerRows([drawing1, drawing1], ['ONLY-IN-SETTINGS']);
    expect(rows.length).toBe(drawing1.layers.length + 1);
    const wall = rows.find(r => r.name === 'A-WALL')!;
    const one = drawing1.layers.find(l => l.name === 'A-WALL')!;
    expect(wall.read!.items).toBe(one.items * 2);
    expect(wall.sources).toEqual([0, 1]);
    expect(rows.find(r => r.name === 'ONLY-IN-SETTINGS')!.read).toBeNull();
    expect(rows.map(r => r.name)).toEqual([...rows.map(r => r.name)].sort());
  });

  it('close to walls: only ignore layers with items near wall-role lines (nearLayers on each plan)', () => {
    // a plan stand-in whose nearLayers answer is known: the module's own function reads the plan (U7's code)
    const plan = { layers: ['A-WALL', 'A-FLOR', 'A-DETL'], count: 0 } as unknown as DecodedPlan;
    const near = new Map([[1, 3], [2, 0]]);
    const role = (n: string) => (n === 'A-WALL' ? 'wall' : 'ignore') as 'wall' | 'ignore';
    const result = closeToWalls([plan], role, () => near);
    expect([...result]).toEqual(['A-FLOR']);
  });
});

describe('the Check step\'s pick helpers', () => {
  it('block mode climbs to the innermost INSERT anchor by key prefix; Find matches keys and layers', () => {
    const json = plan1();
    const p = decodePlan(json);
    const index = keyIndex(p);
    const child = json.items.key.findIndex((k, i) => k.split('/').length === 3 && json.items.type[i] !== 5);
    expect(child).toBeGreaterThanOrEqual(0);
    const key = json.items.key[child]!;
    const anchor = blockOf(key, index, p);
    expect(key.startsWith(`${anchor}/`)).toBe(true);
    expect(p.typeAt(index.get(anchor)!)).toBe(5);
    expect(blockOf(anchor, index, p)).toBe(anchor);
    const found = findItems(p, 'BA/');
    expect(found.length).toBe(50);
    expect(found.every(f => f.key.startsWith('BA/'))).toBe(true);
    expect(findItems(p, 'a-wall', 5).every(f => f.layer === 'A-WALL' || f.layer.toLowerCase().includes('a-wall'))).toBe(true);
    expect(findItems(p, '  ')).toEqual([]);
  });
});

describe('diff rows (U-12.4)', () => {
  it('the counts that changed, then furniture by kind; nothing changed is "same"', () => {
    const body: DiffBody = {
      counts: { L1: { parts: [100, 99], openings: [24, 24] }, L2: {} }, partsAdded: [], partsRemoved: [], openingsAdded: [],
      openingsRemoved: [], openingsChanged: [], furnitureByKind: { seat: [70, 71] }, roomsAdded: [], roomsRemoved: [],
    };
    expect(diffRows(body)).toEqual([{ floor: 'L1', what: 'parts', before: 100, after: 99 }, { floor: '', what: 'furniture: seat', before: 70, after: 71 }]);
    expect(sameAs(body)).toBe(false);
    expect(sameAs({ ...body, counts: { L1: { parts: [1, 1] } }, furnitureByKind: {} })).toBe(true);
  });
});

describe('names (U-13.3, U-2 5f)', () => {
  it('slugs as the API makes them; a new id is 2 - 40 characters', () => {
    expect(slugify('Bangkok Bank, Sampeng Branch')).toBe('bangkok-bank-sampeng-branch');
    expect(slugify('Café Déjà Vu')).toBe('cafe-deja-vu');
    expect(slugify('บ้านสุขุมวิท')).toBe('');
    const long = slugify('The Very Long Name Of A Hotel Lobby Renovation Project Phase Two');
    expect(long.length).toBeLessThanOrEqual(40);
    expect(long.endsWith('-')).toBe(false);
    expect(projectIdProblem('a'.repeat(41))).toMatch(/at most 40/);
    expect(projectIdProblem('a'.repeat(40))).toBeNull();
    expect(projectIdProblem('Bad_Id')).toMatch(/lower-case/);
    expect(projectIdProblem('')).toBeNull();
  });

  it('the default label: <d Mon yyyy>: built from <file names>', () => {
    expect(defaultLabel(['I1201.dwg', 'I1202.dwg'], new Date('2026-11-04T05:00:00Z'))).toBe('4 Nov 2026: built from I1201.dwg, I1202.dwg');
  });
});

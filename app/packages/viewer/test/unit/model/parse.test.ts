// Builder A: parseBuiltModel / parseReplayData (DESIGN.md 5.6, 7, 17.2 "model"). Every fixture model and features.model.json
// passes parseBuiltModel and ajv (Ajv2020, strict); every file of fixtures/models/broken/ is rejected at the path its
// manifest names (the four furniture cases warn instead); the replay data of both bank versions parses.
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { BuiltModel, ModelIssue } from '../../../src/contracts';
import { crossIssues, ModelError, parseBuiltModel, parseReplayData, replayIssues, schemaIssues } from '../../../src/model/parse';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(HERE, '../../../../..');
const json = (rel: string): unknown => JSON.parse(readFileSync(path.join(APP, rel), 'utf8'));
const FEATURES = 'packages/viewer/test/fixtures/features.model.json';
const schema = json('docs/built-model.schema.json') as object;
const ajv = new Ajv2020({ strict: true, allErrors: true }).compile(schema);
const models = readdirSync(path.join(APP, 'fixtures/models')).filter(f => f.endsWith('.model.json')).sort();

afterEach(() => { vi.restoreAllMocks(); });

const issuesOf = (fn: () => unknown): ModelIssue[] => {
  try { fn(); } catch (err) { if (err instanceof ModelError) return err.issues; throw err; }
  return [];
};

describe('parseBuiltModel on the fixture models', () => {
  it.each([...models.map(f => `fixtures/models/${f}`), FEATURES])('%s parses, with no warning, and ajv agrees', rel => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const m = json(rel);
    expect(ajv(m), JSON.stringify(ajv.errors)).toBe(true);
    expect(schemaIssues(m)).toEqual([]);
    expect(crossIssues(m as BuiltModel)).toEqual({ strict: [], furniture: [] });
    expect(parseBuiltModel(m)).toBe(m);
    expect(warn).not.toHaveBeenCalled();
  });

  it('features.model.json has what the build tests need: every part kind, fit top and clip, a plinth, panels, a deck, both skins, a picture', () => {
    const m = json(FEATURES) as BuiltModel;
    expect(new Set(m.parts.map(p => p.kind))).toEqual(new Set(['wall', 'column', 'lintel', 'sill', 'parapet', 'glass', 'pane', 'mullion',
      'railing', 'balustrade', 'single', 'step', 'low', 'builtin', 'deck', 'post', 'slab']));
    expect(new Set(m.parts.map(p => p.fit).filter(Boolean))).toEqual(new Set(['top', 'clip']));
    expect(m.parts.some(p => p.plinth && p.kind === 'slab')).toBe(true);
    expect(m.floors).toHaveLength(2);
    expect(Object.values(m.stairs).some(s => s.panels?.length)).toBe(true);
    expect(new Set(Object.values(m.colliderSkins).flat().map(s => s.glass))).toEqual(new Set([true, false]));
    expect(Object.keys(m.pictureFrame ?? {})).toEqual(['G']);
    expect(m.rooms.length).toBeGreaterThan(0);
    expect(new Set(m.openings.map(o => o.kind))).toEqual(new Set(['door', 'window', 'passage']));
    expect(m.probes.length).toBeGreaterThan(0);
    expect(m.furniture).toHaveLength(6);
  });
});

describe('fixtures/models/broken: each rejected at the manifest path', () => {
  const expected = json('fixtures/models/broken/expected.json') as { cases: Record<string, { path: string; kind: string; viewer: 'throws' | 'warns' }> };
  it.each(Object.entries(expected.cases))('%s', (file, c) => {
    const m = json(`fixtures/models/broken/${file}`);
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    if (c.viewer === 'throws') {
      const issues = issuesOf(() => parseBuiltModel(m));
      expect(issues.map(i => i.path)).toContain(c.path);
      expect(() => parseBuiltModel(m)).toThrow(ModelError);
      if (c.kind === 'schema') {
        expect(ajv(m)).toBe(false);
        expect((ajv.errors ?? []).map(e => e.instancePath)).toContain(c.path);
      }
    } else {
      expect(() => parseBuiltModel(m)).not.toThrow();
      const lines = warn.mock.calls.map(a => String(a[0]));
      expect(lines.some(l => l.startsWith(`[viewer] model: ${c.path}: `))).toBe(true);
      expect(crossIssues(m as BuiltModel).furniture.map(i => i.path)).toContain(c.path);
    }
  });

  it('a ModelError lists every issue, and its message names the first ones', () => {
    const m = json('fixtures/models/bank-v2.model.json') as Record<string, unknown>;
    const bad = { ...m, photoName: 'a b', units: 'mm' };
    let error: ModelError | null = null;
    try { parseBuiltModel(bad); } catch (err) { error = err as ModelError; }
    expect(error).toBeInstanceOf(ModelError);
    expect(error!.issues.map(i => i.path).sort()).toEqual(['/photoName', '/units']);
    expect(error!.message).toMatch(/^\[viewer\] model: 2 issue\(s\): /);
  });
});

describe('the schema checks, rule by rule (hand-written: no validator at run time)', () => {
  const base = () => structuredClone(json('fixtures/models/bank-v2.model.json')) as Record<string, any>;
  const paths = (m: unknown) => schemaIssues(m).map(i => i.path);
  it('closed objects: an extra property is reported at its object, as ajv does', () => {
    const m = base(); m.parts[0].colour = 'red'; m.extra = 1;
    expect(paths(m)).toEqual(expect.arrayContaining(['/parts/0', '']));
    expect(ajv(m)).toBe(false);
  });
  it('vec2 takes exactly two numbers; a ring at least three points', () => {
    const m = base(); m.offset = [1, 2, 3]; m.parts[1].o = [[0, 0], [1, 1]];
    expect(paths(m)).toEqual(expect.arrayContaining(['/offset', '/parts/1/o']));
  });
  it('enums, patterns, minimums: kind, floor keys, furniture keys, rot < 180, wallHeight > 0', () => {
    const m = base();
    m.parts[2].kind = 'roof'; m.floors[0].key = 'L 1'; m.furnitureKinds[0].key = 'none'; m.furniture[0].rot = 180; m.floors[1].wallHeight = 0;
    expect(paths(m)).toEqual(expect.arrayContaining(['/parts/2/kind', '/floors/0/key', '/furnitureKinds/0/key', '/furniture/0/rot', '/floors/1/wallHeight']));
  });
  it('per-floor maps check their property names; dependentRequired furniture -> furnitureKinds', () => {
    const m = base(); m.stairs['bad key'] = { below: [], above: [] }; delete m.furnitureKinds;
    const ps = schemaIssues(m);
    expect(ps.some(i => i.path === '/stairs' && /property name 'bad key'/.test(i.message))).toBe(true);
    expect(ps.some(i => i.path === '' && /furnitureKinds/.test(i.message))).toBe(true);
  });
  it('a non-object is refused at the root', () => {
    expect(paths(null)).toEqual(['']);
    expect(paths([])).toEqual(['']);
  });
});

describe('the cross-reference rules of 5.6', () => {
  const base = () => structuredClone(json('fixtures/models/bank-v2.model.json')) as BuiltModel;
  it('strict: floors in level order, unique keys, plinth only on slabs, per-floor keys, stairs in fours', () => {
    const m = base();
    m.floors[1]!.level = -1;
    (m.parts[0] as { plinth?: boolean }).plinth = true;
    m.voids['L7'] = [];
    m.stairs.L2!.above = [1, 2, 3];
    m.rooms[0]!.floor = 'L9';
    const strict = crossIssues(m).strict.map(i => i.path);
    expect(strict).toEqual(expect.arrayContaining(['/floors/1/level', '/parts/0/plinth', '/voids/L7', '/stairs/L2/above', '/rooms/0/floor']));
    expect(() => parseBuiltModel(m)).toThrow(ModelError);
  });
  it('furniture: unknown floor and duplicate ids only warn (furniture_boxes.js left such pieces out)', () => {
    const m = base();
    m.furniture![1]!.floor = 'L9';
    m.furniture![2]!.id = m.furniture![0]!.id;
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    expect(() => parseBuiltModel(m)).not.toThrow();
    const lines = warn.mock.calls.map(a => String(a[0]));
    expect(lines).toEqual(expect.arrayContaining([expect.stringMatching(/^\[viewer\] model: \/furniture\/1\/floor: /),
      expect.stringMatching(/^\[viewer\] model: \/furniture\/2\/id: /)]));
  });
});

describe('parseReplayData', () => {
  it.each(['bank-v1', 'bank-v2'])('the %s stages parse (valid v1 as they are)', v => {
    const model = json(`fixtures/models/${v}.model.json`) as BuiltModel;
    const stages = json(`fixtures/stages/${v}.stages.json`);
    expect(replayIssues(stages, model)).toEqual([]);
    expect(parseReplayData(stages, model)).toBe(stages);
  });
  it('wants every model floor, no other floor, the seven captions, flat lines in fours and pieces in eights', () => {
    const model = json('fixtures/models/bank-v2.model.json') as BuiltModel;
    const stages = structuredClone(json('fixtures/stages/bank-v2.stages.json')) as Record<string, any>;
    delete stages.captions.raise;
    stages.floors.L1.lines.wall = [1, 2, 3];
    stages.floors.L2.pieces.wall = [1, 2, 3, 4];
    const issues = replayIssues(stages, model).map(i => i.path);
    expect(issues).toEqual(expect.arrayContaining(['/captions', '/floors/L1/lines/wall', '/floors/L2/pieces/wall']));
    expect(() => parseReplayData(stages, model)).toThrow(ModelError);
    const other = structuredClone(json('fixtures/stages/bank-v2.stages.json')) as Record<string, any>;
    other.floors.L3 = other.floors.L2;
    delete other.floors.L2;
    expect(replayIssues(other, model).map(i => i.path)).toEqual(expect.arrayContaining(['/floors', '/floors/L3']));
  });
  it('takes the optional titles and colours, and refuses a colour that is not #rrggbb', () => {
    const model = json('fixtures/models/bank-v2.model.json') as BuiltModel;
    const stages = { ...(json('fixtures/stages/bank-v2.stages.json') as object), introTitle: 'x', layersTitle: 'Layers found', stepTitles: { read: 'Read it' }, colors: { wall: '#7a6650' } };
    expect(replayIssues(stages, model)).toEqual([]);
    expect(replayIssues({ ...stages, colors: { wall: 'brown' } }, model).map(i => i.path)).toEqual(['/colors/wall']);
  });
});

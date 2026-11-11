// Scaffold: the shared fixtures, read through node:fs (so the test tsconfig's Node types are exercised from the start;
// DESIGN.md 4.4): every fixture model is valid BuiltModel v1 for ajv (Ajv2020, strict), the byte-identical copies keep
// their model-data stamps, and every schema case of the broken corpus fails ajv at the path broken/expected.json names
// (the cross cases pass the schema: their faults are for the parsers).
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import { describe, expect, it } from 'vitest';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const read = (rel: string) => readFileSync(path.join(APP, rel));
const json = (rel: string): unknown => JSON.parse(read(rel).toString('utf8'));
const schema = json('docs/built-model.schema.json') as object;
const validate = new Ajv2020({ strict: true, allErrors: true }).compile(schema);
const models = readdirSync(path.join(APP, 'fixtures/models')).filter(f => f.endsWith('.model.json')).sort();

describe('fixtures/models', () => {
  it('has the six v1 models, and the four v2 models of the rooms scaffold', () => {
    const v2 = ['rooms-reference.model.json', 'stairs-L.model.json', 'stairs-U.model.json', 'stairs-straight.model.json'];
    expect(models).toEqual(['bank-v1.model.json', 'bank-v2.model.json', 'hotel.model.json', 'house.model.json', 'mini.model.json',
      ...v2, 'suite.model.json'].sort());
    // v2 = the model has the `stairways` key (docs/rooms/DESIGN.md R-12.2): exactly the four
    const has = (f: string) => 'stairways' in (json(`fixtures/models/${f}`) as object);
    expect(models.filter(has)).toEqual(v2);
  });

  it.each(models)('%s is valid BuiltModel v1 (ajv strict)', file => {
    const ok = validate(json(`fixtures/models/${file}`));
    expect(validate.errors ?? []).toEqual([]);
    expect(ok).toBe(true);
  });

  it.each([
    ['bank-v1.model.json', '4b02dc17f286'],
    ['bank-v2.model.json', 'c3a9408304a2'],
    ['hotel.model.json', '6ab030750886'],
  ])('%s is the prototype file byte for byte (stamp %s)', (file, stamp) => {
    expect(createHash('sha1').update(read(`fixtures/models/${file}`)).digest('hex').slice(0, 12)).toBe(stamp);
  });
});

describe('fixtures/models/broken', () => {
  const expected = json('fixtures/models/broken/expected.json') as { cases: Record<string, { path: string; kind: 'schema' | 'cross' }> };
  const cases = Object.entries(expected.cases);

  it('has 5 schema and 19 cross cases', () => {
    // 4: the fix step (4 Nov) added schema/pattern-trailing-newline.json ('$' before a final newline, Python vs ECMA)
    // the rooms scaffold R0 (11 Nov) added the v2 cases, one per rule of docs/rooms/DESIGN.md R-12.1: 1 schema, 11 cross
    expect(cases.filter(([, c]) => c.kind === 'schema')).toHaveLength(5);
    expect(cases.filter(([, c]) => c.kind === 'cross')).toHaveLength(19);
    expect(cases.filter(([file]) => /\/v2-/.test(file))).toHaveLength(12);
  });

  it.each(cases)('%s', (file, c) => {
    const ok = validate(json(`fixtures/models/broken/${file}`));
    if (c.kind === 'schema') {
      expect(ok).toBe(false);
      expect((validate.errors ?? []).map(e => e.instancePath)).toContain(c.path);
    } else {
      expect(validate.errors ?? []).toEqual([]);
    }
  });
});

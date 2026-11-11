// tools/check-openapi-additive.mjs after the rooms milestone (docs/rooms/DESIGN.md R-12.5; scaffold R0): an existing
// component schema may gain a property that is not required, an interface or object type of the generated client may
// gain optional members, and nothing else may move. The rule on hand-made pairs: a required property added and a
// property's type changed must both fail; then the tool itself on the real document with each of those two faults.
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterAll, describe, expect, it } from 'vitest';
import { schemaChange, symbolChange } from '../../../../../tools/openapi-additive-rules.mjs';

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');
const TOOL = path.join(APP, 'tools', 'check-openapi-additive.mjs');
const base = process.env.WT_TMP ?? os.tmpdir();
mkdirSync(base, { recursive: true });
const tmp = mkdtempSync(path.join(base, 'additive-'));
afterAll(() => rmSync(tmp, { recursive: true, force: true }));

const OLD = {
  type: 'object', title: 'FloorSetup', additionalProperties: false, required: ['key', 'level'],
  properties: { key: { type: 'string', title: 'Key' }, level: { type: 'number', title: 'Level' } },
};
const grown = (extra: Record<string, unknown>, required = OLD.required) => ({ ...OLD, required, properties: { ...OLD.properties, ...extra } });

describe('the additive rule for component schemas', () => {
  it('passes an unchanged schema and one that gained a property that is not required', () => {
    expect(schemaChange(OLD, structuredClone(OLD))).toBeNull();
    expect(schemaChange(OLD, grown({ ceilingHeight: { anyOf: [{ type: 'number' }, { type: 'null' }], title: 'Ceilingheight' } }))).toBeNull();
  });
  it('fails a required property added', () => {
    expect(schemaChange(OLD, grown({ ceilingHeight: { type: 'number' } }, ['key', 'level', 'ceilingHeight']))).toBe('its required list changed');
  });
  it("fails a property's type changed, a property gone, and any other key of the schema changed", () => {
    expect(schemaChange(OLD, { ...OLD, properties: { ...OLD.properties, level: { type: 'string', title: 'Level' } } })).toBe('property level changed');
    expect(schemaChange(OLD, { ...OLD, required: ['key'], properties: { key: OLD.properties.key } })).toBe('its required list changed');
    expect(schemaChange(OLD, { ...OLD, properties: { key: OLD.properties.key, extra: { type: 'number' } } })).toBe('property level is gone');
    expect(schemaChange(OLD, { ...grown({ extra: { type: 'number' } }), additionalProperties: true })).toBe('its additionalProperties changed');
    expect(schemaChange({ type: 'string', enum: ['a'] }, { type: 'string', enum: ['a', 'b'] })).toBe('changed');
  });
});

describe('the additive rule for the generated client', () => {
  const old = "export type FloorSetup = {\n    /**\n     * Key\n     */\n    key: string;\n    level: number;\n}";
  it('passes identical text and an object type or interface that gained optional members', () => {
    expect(symbolChange(old, old)).toBeNull();
    expect(symbolChange(old, old.replace('    level: number;', '    level: number;\n    /**\n     * Ceilingheight\n     */\n    ceilingHeight?: number | null;'))).toBeNull();
    expect(symbolChange('export interface A { a: string }', 'export interface A { a: string; b?: number }')).toBeNull();
  });
  it("fails a member that is not optional, a member's type changed, a member gone, and anything that is not an object type", () => {
    expect(symbolChange(old, old.replace('    level: number;', '    level: number;\n    ceilingHeight: number | null;'))).toBe('new member ceilingHeight is not optional');
    expect(symbolChange(old, old.replace('level: number', 'level: string'))).toBe('member level changed');
    expect(symbolChange(old, old.replace('    level: number;\n', ''))).toBe('member level is gone');
    expect(symbolChange("export type Units = 'mm' | 'm';", "export type Units = 'mm' | 'm' | 'cm';")).toBe('changed');
    expect(symbolChange('export const x = 1;', 'export const x = 2;')).toBe('changed');
    expect(symbolChange('export interface A { a: string }', 'export interface B { a: string; b?: number }')).toBe('changed');
  });
});

describe('the tool itself on the real document', { timeout: 120_000 }, () => {
  const doc = () => JSON.parse(readFileSync(path.join(APP, 'apps/web/openapi.json'), 'utf8'));
  const run = (file: string) => spawnSync(process.execPath, [TOOL, '--openapi', file], { cwd: APP, encoding: 'utf8' });
  const write = (name: string, d: unknown) => { const p = path.join(tmp, name); writeFileSync(p, JSON.stringify(d)); return p; };

  it('passes the document as it is, against the API before the rooms milestone', () => {
    const r = run(write('same.json', doc()));
    expect(r.stdout + r.stderr).toContain('ok (additive against 66b4c06');
    expect(r.status).toBe(0);
  });
  it('fails a required property added to an existing schema', () => {
    const d = doc();
    d.components.schemas.BuildDefaults.properties.extraHeight = { type: 'number', title: 'Extraheight' };
    d.components.schemas.BuildDefaults.required.push('extraHeight');
    const r = run(write('required.json', d));
    expect(r.status).toBe(1);
    expect(r.stderr).toContain('component schema BuildDefaults: its required list changed');
  });
  it("fails a property's type changed", () => {
    const d = doc();
    d.components.schemas.BuildDefaults.properties.doorHead = { type: 'string', title: 'Doorhead' };
    const r = run(write('type.json', d));
    expect(r.status).toBe(1);
    expect(r.stderr).toContain('component schema BuildDefaults: property doorHead changed');
  });
});
